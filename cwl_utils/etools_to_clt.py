#!/usr/bin/env python3
import sys
import copy
import cwl_utils.parser_v1_0 as cwl
from ruamel import yaml
from typing import Any, Dict, List, MutableSequence, Optional, Text, Union
from cwltool.expression import do_eval
from cwltool.errors import WorkflowException
from schema_salad.sourceline import SourceLine

def main():
    top = cwl.load_document(sys.argv[1])
    result = traverse(top, False)  # 2nd parameter: True to make CommandLineTools, False for ExpressionTools
    result_json = cwl.save(
        result,
        base_url=result.loadingOptions.fileuri)
    #   ^^ Setting the base_url and keeping the default value
    #      for relative_uris=True means that the IDs in the generated
    #      JSON/YAML are kept clean of the path to the input document
    yaml.scalarstring.walk_tree(result_json)
    # ^ converts multine line strings to nice multiline YAML
    print("#!/usr/bin/env cwl-runner")  # TODO: teach the codegen to do this?
    yaml.round_trip_dump(result_json, sys.stdout)


def escape_expression_field(contents: str) -> str:
    return contents.replace('${', '$/{').replace('$(', '$/(')

def is_expression(string: str,
                  inputs: Dict[Text, Union[Dict, List, Text, None]],
                  self: Optional[Any]
                 ) -> bool:
    if string.strip().startswith('${'):
        return True
    if '$(' in string:
        try:
            do_eval(string, inputs, context=self)
        except WorkflowException:
            return True
    return False

def etool_to_cltool(etool: cwl.ExpressionTool, expressionLib: Optional[List[str]]=None) -> cwl.CommandLineTool:
    inputs = yaml.comments.CommentedSeq()  # preserve the order
    for inp in etool.inputs:
        inputs.append(cwl.CommandInputParameter(
            inp.label, inp.secondaryFiles, inp.streamable, inp.doc, inp.id,
            inp.format, None, inp.default, inp.type, inp.extension_fields,
            inp.loadingOptions))
    outputs = yaml.comments.CommentedSeq()
    for outp in etool.outputs:
        outputs.append(cwl.CommandOutputParameter(
            outp.label, outp.secondaryFiles, outp.streamable, outp.doc,
            outp.id, None, outp.format, outp.type, outp.extension_fields,
            outp.loadingOptions))
    contents = """"use strict";
var inputs=$(inputs);
var runtime=$(runtime);"""
    if expressionLib:
        contents += "\n" + "\n".join(expressionLib)
    contents +="""
var ret = function(){"""+etool.expression.strip()[2:-1]+"""}();
process.stdout.write(JSON.stringify(ret));"""
    contest = escape_expression_field(contents)
    listing = [cwl.Dirent("expression.js", contents, writable=None)]
    iwdr = cwl.InitialWorkDirRequirement(listing)
    containerReq = cwl.DockerRequirement("node:slim", None, None, None, None, None)
    return cwl.CommandLineTool(
        etool.id, inputs, outputs, [iwdr],
        [containerReq], etool.label, etool.doc,
        etool.cwlVersion, ["nodejs", "expression.js"], None, None, None,
        "cwl.output.json", None, None, None, etool.extension_fields,
        etool.loadingOptions)


def traverse(process: cwl.Process, replace_etool=False) -> cwl.Process:
    if isinstance(process, cwl.ExpressionTool) and replace_etool:
        return etool_to_cltool(process)
    if isinstance(process, cwl.Workflow):
        return traverse_workflow(process, replace_etool)
    return process


def load_step(step: cwl.WorkflowStep) -> cwl.WorkflowStep:
    if isinstance(step.run, str):
        step.run = traverse(cwl.load_document(step.run))

def generate_etool_from_expr(expr: str,
                             target: cwl.Parameter,
                             no_inputs=False,
                             self_type: Optional[cwl.Parameter] = None,  # if the "self" input should be a different type than the "result" output
                            ) -> cwl.ExpressionTool:
    inputs = yaml.comments.CommentedSeq()
    if not no_inputs:
        if not self_type:
            self_type = target
        inputs.append(cwl.InputParameter(
            self_type.label, self_type.secondaryFiles, self_type.streamable, self_type.doc, "self",
            self_type.format, None, None, self_type.type, self_type.extension_fields, self_type.loadingOptions))
    outputs = yaml.comments.CommentedSeq()
    outputs.append(cwl.ExpressionToolOutputParameter(
        target.label, target.secondaryFiles, target.streamable, target.doc,
        "result", None, target.format, target.type))
    expression = "${"
    if not no_inputs:
        expression += "\n  var self=inputs.self;"
    expression += """
  return {"result": function(){"""+expr[2:-1]+"""}()};
 }"""
    return cwl.ExpressionTool(
        None, inputs, outputs, [cwl.InlineJavascriptRequirement(None)], None,
        None, None, "v1.0", expression)

def get_input_for_id(name: str, tool: [cwl.CommandLineTool, cwl.Workflow]) -> cwl.CommandInputParameter:
    name = name.split('/')[-1]
    for inp in tool.inputs:
        if inp.id.split('#')[-1] == name:
            return inp
    if isinstance(tool, cwl.Workflow) and '/' in name:
        stepname, stem = name.split('/', 1)
        for step in tool.steps:
            if step.id == stepname:
                result = get_input_for_id(stem, tool.run)
                if result:
                    return result

def find_expressionLib(processes: List[cwl.Process]) -> Optional[List[str]]:
    for process in processes.reverse():
        if process.requirements:
            for req in process.requirements:
                if isinstance(req, cwl.InlineJavascriptRequirement):
                    return req.expressionLib

def replace_expr_with_etool(expr: str,
                            name: str,
                            workflow: cwl.Workflow,
                            target: cwl.Parameter,
                            source: Optional[str],
                            replace_etool=False,
                            extra_process: cwl.Process = None) -> None:
    etool = generate_etool_from_expr(expr, target, source == None)
    if replace_etool:
        processes = [workflow]
        if extra_process:
            processes.append(extra_process)
        etool = etool_to_cltool(etool, find_expressionLib(processes))
    inps = []
    if source:
        inps.append(cwl.WorkflowStepInput(source, None, "self", None, None))
    workflow.steps.append(cwl.WorkflowStep(
        name,
        inps,
        [cwl.WorkflowStepOutput("result")], None, None, None, None, etool, None, None))

def replace_wf_input_ref_with_step_output(workflow: cwl.Workflow, name: str, target: str) -> None:
    if workflow.steps:
        for step in workflow.steps:
            if step.in_:
                for inp in step.in_:
                    if inp.source:
                        if inp.source == name:
                            inp.source = target
                        if isinstance(inp.source, MutableSequence):
                            for index, source in enumerate(inp.source):
                                if souce == name:
                                    inp.source[index] = target
    if workflow.outputs:
        for outp in workflow.outputs:
            if outp.outputSource:
                if outp.outputSource == name:
                    outp.outputSource = target
                if isinstance(outp.outputSource, MutableSequence):
                    for index, outputSource in enumerate(outp.outputSource):
                        if outputSource == name:
                            outp.outputSource[index] = target

def empty_inputs(process_or_step: Union[cwl.Process, cwl.WorkflowStep], parent: Optional[cwl.Workflow] = None) -> Dict[str, Any]:
    result = {}
    if isinstance(process_or_step, cwl.Process):
        for param in process_or_step.inputs:
            result[param.id] = example_input(param.type)
    else:
        for param in process_or_step.in_:
            try:
                result[param.id] = example_input(type_for_source(process_or_step.run, param.id.split('/')[-1], parent))
            except WorkflowException:
                pass
    return result

def example_input(some_type: Any) -> Any:
    #TODO: return an example input for the provided type
    return None

def type_for_source(process: cwl.Process, sourcenames: Union[str, List[str]], parent: Optional[cwl.Workflow] = None) -> Any:
    if isinstance(sourcenames, str):
        sourcenames = [sourcenames]
    for sourcename in sourcenames:
        for param in process.inputs:
            if param.id.split('#')[-1] == sourcename:
                return param.type
        if isinstance(process, cwl.Workflow):
            for step in process.steps:
                if sourcename.split('/')[0] == step.id.split('#')[:-1]:
                    try:
                        return type_for_source(step.run, sourcename.split('/', 1)[1])
                    except WorkflowException:
                        pass
    raise WorkflowException("param {} not found in {} or ".format(sourcename, cwl.save(process), cwl.save(parent)))

EMPTY_FILE = {"class": "File", "basename": "em.pty", "nameroot": "em", "nameext": "pty"}

TOPLEVEL_SF_EXPR_ERROR="Input '{}'. Sorry, CWL Expressions as part of a secondaryFiles "\
    "specification in a Workflow level input are not able to be refactored "\
    "into separate ExpressionTool/CommandLineTool steps."

TOPLEVEL_FORMAT_EXPR_ERROR="Input '{}'. Sorry, CWL Expressions as part of a secondaryFiles "\
    "specification in a Workflow level input are not able to be refactored "\
    "into separate ExpressionTool/CommandLineTool steps."


def process_workflow_inputs_and_outputs(workflow: cwl.Workflow, replace_etool) -> None:
    inputs = empty_inputs(workflow)
    for param in workflow.inputs:
        if param.format and is_expression(param.format, inputs, None):
            raise SourceLine(
                param.loadingOptions.original_doc, 'format',
                raise_type=WorkflowException).makeError(
                    TOPLEVEL_FORMAT_EXPR_ERROR.format(param.id.split('#')[-1]))
        if param.secondaryFiles:
            if is_expression(param.secondaryFiles, inputs, EMPTY_FILE):
                raise SourceLine(
                    param.loadingOptions.original_doc, 'secondaryFiles',
                    raise_type=WorkflowException).makeError(
                        TOPLEVEL_SF_EXPR_ERROR.format(param.id.split('#')[-1]))
            elif isinstance(param.secondaryFiles, MutableSequence):
                for index, entry in enumerate(param.secondaryFiles):
                    if is_expression(entry, inputs, EMPTY_FILE):
                        raise SourceLine(
                            param.secondaryFiles.loadingOptions.original_doc,
                            index, raise_type=WorkflowException).makeError(
                                "Entry {},".format(index)
                                + TOPLEVEL_SF_EXPR_ERROR.format(
                                    param.id.split('#')[-1]))

def process_workflow_reqs_and_hints(workflow: cwl.Workflow, replace_etool=False) -> None:
    # TODO: consolidate the generated etools/cltools into a single "_expression_workflow_reqs" step
    # TODO: support resourceReq.* references to Workflow.inputs?
    #       ^ By refactoring replace_expr_etool to allow multiple inputs, and connecting all workflow inputs to the generated step
    inputs = empty_inputs(workflow)
    generated_res_reqs: List[Tuple[str, str]] = []
    generated_iwdr_reqs: List[Tuple[str, str]] = []
    generated_envVar_reqs: List[Tuple[str, str]] = []
    prop_reqs: Tuple[cwl.ProcessRequirement] = ()
    resourceReq: Optional[cwl.ResourceRequirement] = None
    envVarReq: Optional[cwl.EnvVarRequirement] = None
    iwdr: Optional[cwl.InitialWorkDirRequirement] = None
    if workflow.requirements:
        for req in workflow.requirements:
            if req and isinstance(req, cwl.EnvVarRequirement):
                if req.envDef:
                    for index, envDef in enumerate(req.envDef):
                        if envDef.envValue and is_expression(envDef.envValue, inputs, None):
                            target = cwl.InputParameter(None, None, None, None, None, None, None, None, "string")
                            etool_id = "_expression_workflow_EnvVarRequirement_{}".format(index)
                            replace_expr_with_etool(
                                envDef.envValue,
                                etool_id,
                                workflow,
                                target,
                                None,
                                replace_etool)
                            if not envVarReq:
                                envVarReq = copy.deepcopy(req)
                                prop_reqs += (cwl.EnvVarRequirement, )
                            newEnvDef = copy.deepcopy(envDef)
                            newEnvDef.envValue = "$(inputs._envDef{})".format(index)
                            envVarReq.envDef[index] = newEnvDef
                            generated_envVar_reqs.append((etool_id, index))
            if req and isinstance(req, cwl.ResourceRequirement):
                for attr in cwl.ResourceRequirement.attrs:
                    this_attr = getattr(req, attr, None)
                    if this_attr and is_expression(this_attr, inputs, None):
                        target = cwl.InputParameter(None, None, None, None, None, None, None, None, "long")
                        etool_id = "_expression_workflow_ResourceRequirement_{}".format(attr)
                        replace_expr_with_etool(
                            this_attr,
                            etool_id,
                            workflow,
                            target,
                            None,
                            replace_etool)
                        if not resourceReq:
                            resourceReq = cwl.ResourceRequirement(
                                None, None, None, None, None, None, None, None,
                                loadingOptions=workflow.loadingOptions)
                            prop_reqs += (cwl.ResourceRequirement, )
                        setattr(resourceReq, attr, "$(inputs._{})".format(attr))
                        generated_res_reqs.append((etool_id, attr))
            if req and isinstance(req, cwl.InitialWorkDirRequirement):
                if req.listing:
                    if isinstance(req.listing, str) and is_expression(req.listing, inputs, None):
                        target_type = cwl.InputArraySchema(['File', 'Directory'], 'array', None, None)
                        target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                        etool_id = "_expression_workflow_InitialWorkDirRequirement"
                        replace_expr_with_etool(
                            req.listing,
                            etool_id,
                            workflow,
                            target,
                            None,
                            replace_etool)
                        iwdr = cwl.InitialWorkDirRequirement(
                            "$(inputs._iwdr_listing)",
                            loadingOptions=workflow.loadingOptions)
                        prop_reqs += (cwl.InitialWorkDirRequirement, )
                    else:
                        iwdr = copy.deepcopy(req)
                        for index, entry in enumerate(req.listing):
                            if is_expression(entry, inputs, None):
                                target_type = cwl.InputArraySchema(['File', 'Directory'], 'array', None, None)
                                target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                                etool_id = "_expression_workflow_InitialWorkDirRequirement_{}".format(index)
                                replace_expr_with_etool(
                                    entry,
                                    etool_id,
                                    workflow,
                                    target,
                                    None,
                                    replace_etool)
                                iwdr.listing[index] = "$(inputs._iwdr_listing_{}".format(index)
                                generated_iwdr_reqs.append((etool_id, index))
                            elif isinstance(entry, cwl.Dirent):
                                if entry.entry and is_expression(entry.entry, inputs, None):
                                    target_type = [cwl.File, cwl.Dirent]
                                    target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                                    etool_id = "_expression_workflow_InitialWorkDirRequirement_{}".format(index)
                                    replace_expr_with_etool(
                                        entry.entry,
                                        etool_id,
                                        workflow,
                                        target,
                                        None,
                                        replace_etool)
                                    iwdr.listing[index] = "$(inputs._iwdr_listing_{}".format(index)
                                    generated_iwdr_reqs.append((etool_id, index))
                                elif entry.entryname and is_expression(entry.entryname, inputs, None):
                                    target = cwl.InputParameter(None, None, None, None, None, None, None, None, str)
                                    etool_id = "_expression_workflow_InitialWorkDirRequirement_{}".format(index)
                                    replace_expr_with_etool(
                                        entry.entryname,
                                        etool_id,
                                        workflow,
                                        target,
                                        None,
                                        replace_etool)
                                    iwdr.listing[index] = "$(inputs._iwdr_listing_{}".format(index)
                                    generated_iwdr_reqs.append((etool_id, index))
                        if generated_iwdr_reqs:
                            prop_reqs += (cwl.InitialWorkDirRequirement, )
                        else:
                            iwdr = None
    if envVarReq and workflow.steps:
        for step in workflow.steps:
            if step.id.split("#")[-1].startswith("_expression_"):
                continue
            if step.requirements:
                for req in step.requirements:
                    if isinstance(req, cwl.EnvVarRequirement):
                        continue
            else:
                step.requirements = yaml.comments.CommentedSeq()
            step.requirements.append(envVarReq)
            for entry in generated_envVar_reqs:
                step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, "_envDef{}".format(entry[1]), None, None))


    if resourceReq and workflow.steps:
        for step in workflow.steps:
            if step.id.split("#")[-1].startswith("_expression_"):
                continue
            if step.requirements:
                for req in step.requirements:
                    if isinstance(req, cwl.ResourceRequirement):
                        continue
            else:
                step.requirements = yaml.comments.CommentedSeq()
            step.requirements.append(resourceReq)
            for entry in generated_res_reqs:
                step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, "_{}".format(entry[1]), None, None))

    if iwdr and workflow.steps:
        for step in workflow.steps:
            if step.id.split("#")[-1].startswith("_expression_"):
                continue
            if step.requirements:
                for req in step.requirements:
                    if isinstance(req, cwl.InitialWorkDirRequirement):
                        continue
            else:
                step.requirements = yaml.comments.CommentedSeq()
            step.requirements.append(iwdr)
            if generated_iwdr_reqs:
                for entry in generatetd_iwdr_reqs:
                    step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, "_iwdr_listing_{}".format(index), None, None))
            else:
                step.in_.append(cwl.WorkflowStepInput("_expression_workflow_InitialWorkDirRequirement/result", None, "_iwdr_listing", None, None))


    workflow.requirements[:] = [
        x for x  in workflow.requirements
        if not isinstance(x, prop_reqs)]

def process_level_reqs(process: cwl.Process, step: cwl.WorkflowStep, parent: cwl.Workflow, replace_etool=False) -> None:
    # This is for reqs inside a Process (CommandLineTool, ExpressionTool)
    # differences from process_workflow_reqs_and_hints() are:
    # - the name of the generated ETools/CTools contain the name of the step, not "workflow"
    # - Generated ETools/CTools are adjacent steps
    # - Replace the CWL Expression inplace with a CWL parameter reference
    # - Don't create a new Requirement, nor delete the existing Requirement
    # - the Process is passed to replace_expr_with_etool for later searching for JS expressionLibs
    # - in addition to adding the input to the step for the ETool/CTool result, add it to the Process.inputs as well
    if not process.requirements:
        return
    inputs = empty_inputs(process)
    generated_res_reqs: List[Tuple[str, str]] = []
    generated_iwdr_reqs: List[Tuple[str, str, Any]] = []
    generated_envVar_reqs: List[Tuple[str, str]] = []
    step_name = step.id.split('#',1)[1]
    for req in process.requirements:
        if req and isinstance(req, cwl.EnvVarRequirement):
            if req.envDef:
                for index, envDef in enumerate(req.envDef):
                    if envDef.envValue and is_expression(envDef.envValue, inputs, None):
                        target = cwl.InputParameter(None, None, None, None, None, None, None, None, "string")
                        etool_id = "_expression_{}_EnvVarRequirement_{}".format(step_name, index)
                        replace_expr_with_etool(
                            envDef.envValue,
                            etool_id,
                            parent,
                            target,
                            None,
                            replace_etool,
                            process)
                        envDef.envValue = "$(inputs._envDef{})".format(index)
                        generated_envVar_reqs.append((etool_id, index))
        if req and isinstance(req, cwl.ResourceRequirement):
            for attr in cwl.ResourceRequirement.attrs:
                this_attr = getattr(req, attr, None)
                if this_attr and is_expression(this_attr, inputs, None):
                    target = cwl.InputParameter(None, None, None, None, None, None, None, None, "long")
                    etool_id = "_expression_{}_ResourceRequirement_{}".format(step_name, attr)
                    replace_expr_with_etool(
                        this_attr,
                        etool_id,
                        parent,
                        target,
                        None,
                        replace_etool,
                        process)
                    setattr(req, attr, "$(inputs._{})".format(attr))
                    generated_res_reqs.append((etool_id, attr))

        if req and isinstance(req, cwl.InitialWorkDirRequirement):
            if req.listing:
                if isinstance(req.listing, str) and is_expression(req.listing, inputs, None):
                    target_type = cwl.InputArraySchema(['File', 'Directory'], 'array', None, None)
                    target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                    etool_id = "_expression_{}_InitialWorkDirRequirement".format(step_name)
                    replace_expr_with_etool(
                        req.listing,
                        etool_id,
                        parent,
                        target,
                        None,
                        replace_etool,
                        process)
                    req.listing = "$(inputs._iwdr_listing)",
                    step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, "_iwdr_listing", None, None))
                    add_input_to_process(process, "_iwdr_listing", target_type)
                else:
                    for index, entry in enumerate(req.listing):
                        if is_expression(entry, inputs, None):
                            target_type = cwl.InputArraySchema(['File', 'Directory'], 'array', None, None)
                            target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                            etool_id = "_expression_{}_InitialWorkDirRequirement_{}".format(step_name, index)
                            replace_expr_with_etool(
                                entry,
                                etool_id,
                                parent,
                                target,
                                None,
                                replace_etool,
                                process)
                            req.listing[index] = "$(inputs._iwdr_listing_{}".format(index)
                            generated_iwdr_reqs.append((etool_id, index))
                        elif isinstance(entry, cwl.Dirent):
                            if entry.entry and is_expression(entry.entry, inputs, None):
                                target_type = [cwl.File, cwl.Dirent]
                                target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                                etool_id = "_expression_{}_InitialWorkDirRequirement_{}".format(step_name, index)
                                replace_expr_with_etool(
                                    entry.entry,
                                    etool_id,
                                    parent,
                                    target,
                                    None,
                                    replace_etool,
                                    process)
                                entry.entry = "$(inputs._iwdr_listing_{}".format(index)
                                generated_iwdr_reqs.append((etool_id, index, target_type))
                            elif entry.entryname and is_expression(entry.entryname, inputs, None):
                                target = cwl.InputParameter(None, None, None, None, None, None, None, None, "string")
                                etool_id = "_expression_{}_InitialWorkDirRequirement_{}".format(index)
                                replace_expr_with_etool(
                                    entry.entryname,
                                    etool_id,
                                    parent,
                                    target,
                                    None,
                                    replace_etool,
                                    process)
                                entry.entryname = "$(inputs._iwdr_listing_{}".format(index)
                                generated_iwdr_reqs.append((etool_id, index, "string"))
    for entry in generated_envVar_reqs:
        name = "_envDef{}".format(entry[1])
        step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, name, None, None))
        add_input_to_process(process, name, "string", process.loadingOptions)
    for entry in generated_res_reqs:
        name = "_{}".format(entry[1])
        step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, name, None, None))
        add_input_to_process(process, name, "long", process.loadingOptions)
    for entry in generated_iwdr_reqs:
        name = "_iwdr_listing_{}".format(index)
        step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, name, None, None))
        add_input_to_process(process, name, entry[2], process.loadingOptions)

def add_input_to_process(process: cwl.Process, name: str, inptype: Any, loadingOptions: cwl.LoadingOptions):
    if isinstance(process, cwl.CommandLineTool):
        process.inputs.append(cwl.CommandInputParameter(
            None, None, None, None, name, None, None, None, inptype,
            loadingOptions=loadingOptions))

def traverse_CommandLineTool(clt: cwl.CommandLineTool, parent: cwl.Workflow, step=cwl.WorkflowStep, replace_etool=False) -> None:
    inputs = empty_inputs(clt)
    step_id = step.id.split('#')[-1]
    if clt.arguments:
        for index, arg in enumerate(clt.arguments):
            if isinstance(arg, str) and is_expression(arg, inputs, None):
                inp_id = "_arguments_{}".format(index)
                etool_id = "_expression_{}{}".format(step_id, inp_id)
                target_type = "string"
                target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                replace_step_clt_expr_with_etool(
                    arg,
                    etool_id,
                    parent,
                    target,
                    step,
                    replace_etool)
                clt.arguments[index] = "$(inputs.{})".format(inp_id)
                clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, target_type))
                step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
            elif isinstance(arg, cwl.CommandLineBinding) and arg.valueFrom \
                    and is_expression(arg.valueFrom, inputs, None):
                inp_id = "_arguments_{}".format(index)
                etool_id = "_expression_{}{}".format(step_id, inp_id)
                target_type = "string"
                target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                replace_step_clt_expr_with_etool(
                    arg.valueFrom,
                    etool_id,
                    parent,
                    target,
                    step,
                    replace_etool)
                arg.valueFrom = "$(inputs.{})".format(inp_id)
                clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, target_type))
                step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
    for streamtype in 'stdout', 'stderr':  # add 'stdin' for v1.1 version
        stream_value = getattr(clt, streamtype)
        if stream_value and is_expression(stream_value, inputs, None):
            inp_id = "_{}".format(streamtype)
            etool_id = "_expression_{}{}".format(step_id, inp_id)
            target_type = "string"
            target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
            replace_step_clt_expr_with_etool(
                stream_value,
                etool_id,
                parent,
                target,
                step,
                replace_etool)
            setattr(clt, streamtype, "$(inputs.{})".format(inp_id))
            clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, target_type))
            step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
    for inp in clt.inputs:
        if inp.inputBinding and inp.inputBinding.valueFrom and is_expression(inp.inputBinding.valueFrom, inputs, example_input(inp.type)):
            self_id = inp.id.split('#')[-1]
            inp_id = "_{}_valueFrom".format(self_id)
            etool_id = "_expression_{}{}".format(step_id, inp_id)
            replace_step_clt_expr_with_etool(
                inp.inputBinding.valueFrom,
                etool_id,
                parent,
                inp,
                step,
                replace_etool,
                self_id)
            inp.inputBinding.valueFrom = "$(inputs.{})".format(inp_id)
            clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, inp.type))
            step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
    for outp in clt.outputs:
        if outp.outputBinding:
            if outp.outputBinding.glob and is_expression(outp.outputBinding.glob, inputs, None):
                inp_id = "_{}_glob".format(outp.id.split('#')[-1])
                etool_id = "_expression_{}{}".format(step_id, inp_id)
                target_type = ["string", cwl.ArraySchema("string", "array")]
                target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                replace_step_clt_expr_with_etool(
                    outp.outputBinding.glob,
                    etool_id,
                    parent,
                    target,
                    step,
                    replace_etool)
                outp.outputBinding.glob = "$(inputs.{})".format(inp_id)
                clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, target_type))
                step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
            if outp.outputBinding.outputEval:
                self = [{"class": "File", "basename": "base.name", "nameroot": "base", "nameext": "name", "path": "/tmp/base.name", "dirname": "/tmp" }]
                if outp.outputBinding.loadContents:
                    self[0]["contents"] = "stuff"
                if is_expression(outp.outputBinding.outputEval, inputs, self):
                    outp_id = outp.id.split('#')[-1]
                    inp_id = "_{}_outputEval".format(outp_id)
                    etool_id = "_expression_{}{}".format(step_id, inp_id)
                    self_type = cwl.InputParameter(
                        None, None, None, None, None, None, None, None,
                        cwl.ArraySchema("File", "array"))
                    etool = generate_etool_from_expr(outp.outputBinding.outputEval, outp, False, self_type)
                    etool.inputs.extend(cltool_inputs_to_etool_inputs(clt))
                    outp.type = self_type.type
                    if replace_etool:
                        processes = [parent]
                        etool = etool_to_cltool(etool, find_expressionLib(processes))
                    wf_step_inputs = copy.deepcopy(step.in_)
                    for wf_step_input in wf_step_inputs:
                        wf_step_input.id = wf_step_input.id.split('/')[-1]
                    wf_step_inputs[:] = [
                        x for x  in wf_step_inputs
                        if not x.id.startswith('_')]
                    etool_step = cwl.WorkflowStep(
                        etool_id,
                        wf_step_inputs,
                        [cwl.WorkflowStepOutput("result")], None, None, None, None, etool, None, None)
                    parent.steps.append(etool_step)
                    rename_step_source(parent, "{}/{}".format(step_id, outp_id), "{}/result".format(etool_id))
                    wf_step_inputs.append(cwl.WorkflowStepInput("{}/{}".format(step_id, outp_id), None, "self", None, None))
                    outp.outputBinding.outputEval = None


def rename_step_source(workflow: cwl.Workflow, old: str, new: str) -> None:
    def simplify_wf_id(uri: str) -> str:
        return uri.split('#')[-1].split('/', 1)[1]
    def simplify_step_id(uri: str) -> str:
        return uri.split('#')[-1]
    for wf_outp in workflow.outputs:
        if wf_outp.outputSource and simplify_wf_id(wf_outp.outputSource) == old:
            wf_outp.outputSource = new
    for step in workflow.steps:
        if step.in_:
            for inp in step.in_:
                if inp.source:
                    if isinstance(inp.source, str):
                        source_id = simplify_step_id(inp.source) if '#' in inp.source else inp.source
                        if source_id == old:
                            inp.source = new
                    else:
                        for index, source in enumerate(inp.source):
                            if simplify_step_id(source) == old:
                                inp.source[index] = new

def replace_step_clt_expr_with_etool(expr: str,
                                     name: str,
                                     workflow: cwl.Workflow,
                                     target: cwl.Parameter,
                                     step: cwl.WorkflowStep,
                                     replace_etool=False,
                                     self_name: Optional[str]=None,
                                    ) -> None:
    etool_inputs = cltool_inputs_to_etool_inputs(step.run)
    etool = generate_etool_from_expr2(expr, target, etool_inputs, self_name)
    if replace_etool:
        processes = [workflow]
        etool = etool_to_cltool(etool, find_expressionLib(processes))
    wf_step_inputs = copy.deepcopy(step.in_)
    for wf_step_input in wf_step_inputs:
        wf_step_input.id = wf_step_input.id.split('/')[-1]
    wf_step_inputs[:] = [
        x for x  in wf_step_inputs
        if not x.id.startswith('_')]
    workflow.steps.append(cwl.WorkflowStep(
        name,
        wf_step_inputs,
        [cwl.WorkflowStepOutput("result")], None, None, None, None, etool, None, None))

def cltool_inputs_to_etool_inputs(tool: cwl.CommandLineTool) -> List[cwl.InputParameter]:
    inputs = yaml.comments.CommentedSeq()
    if tool.inputs:
        for clt_inp in tool.inputs:
            clt_inp_id = clt_inp.id.split('#')[-1].split('/')[-1]
            if not clt_inp_id.startswith('_'):
                inputs.append(cwl.InputParameter(
                    clt_inp.label, clt_inp.secondaryFiles, clt_inp.streamable,
                    clt_inp.doc, clt_inp_id, clt_inp.format, None, clt_inp.default,
                    clt_inp.type, clt_inp.extension_fields, clt_inp.loadingOptions))
    return inputs


def generate_etool_from_expr2(expr: str,
                              target: cwl.Parameter,
                              inputs: List[cwl.Parameter],
                              self_name: Optional[str] = None
                             ) -> cwl.ExpressionTool:
    outputs = yaml.comments.CommentedSeq()
    outputs.append(cwl.ExpressionToolOutputParameter(
        target.label, target.secondaryFiles, target.streamable, target.doc,
        "result", None, target.format, target.type))
    expression = "${"
    if self_name:
        expression += "\n  var self=inputs.{};".format(self_name)
    expression += """
  return {"result": function(){"""+expr[2:-1]+"""}()};
 }"""
    return cwl.ExpressionTool(
        None, inputs, outputs, [cwl.InlineJavascriptRequirement(None)], None,
        None, None, "v1.0", expression)


def traverse_step(step: cwl.WorkflowStep, parent: cwl.Workflow, replace_etool=False) -> None:
    inputs = empty_inputs(step, parent)
    step_id = step.id.split('#')[-1]
    for inp in step.in_:
        if inp.valueFrom:
            if not inp.source:
                self = None
            elif not step.scatter:
                self = example_input(type_for_source(parent, inp.source.split('#')[-1]))
            else:
                self = example_input(type_for_source(parent, inp.source).type)
            if is_expression(inp.valueFrom, empty_inputs, self):
                etool_id = "_expression_{}_{}".format(step_id, inp.id.split('/')[-1])
                replace_expr_with_etool(
                    inp.valueFrom,
                    etool_id,
                    parent,
                    get_input_for_id(inp.id, step.run),
                    inp.source.split('#')[-1],
                    replace_etool,
                    step)
                inp.valueFrom = None
                inp.source = "{}/result".format(etool_id)
    # TODO: skip or special process for sub workflows?
    process_level_reqs(step.run, step, parent, replace_etool)
    if isinstance(step.run, cwl.CommandLineTool):
        traverse_CommandLineTool(step.run, parent, step, replace_etool)

def traverse_workflow(workflow: cwl.Workflow, replace_etool=False) -> cwl.Workflow:
    for index, step in enumerate(workflow.steps):
        if isinstance(step.run, cwl.ExpressionTool) and replace_etool:
            workflow.steps[index].run = etool_to_cltool(step.run)
        else:
            load_step(step)
    for step in workflow.steps:
        if not step.id.startswith('_expression'):
            traverse_step(step, workflow)
    process_workflow_inputs_and_outputs(workflow, replace_etool)
    process_workflow_reqs_and_hints(workflow, replace_etool)
    workflow.requirements[:] = [
        x for x  in workflow.requirements
        if not isinstance(x, (cwl.InlineJavascriptRequirement,
                              cwl.StepInputExpressionRequirement))]
    if not workflow.requirements:
        workflow.requirements = None
    return workflow


if __name__ == "__main__":
    sys.exit(main())
