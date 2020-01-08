#!/usr/bin/env python3
import sys
import copy
import shutil
import hashlib
import cwl_utils.parser_v1_0 as cwl
from ruamel import yaml
from typing import Any, Dict, List, MutableSequence, Optional, Sequence, Text, Tuple, Type, Union
from cwltool.expression import do_eval
from cwltool.errors import WorkflowException
from schema_salad.sourceline import SourceLine
from schema_salad.utils import json_dumps

SKIP_COMMAND_LINE = True  # don't process CommandLineTool.inputs...inputBinding and CommandLineTool.arguments sections
SKIP_COMMAND_LINE2 = True  # don't process CommandLineTool.outputEval or CommandLineTool.requirements...InitialWorkDirRequirement
# as Galaxy will use cwltool which can handle expression which might appear there

def main():
    top = cwl.load_document(sys.argv[1])
    result, modified = traverse(top, False)  # 2nd parameter: True to make CommandLineTools, False for ExpressionTools
    if not modified:
        with open(sys.argv[1], 'r') as f:
            shutil.copyfileobj(f, sys.stdout)
            return
    if not isinstance(result, MutableSequence):
        result_json = cwl.save(
            result,
            base_url=result.loadingOptions.fileuri)
    #   ^^ Setting the base_url and keeping the default value
    #      for relative_uris=True means that the IDs in the generated
    #      JSON/YAML are kept clean of the path to the input document
    else:
        result_json = [cwl.save(
            result_item, base_url=result_item.loadingOptions.fileuri) for
            result_item in result]
    yaml.scalarstring.walk_tree(result_json)
    # ^ converts multine line strings to nice multiline YAML
    print("#!/usr/bin/env cwl-runner")  # TODO: teach the codegen to do this?
    yaml.round_trip_dump(result_json, sys.stdout)


def expand_stream_shortcuts(process: cwl.CommandLineTool) -> cwl.CommandLineTool:
    if not process.outputs:
        return process
    result = None
    for index, output in enumerate(process.outputs):
        if output.type == 'stdout':
            if not result:
                result = copy.deepcopy(process)
            stdout_path = process.stdout
            if not stdout_path:
                stdout_path = str(hashlib.sha1(json_dumps(cwl.save(process)).encode('utf-8')).hexdigest())
                result.stdout = stdout_path
            result.outputs[index].type = 'File'
            output.outputBinding = cwl.CommandOutputBinding(stdout_path, None, None)
    if result:
        return result
    return process

def escape_expression_field(contents: str) -> str:
    return contents.replace('${', '$/{').replace('$(', '$/(')

def clean_type_ids(cwltype: Any) -> Any:
    result = copy.deepcopy(cwltype)
    if isinstance(cwltype, cwl.ArraySchema):
        if isinstance(result.items, MutableSequence):
            for item in result.items:
                if hasattr(item, 'id'):
                    item.id = item.id.split('#')[-1]
        elif isinstance(result.items, cwl.InputRecordSchema):
            result.items.name = result.items.name.split('/')[-1]
            if result.items.fields:
                for field in result.items.fields:
                    field.name = field.name.split('/')[-1]
    elif isinstance(cwltype, cwl.InputRecordSchema):
        result.name = result.name.split('/')[-1]
        if result.fields:
            for field in result.fields:
                field.name = field.name.split('/')[-1]
    return result

def get_expression(string: str,
                  inputs: Dict[Text, Union[Dict, List, Text, None]],
                  self: Optional[Any]
                 ) -> Optional[Text]:
    if not isinstance(string, Text):
        return None
    if string.strip().startswith('${'):
        return string
    if '$(' in string:
        try:
            do_eval(string, inputs, context=self, requirements=[], outdir='', tmpdir='', resources={})
        except WorkflowException:
            return "${return "+string.strip()[2:-1]+";}"
    return None

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
    contents = escape_expression_field(contents)
    listing = [cwl.Dirent("expression.js", contents, writable=None)]
    iwdr = cwl.InitialWorkDirRequirement(listing)
    containerReq = cwl.DockerRequirement("node:slim", None, None, None, None, None)
    return cwl.CommandLineTool(
        etool.id, inputs, outputs, [iwdr],
        [containerReq], etool.label, etool.doc,
        etool.cwlVersion, ["nodejs", "expression.js"], None, None, None,
        "cwl.output.json", None, None, None, etool.extension_fields,
        etool.loadingOptions)


def traverse(process: Union[cwl.Process, cwl.CommandLineTool, cwl.ExpressionTool, cwl.Workflow], replace_etool=False, inside=False) -> Tuple[Union[cwl.Process, cwl.CommandLineTool, cwl.ExpressionTool, cwl.Workflow], bool]:
    if not inside and isinstance(process, cwl.CommandLineTool):
        process = expand_stream_shortcuts(process)
        wf_inputs = []
        wf_outputs = []
        step_inputs = []
        step_outputs = []
        if process.inputs:
            for inp in process.inputs:
                inp_id = inp.id.split('#')[-1]
                step_inputs.append(cwl.WorkflowStepInput(inp_id, None, inp_id, None, None, inp.extension_fields, inp.loadingOptions))
                wf_inputs.append(cwl.InputParameter(inp.label, inp.secondaryFiles, inp.streamable,
                    inp.doc, inp_id, inp.format, None, inp.default,
                    inp.type, inp.extension_fields, inp.loadingOptions))
        if process.outputs:
            for outp in process.outputs:
                outp_id = outp.id.split('#')[-1]
                step_outputs.append(outp_id)
                wf_outputs.append(cwl.WorkflowOutputParameter(outp.label, outp.secondaryFiles, outp.streamable, outp.doc, outp_id, None, outp.format, "main/{}".format(outp_id), None, outp.type, outp.extension_fields, outp.loadingOptions))
        step = cwl.WorkflowStep("#main", step_inputs, step_outputs, None, None, None, None, copy.deepcopy(process), None, None)
        workflow = cwl.Workflow(None, wf_inputs, wf_outputs, None, None, None, None, process.cwlVersion, [step])
        result, modified = traverse_workflow(workflow, replace_etool)
        if modified:
            return result, True
        else:
            return process, False
    if isinstance(process, cwl.ExpressionTool) and replace_etool:
        return etool_to_cltool(process), True
    if isinstance(process, cwl.Workflow):
        return traverse_workflow(process, replace_etool)
    return process, False


def load_step(step: cwl.WorkflowStep, replace_etool=False) -> bool:
    modified = False
    if isinstance(step.run, str):
        step.run, modified = traverse(cwl.load_document(step.run), replace_etool, True)
    return modified

def generate_etool_from_expr(expr: str,
                             target: Union[cwl.CommandInputParameter, cwl.InputParameter],
                             no_inputs=False,
                             self_type: Optional[Union[cwl.InputParameter, cwl.CommandInputParameter]] = None,  # if the "self" input should be a different type than the "result" output
                             extra_processes: Optional[Sequence[Union[cwl.Workflow, cwl.WorkflowStep, cwl.CommandLineTool]]] = None
                            ) -> cwl.ExpressionTool:
    inputs = yaml.comments.CommentedSeq()
    if not no_inputs:
        if not self_type:
            self_type = target
        new_type = clean_type_ids(self_type.type)
        inputs.append(cwl.InputParameter(
            self_type.label, self_type.secondaryFiles, self_type.streamable, self_type.doc, "self",
            self_type.format, None, None, new_type, self_type.extension_fields, self_type.loadingOptions))
    outputs = yaml.comments.CommentedSeq()
    outputs.append(cwl.ExpressionToolOutputParameter(
        target.label, target.secondaryFiles, target.streamable, target.doc,
        "result", None, target.format, target.type))
    expression = "${"
    if not no_inputs:
        expression += "\n  var self=inputs.self;"
    expression += """
  return {"result": function(){"""+expr[2:-2]+"""}()};
 }"""
    inlineJSReq = cwl.InlineJavascriptRequirement(find_expressionLib(extra_processes))
    return cwl.ExpressionTool(
        None, inputs, outputs, [inlineJSReq], None,
        None, None, "v1.0", expression)


def get_input_for_id(name: str, tool: Union[cwl.CommandLineTool, cwl.Workflow]) -> Optional[cwl.CommandInputParameter]:
    name = name.split('/')[-1]
    for inp in tool.inputs:
        if inp.id.split('#')[-1].split('/')[-1] == name:
            return inp
    if isinstance(tool, cwl.Workflow) and '/' in name:
        stepname, stem = name.split('/', 1)
        for step in tool.steps:
            if step.id == stepname:
                result = get_input_for_id(stem, step.run)
                if result:
                    return result
    return None

def find_expressionLib(processes: Sequence[Union[cwl.CommandLineTool, cwl.Workflow, cwl.ExpressionTool, cwl.WorkflowStep]]) -> Optional[List[str]]:
    reverse_processes = copy.copy(processes)
    reverse_processes.reverse()
    for process in reverse_processes:
        if process.requirements:
            for req in process.requirements:
                if isinstance(req, cwl.InlineJavascriptRequirement):
                    return copy.deepcopy(req.expressionLib)
    return None

def replace_expr_with_etool(expr: str,
                            name: str,
                            workflow: cwl.Workflow,
                            target: Union[cwl.CommandInputParameter, cwl.InputParameter],
                            source: Optional[Union[str, List[Any]]],
                            replace_etool=False,
                            extra_process: Union[cwl.Workflow, cwl.WorkflowStep, cwl.Process] = None,
                            source_type: Optional[cwl.CommandInputParameter] = None) -> None:
    etool = generate_etool_from_expr(expr, target, source is None, source_type, [workflow, extra_process])  # type: Union[cwl.Process, cwl.Workflow, cwl.CommandLineTool, cwl.ExpressionTool]
    if replace_etool:
        processes = [workflow]  # type: List[Union[cwl.Process, cwl.Workflow, cwl.CommandLineTool, cwl.ExpressionTool]]
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
                                if source == name:
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

def empty_inputs(process_or_step: Union[cwl.CommandLineTool, cwl.WorkflowStep, cwl.Workflow], parent: Optional[cwl.Workflow] = None) -> Dict[str, Any]:
    result = {}
    if isinstance(process_or_step, cwl.Process):
        for param in process_or_step.inputs:
            result[param.id.split('#')[-1]] = example_input(param.type)
    else:
        for param in process_or_step.in_:
            try:
                result[param.id.split('#')[-1]] = example_input(type_for_source(process_or_step.run, param.id.split('/')[-1], parent))
            except WorkflowException:
                pass
    return result

def example_input(some_type: Any) -> Any:
    if some_type == 'Directory':
        return {'class': 'Directory', 'location': 'https://www.example.com/example', 'basename': 'example', 'listing': [{'class': 'File', 'basename':'example.txt', 'size': 23, 'contents':'hoopla', 'nameroot': 'example', 'nameext': 'txt'}]}
    if some_type == 'File':
        return {'class': 'File', 'location': 'https://www.example.com/example.txt', 'basename': 'example.txt', 'size': 23, 'contents': "hoopla", 'nameroot': 'example', 'nameext': 'txt'}
    return None

def type_for_source(process: Union[cwl.CommandLineTool, cwl.Workflow, cwl.ExpressionTool], sourcenames: Union[str, List[str]], parent: Optional[cwl.Workflow] = None) -> Any:
    return param_for_source_id(process, sourcenames, parent).type

def param_for_source_id(process: Union[cwl.CommandLineTool, cwl.Workflow, cwl.ExpressionTool], sourcenames: Union[str, List[str]], parent: Optional[cwl.Workflow] = None) -> Any:
    if isinstance(sourcenames, str):
        sourcenames = [sourcenames]
    for sourcename in sourcenames:
        for param in process.inputs:
            if param.id.split('#')[-1] == sourcename.split('#')[-1]:
                return param
        targets = [process]
        if parent:
            targets.append(parent)
        for target in targets:
            if isinstance(target, cwl.Workflow):
                for inp in target.inputs:
                    if inp.id.split('#')[-1] == sourcename.split('#')[-1]:
                        return inp
                for step in target.steps:
                    if sourcename.split('/')[0] == step.id.split('#')[-1] and step.out:
                        for outp in step.out:
                            outp_id = outp if isinstance(outp, str) else outp.id
                            if outp_id.split('/')[-1] == sourcename.split('/', 1)[1]:
                                if step.run and step.run.outputs:
                                    for output in step.run.outputs:
                                        if output.id.split('#')[-1] == sourcename.split('/', 1)[1]:
                                            return output
    raise WorkflowException("param {} not found in {}\n or\n {}.".format(sourcename, yaml.round_trip_dump(cwl.save(process)), yaml.round_trip_dump(cwl.save(parent))))

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
        if param.format and get_expression(param.format, inputs, None):
            raise SourceLine(
                param.loadingOptions.original_doc, 'format',
                raise_type=WorkflowException).makeError(
                    TOPLEVEL_FORMAT_EXPR_ERROR.format(param.id.split('#')[-1]))
        if param.secondaryFiles:
            if get_expression(param.secondaryFiles, inputs, EMPTY_FILE):
                raise SourceLine(
                    param.loadingOptions.original_doc, 'secondaryFiles',
                    raise_type=WorkflowException).makeError(
                        TOPLEVEL_SF_EXPR_ERROR.format(param.id.split('#')[-1]))
            elif isinstance(param.secondaryFiles, MutableSequence):
                for index, entry in enumerate(param.secondaryFiles):
                    if get_expression(entry, inputs, EMPTY_FILE):
                        raise SourceLine(
                            param.secondaryFiles[index].loadingOptions.original_doc,
                            index, raise_type=WorkflowException).makeError(
                                "Entry {},".format(index)
                                + TOPLEVEL_SF_EXPR_ERROR.format(
                                    param.id.split('#')[-1]))

def process_workflow_reqs_and_hints(workflow: cwl.Workflow, replace_etool=False) -> bool:
    # TODO: consolidate the generated etools/cltools into a single "_expression_workflow_reqs" step
    # TODO: support resourceReq.* references to Workflow.inputs?
    #       ^ By refactoring replace_expr_etool to allow multiple inputs, and connecting all workflow inputs to the generated step
    modified = False
    inputs = empty_inputs(workflow)
    generated_res_reqs: List[Tuple[str, Union[int, str]]] = []
    generated_iwdr_reqs: List[Tuple[str, Union[int, str]]] = []
    generated_envVar_reqs: List[Tuple[str, Union[int, str]]] = []
    prop_reqs: Union[Tuple[Union[Type[cwl.EnvVarRequirement],Type[cwl.ResourceRequirement],Type[cwl.InitialWorkDirRequirement]]], Tuple] = ()
    resourceReq: Optional[cwl.ResourceRequirement] = None
    envVarReq: Optional[cwl.EnvVarRequirement] = None
    iwdr: Optional[cwl.InitialWorkDirRequirement] = None
    if workflow.requirements:
        for req in workflow.requirements:
            if req and isinstance(req, cwl.EnvVarRequirement):
                if req.envDef:
                    for index, envDef in enumerate(req.envDef):
                        if envDef.envValue:
                            expression = get_expression(envDef.envValue, inputs, None)
                            if expression:
                                modified = True
                                target = cwl.InputParameter(None, None, None, None, None, None, None, None, "string")
                                etool_id = "_expression_workflow_EnvVarRequirement_{}".format(index)
                                replace_expr_with_etool(
                                    expression,
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
                    if this_attr:
                        expression = get_expression(this_attr, inputs, None)
                        if expression:
                            modified = True
                            target = cwl.InputParameter(None, None, None, None, None, None, None, None, "long")
                            etool_id = "_expression_workflow_ResourceRequirement_{}".format(attr)
                            replace_expr_with_etool(
                                expression,
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
                    if isinstance(req.listing, str):
                        expression = get_expression(req.listing, inputs, None)
                        if expression:
                            modified = True
                            target = cwl.InputParameter(None, None, None, None, None, None, None, None,
                                    cwl.InputArraySchema(['File', 'Directory'], 'array', None, None))
                            etool_id = "_expression_workflow_InitialWorkDirRequirement"
                            replace_expr_with_etool(
                                expression,
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
                            expression = get_expression(entry, inputs, None)
                            if expression:
                                modified = True
                                target = cwl.InputParameter(None, None, None, None, None, None, None, None,
                                        cwl.InputArraySchema(['File', 'Directory'], 'array', None, None))
                                etool_id = "_expression_workflow_InitialWorkDirRequirement_{}".format(index)
                                replace_expr_with_etool(
                                    expression,
                                    etool_id,
                                    workflow,
                                    target,
                                    None,
                                    replace_etool)
                                iwdr.listing[index] = "$(inputs._iwdr_listing_{}".format(index)
                                generated_iwdr_reqs.append((etool_id, index))
                            elif isinstance(entry, cwl.Dirent):
                                if entry.entry:
                                    expression = get_expression(entry.entry, inputs, None)
                                    if expression:
                                        modified = True
                                        target = cwl.InputParameter(None, None, None, None, None, None, None, None,
                                                ["File", "Directory"])
                                        etool_id = "_expression_workflow_InitialWorkDirRequirement_{}".format(index)
                                        expression = '${return {"class": "File", "basename": "'+entry.entryname+'", "contents": (function(){'+expression[2:-1]+'})() }; }'
                                        replace_expr_with_etool(
                                            expression,
                                            etool_id,
                                            workflow,
                                            target,
                                            None,
                                            replace_etool)
                                        iwdr.listing[index] = "$(inputs._iwdr_listing_{}".format(index)
                                        generated_iwdr_reqs.append((etool_id, index))
                                elif entry.entryname:
                                    expression = get_expression(entry.entryname, inputs, None)
                                    if expression:
                                        modified = True
                                        target = cwl.InputParameter(None, None, None, None, None, None, None, None, str)
                                        etool_id = "_expression_workflow_InitialWorkDirRequirement_{}".format(index)
                                        replace_expr_with_etool(
                                            expression,
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
                for entry in generated_iwdr_reqs:
                    step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, "_iwdr_listing_{}".format(index), None, None))
            else:
                step.in_.append(cwl.WorkflowStepInput("_expression_workflow_InitialWorkDirRequirement/result", None, "_iwdr_listing", None, None))


    if workflow.requirements:
        workflow.requirements[:] = [
            x for x  in workflow.requirements
            if not isinstance(x, prop_reqs)]
    return modified

def process_level_reqs(process: cwl.CommandLineTool, step: cwl.WorkflowStep, parent: cwl.Workflow, replace_etool=False) -> bool:
    # This is for reqs inside a Process (CommandLineTool, ExpressionTool)
    # differences from process_workflow_reqs_and_hints() are:
    # - the name of the generated ETools/CTools contain the name of the step, not "workflow"
    # - Generated ETools/CTools are adjacent steps
    # - Replace the CWL Expression inplace with a CWL parameter reference
    # - Don't create a new Requirement, nor delete the existing Requirement
    # - the Process is passed to replace_expr_with_etool for later searching for JS expressionLibs
    # - in addition to adding the input to the step for the ETool/CTool result, add it to the Process.inputs as well
    if not process.requirements:
        return False
    modified = False
    target_process = step.run
    inputs = empty_inputs(process)
    generated_res_reqs: List[Tuple[str, str]] = []
    generated_iwdr_reqs: List[Tuple[str, Union[int, str], Any]] = []
    generated_envVar_reqs: List[Tuple[str, Union[int, str]]] = []
    step_name = step.id.split('#',1)[1]
    for req_index, req in enumerate(process.requirements):
        if req and isinstance(req, cwl.EnvVarRequirement):
            if req.envDef:
                for env_index, envDef in enumerate(req.envDef):
                    if envDef.envValue:
                        expression = get_expression(envDef.envValue, inputs, None)
                        if expression:
                            modified = True
                            target = cwl.InputParameter(None, None, None, None, None, None, None, None, "string")
                            etool_id = "_expression_{}_EnvVarRequirement_{}".format(step_name, env_index)
                            replace_expr_with_etool(
                                expression,
                                etool_id,
                                parent,
                                target,
                                None,
                                replace_etool,
                                process)
                            target_process.requirements[req_index][env_index].envValue = "$(inputs._envDef{})".format(env_index)
                            generated_envVar_reqs.append((etool_id, env_index))
        if req and isinstance(req, cwl.ResourceRequirement):
            for attr in cwl.ResourceRequirement.attrs:
                this_attr = getattr(req, attr, None)
                if this_attr:
                    expression = get_expression(this_attr, inputs, None)
                    if expression:
                        modified = True
                        target = cwl.InputParameter(None, None, None, None, None, None, None, None, "long")
                        etool_id = "_expression_{}_ResourceRequirement_{}".format(step_name, attr)
                        replace_clt_hintreq_expr_with_etool(
                            expression,
                            etool_id,
                            parent,
                            target,
                            step,
                            replace_etool)
                        setattr(target_process.requirements[req_index], attr, "$(inputs._{})".format(attr))
                        generated_res_reqs.append((etool_id, attr))

        if not SKIP_COMMAND_LINE2 and req and isinstance(req, cwl.InitialWorkDirRequirement):
            if req.listing:
                if isinstance(req.listing, str):
                    expression = get_expression(req.listing, inputs, None)
                    if expression:
                        modified = True
                        target_type = cwl.InputArraySchema(['File', 'Directory'], 'array', None, None)
                        target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                        etool_id = "_expression_{}_InitialWorkDirRequirement".format(step_name)
                        replace_expr_with_etool(
                            expression,
                            etool_id,
                            parent,
                            target,
                            None,
                            replace_etool,
                            process)
                        target_process.requirements[req_index].listing = "$(inputs._iwdr_listing)",
                        step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, "_iwdr_listing", None, None))
                        add_input_to_process(target_process, "_iwdr_listing", target_type, process.loadingOptions)
                else:
                    for listing_index, entry in enumerate(req.listing):
                        expression = get_expression(entry, inputs, None)
                        if expression:
                            modified = True
                            target_type = cwl.InputArraySchema(['File', 'Directory'], 'array', None, None)
                            target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                            etool_id = "_expression_{}_InitialWorkDirRequirement_{}".format(step_name, listing_index)
                            replace_expr_with_etool(
                                expression,
                                etool_id,
                                parent,
                                target,
                                None,
                                replace_etool,
                                process)
                            target_process.requirements[req_index].listing[listing_index] = "$(inputs._iwdr_listing_{}".format(listing_index)
                            generated_iwdr_reqs.append((etool_id, listing_index, target_type))
                        elif isinstance(entry, cwl.Dirent):
                            if entry.entry:
                                expression = get_expression(entry.entry, inputs, None)
                                if expression:
                                    modified = True
                                    entryname_expr = get_expression(entry.entryname, inputs, None)
                                    entryname = entry.entryname if entryname_expr else '"{}"'.format(entry.entryname)
                                    d_target_type = ["File", "Directory"]
                                    target = cwl.InputParameter(None, None, None, None, None, None, None, None, d_target_type)
                                    etool_id = "_expression_{}_InitialWorkDirRequirement_{}".format(step_name, listing_index)

                                    expression = "${var result; var entryname = " + entryname + "; var entry = " + entry.entry[2:-1] + """;
if (typeof entry === 'string' || entry instanceof String) {
result = {"class": "File", "basename": entryname, "contents": entry} ;
if (typeof entryname === 'string' || entryname instanceof String) {
result.basename = entryname ;
}
} else {
result = entry ;
}
return result; }"""
                                    replace_clt_hintreq_expr_with_etool(
                                        expression,
                                        etool_id,
                                        parent,
                                        target,
                                        step,
                                        replace_etool)
                                    target_process.requirements[req_index].listing[listing_index].entry = "$(inputs._iwdr_listing_{})".format(listing_index)
                                    generated_iwdr_reqs.append((etool_id, listing_index, d_target_type))
                            elif entry.entryname:
                                expression = get_expression(entry.entryname, inputs, None)
                                if expression:
                                    modified = True
                                    target = cwl.InputParameter(None, None, None, None, None, None, None, None, "string")
                                    etool_id = "_expression_{}_InitialWorkDirRequirement_{}".format(step_name, listing_index)
                                    replace_expr_with_etool(
                                        expression,
                                        etool_id,
                                        parent,
                                        target,
                                        None,
                                        replace_etool,
                                        process)
                                    target_process.requirements[req_index].listing[listing_index].entryname = "$(inputs._iwdr_listing_{})".format(listing_index)
                                    generated_iwdr_reqs.append((etool_id, listing_index, "string"))
    for entry in generated_envVar_reqs:
        name = "_envDef{}".format(entry[1])
        step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, name, None, None))
        add_input_to_process(target_process, name, "string", process.loadingOptions)
    for entry in generated_res_reqs:
        name = "_{}".format(entry[1])
        step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, name, None, None))
        add_input_to_process(target_process, name, "long", process.loadingOptions)
    for entry in generated_iwdr_reqs:
        name = "_iwdr_listing_{}".format(entry[1])
        step.in_.append(cwl.WorkflowStepInput("{}/result".format(entry[0]), None, name, None, None))
        add_input_to_process(target_process, name, entry[2], process.loadingOptions)
    return modified

def add_input_to_process(process: cwl.Process, name: str, inptype: Any, loadingOptions: cwl.LoadingOptions):
    if isinstance(process, cwl.CommandLineTool):
        process.inputs.append(cwl.CommandInputParameter(
            None, None, None, None, name, None, None, None, inptype,
            loadingOptions=loadingOptions))

def traverse_CommandLineTool(clt: cwl.CommandLineTool, parent: cwl.Workflow, step=cwl.WorkflowStep, replace_etool=False) -> bool:
    modified = False
    # don't modifiy clt, modify step.run
    target_clt = step.run
    inputs = empty_inputs(clt)
    step_id = step.id.split('#')[-1]
    if clt.arguments and not SKIP_COMMAND_LINE:
        for index, arg in enumerate(clt.arguments):
            if isinstance(arg, str):
                expression = get_expression(arg, inputs, None)
                if expression:
                    modified = True
                    inp_id = "_arguments_{}".format(index)
                    etool_id = "_expression_{}{}".format(step_id, inp_id)
                    target_type = "Any"
                    target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                    replace_step_clt_expr_with_etool(
                        expression,
                        etool_id,
                        parent,
                        target,
                        step,
                        replace_etool)
                    target_clt.arguments[index].valueFrom = "$(inputs.{})".format(inp_id)
                    target_clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, target_type))
                    step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
                    remove_JSReq(target_clt)
            elif isinstance(arg, cwl.CommandLineBinding) and arg.valueFrom:
                expression = get_expression(arg.valueFrom, inputs, None)
                if expression:
                    modified = True
                    inp_id = "_arguments_{}".format(index)
                    etool_id = "_expression_{}{}".format(step_id, inp_id)
                    target_type = "Any"
                    target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                    replace_step_clt_expr_with_etool(
                        expression,
                        etool_id,
                        parent,
                        target,
                        step,
                        replace_etool)
                    target_clt.arguments[index].valueFrom = "$(inputs.{})".format(inp_id)
                    target_clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, target_type))
                    step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
                    remove_JSReq(target_clt)
    for streamtype in 'stdout', 'stderr':  # add 'stdin' for v1.1 version
        stream_value = getattr(clt, streamtype)
        if stream_value:
            expression = get_expression(stream_value, inputs, None)
            if expression:
                modified = True
                inp_id = "_{}".format(streamtype)
                etool_id = "_expression_{}{}".format(step_id, inp_id)
                target_type = "string"
                target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                replace_step_clt_expr_with_etool(
                    expression,
                    etool_id,
                    parent,
                    target,
                    step,
                    replace_etool)
                setattr(target_clt, streamtype, "$(inputs.{})".format(inp_id))
                target_clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, target_type))
                step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
    for inp in clt.inputs:
        if not SKIP_COMMAND_LINE and inp.inputBinding and inp.inputBinding.valueFrom:
            expression = get_expression(inp.inputBinding.valueFrom, inputs, example_input(inp.type))
            if expression:
                modified = True
                self_id = inp.id.split('#')[-1]
                inp_id = "_{}_valueFrom".format(self_id)
                etool_id = "_expression_{}{}".format(step_id, inp_id)
                replace_step_clt_expr_with_etool(
                    expression,
                    etool_id,
                    parent,
                    inp,
                    step,
                    replace_etool,
                    self_id)
                inp.inputBinding.valueFrom = "$(inputs.{})".format(inp_id)
                target_clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, inp.type))
                step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
    for outp in clt.outputs:
        if outp.outputBinding:
            if outp.outputBinding.glob:
                expression = get_expression(outp.outputBinding.glob, inputs, None)
                if expression:
                    modified = True
                    inp_id = "_{}_glob".format(outp.id.split('#')[-1])
                    etool_id = "_expression_{}{}".format(step_id, inp_id)
                    target_type = ["string", cwl.ArraySchema("string", "array")]
                    target = cwl.InputParameter(None, None, None, None, None, None, None, None, target_type)
                    replace_step_clt_expr_with_etool(
                        expression,
                        etool_id,
                        parent,
                        target,
                        step,
                        replace_etool)
                    outp.outputBinding.glob = "$(inputs.{})".format(inp_id)
                    target_clt.inputs.append(cwl.CommandInputParameter(None, None, None, None, inp_id, None, None, None, target_type))
                    step.in_.append(cwl.WorkflowStepInput("{}/result".format(etool_id), None, inp_id, None, None))
            if outp.outputBinding.outputEval and not SKIP_COMMAND_LINE2:
                self = [{"class": "File", "basename": "base.name", "nameroot": "base", "nameext": "name", "path": "/tmp/base.name", "dirname": "/tmp" }]
                if outp.outputBinding.loadContents:
                    self[0]["contents"] = "stuff"
                expression = get_expression(outp.outputBinding.outputEval, inputs, self)
                if expression:
                    modified = True
                    outp_id = outp.id.split('#')[-1]
                    inp_id = "_{}_outputEval".format(outp_id)
                    etool_id = "expression{}".format(inp_id)
                    sub_wf_outputs = cltool_step_outputs_to_workflow_outputs(step, etool_id, outp_id)
                    self_type = cwl.InputParameter(
                        None, None, None, None, None, None, None, None,
                        cwl.InputArraySchema("File", "array", None, None))
                    etool = generate_etool_from_expr(expression, outp, False, self_type, [clt, step, parent])
                    if outp.outputBinding.loadContents:
                        etool.inputs[0].type.inputBinding = cwl.CommandLineBinding(True, None, None, None, None, None, None)
                    etool.inputs.extend(cltool_inputs_to_etool_inputs(clt))
                    sub_wf_inputs = cltool_inputs_to_etool_inputs(clt)
                    orig_step_inputs = copy.deepcopy(step.in_)
                    for orig_step_input in orig_step_inputs:
                        orig_step_input.id = orig_step_input.id.split('/')[-1]
                        if isinstance(orig_step_input.source, MutableSequence):
                            for index, source in enumerate(orig_step_input.source):
                                orig_step_input.source[index] = source.split('#')[-1]
                        else:
                            orig_step_input.source = orig_step_input.source.split('#')[-1]
                    orig_step_inputs[:] = [
                        x for x  in orig_step_inputs
                        if not x.id.startswith('_')]
                    for inp in orig_step_inputs:
                        inp.source = inp.id
                        inp.linkMerge = None
                    if replace_etool:
                        processes = [parent]
                        final_etool: Union[cwl.CommandLineTool, cwl.ExpressionTool] = etool_to_cltool(etool, find_expressionLib(processes))
                    else:
                        final_etool = etool
                    etool_step = cwl.WorkflowStep(
                        etool_id,
                        orig_step_inputs,
                        [cwl.WorkflowStepOutput("result")], None, None, None, None, final_etool, None, step.scatterMethod)
                    new_clt_step = copy.copy(step)  # a deepcopy would be convienant, but params2.cwl gives it problems
                    new_clt_step.id = new_clt_step.id.split('#')[-1]
                    new_clt_step.run = copy.copy(step.run)
                    new_clt_step.run.id = None
                    remove_JSReq(new_clt_step.run)
                    for new_outp in new_clt_step.run.outputs:
                        if new_outp.id.split('#')[-1] == outp_id:
                            if new_outp.outputBinding:
                                new_outp.outputBinding.outputEval = None
                                new_outp.outputBinding.loadContents = None
                            new_outp.type = cwl.CommandOutputArraySchema("File", "array", None, None)
                    new_clt_step.in_ = copy.deepcopy(step.in_)
                    for inp in new_clt_step.in_:
                        inp.id = inp.id.split('/')[-1]
                        inp.source = inp.id
                        inp.linkMerge = None
                    for index, out in enumerate(new_clt_step.out):
                        new_clt_step.out[index] = out.split('/')[-1]
                    for tool_inp in new_clt_step.run.inputs:
                        tool_inp.id = tool_inp.id.split('#')[-1]
                    for tool_out in new_clt_step.run.outputs:
                        tool_out.id = tool_out.id.split('#')[-1]
                    sub_wf_steps = [new_clt_step, etool_step]
                    sub_workflow = cwl.Workflow(None, sub_wf_inputs, sub_wf_outputs, None, None, None, None, parent.cwlVersion, sub_wf_steps)
                    if step.scatter:
                        new_clt_step.scatter = None
                    step.run = sub_workflow 
                    rename_step_source(sub_workflow, "{}/{}".format(step_id, outp_id), "{}/result".format(etool_id))
                    orig_step_inputs.append(cwl.WorkflowStepInput("{}/{}".format(step_id, outp_id), None, "self", None, None))
                    if not parent.requirements:
                        parent.requirements = [cwl.SubworkflowFeatureRequirement()]
                    else:
                        has_sub_wf_req = False
                        for req in parent.requirements:
                            if isinstance(req, cwl.SubworkflowFeatureRequirement):
                                has_sub_wf_req = True
                        if not has_sub_wf_req:
                            parent.requirements.append(cwl.SubworkflowFeatureRequirement())
    return modified



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

def remove_JSReq(process: Union[cwl.CommandLineTool, cwl.WorkflowStep, cwl.Workflow]) -> None:
    if SKIP_COMMAND_LINE and isinstance(process, cwl.CommandLineTool):
        return
    if process.hints:
        process.hints[:] = [hint for hint in process.hints if not isinstance(hint, cwl.InlineJavascriptRequirement)]
        if not process.hints:
            process.hints = None
    if process.requirements:
        process.requirements[:] = [req for req in process.requirements if not isinstance(req, cwl.InlineJavascriptRequirement)]
        if not process.requirements:
            process.requirements = None

def replace_step_clt_expr_with_etool(expr: str,
                                     name: str,
                                     workflow: cwl.Workflow,
                                     target: cwl.InputParameter,
                                     step: cwl.WorkflowStep,
                                     replace_etool=False,
                                     self_name: Optional[str]=None,
                                    ) -> None:
    etool_inputs = cltool_inputs_to_etool_inputs(step.run)
    temp_etool = generate_etool_from_expr2(expr, target, etool_inputs, self_name, step.run, [workflow])
    if replace_etool:
        processes = [workflow]
        etool: Union[cwl.ExpressionTool, cwl.CommandLineTool] = etool_to_cltool(temp_etool, find_expressionLib(processes))
    else:
        etool = temp_etool
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

    
def replace_clt_hintreq_expr_with_etool(expr: str,
                                        name: str,
                                        workflow: cwl.Workflow,
                                        target: cwl.InputParameter,
                                        step: cwl.WorkflowStep,
                                        replace_etool=False,
                                        self_name: Optional[str]=None,
                                        ) -> Union[cwl.CommandLineTool, cwl.ExpressionTool]:
    # Same as replace_step_clt_expr_with_etool or different?
    etool_inputs = cltool_inputs_to_etool_inputs(step.run)
    temp_etool = generate_etool_from_expr2(expr, target, etool_inputs, self_name, step.run, [workflow])
    if replace_etool:
        processes = [workflow]
        etool: Union[cwl.CommandLineTool, cwl.ExpressionTool] = etool_to_cltool(temp_etool, find_expressionLib(processes))
    else:
        etool = temp_etool
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
    return etool


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


def cltool_step_outputs_to_workflow_outputs(cltool_step: cwl.WorkflowStep, etool_step_id: Text, etool_out_id) -> List[cwl.OutputParameter]:
    outputs = yaml.comments.CommentedSeq()
    default_step_id = cltool_step.id.split('#')[-1]
    if cltool_step.run.outputs:
        for clt_out in cltool_step.run.outputs:
            clt_out_id = clt_out.id.split('#')[-1].split('/')[-1]
            if clt_out_id == etool_out_id:
                outputSource = "{}/result".format(etool_step_id)
            else:
                outputSource = "{}/{}".format(default_step_id, clt_out_id)
            if not clt_out_id.startswith('_'):
                outputs.append(cwl.WorkflowOutputParameter(
                    clt_out.label, clt_out.secondaryFiles, clt_out.streamable,
                    clt_out.doc, clt_out_id, None, clt_out.format, outputSource, None,
                    clt_out.type, clt_out.extension_fields, clt_out.loadingOptions))
    return outputs



def generate_etool_from_expr2(expr: str,
                              target: cwl.InputParameter,
                              inputs: Sequence[Union[cwl.InputParameter, cwl.CommandInputParameter]],
                              self_name: Optional[str] = None,
                              process: Optional[Union[cwl.CommandLineTool, cwl.ExpressionTool]] = None,
                              extra_processes: Optional[Sequence[Union[cwl.Workflow, cwl.WorkflowStep, cwl.CommandLineTool]]] = None
                             ) -> cwl.ExpressionTool:
    outputs = yaml.comments.CommentedSeq()
    outputs.append(cwl.ExpressionToolOutputParameter(
        target.label, target.secondaryFiles, target.streamable, target.doc,
        "result", None, target.format, target.type))
    expression = "${"
    if self_name:
        expression += "\n  var self=inputs.{};".format(self_name)
    expression += """
  return {"result": function(){"""+expr[2:-2]+"""}()};
 }"""
    hints = None
    procs = []
    if process:
        procs.append(process)
    if extra_processes:
        procs.extend(extra_processes)
    inlineJSReq = cwl.InlineJavascriptRequirement(find_expressionLib(procs))
    reqs = [inlineJSReq]
    if process:
        if process.hints:
            hints = copy.deepcopy(process.hints)
            hints[:] = [x for x in hints if not isinstance(x, cwl.InitialWorkDirRequirement)]
        if process.requirements:
            reqs.extend(copy.deepcopy(process.requirements))
            reqs[:] = [x for x in reqs if not isinstance(x, cwl.InitialWorkDirRequirement)]
    return cwl.ExpressionTool(
        None, inputs, outputs, reqs, None,
        None, None, "v1.0", expression)


def traverse_step(step: cwl.WorkflowStep, parent: cwl.Workflow, replace_etool=False) -> bool:
    modified = False
    inputs = empty_inputs(step, parent)
    step_id = step.id.split('#')[-1]
    original_process = copy.deepcopy(step.run)
    original_step_ins = copy.deepcopy(step.in_)
    for inp in step.in_:
        if inp.valueFrom:
            if not inp.source:
                self = None
            else:
                if isinstance(inp.source, MutableSequence):
                    self = []
                    for source in inp.source:
                        if not step.scatter:
                            self.append(example_input(type_for_source(parent, source.split('#')[-1])))
                        else:
                            self.append(example_input(type_for_source(parent, source).type))
                else:
                    if not step.scatter:
                        self = example_input(type_for_source(parent, inp.source.split('#')[-1]))
                    else:
                        self = example_input(type_for_source(parent, inp.source).type)
            expression = get_expression(inp.valueFrom, inputs, self)
            if expression:
                modified = True
                etool_id = "_expression_{}_{}".format(step_id, inp.id.split('/')[-1])
                target = get_input_for_id(inp.id, original_process)
                if not target:
                    raise Exception("target not found")
                input_source_id = None
                source_type = None
                if inp.source:
                    if isinstance(inp.source, MutableSequence):
                        input_source_id = []
                        source_types: List[cwl.InputParameter] = []
                        for source in inp.source:
                            source_id = source.split('#')[-1]
                            input_source_id.append(source_id)
                            temp_type = param_for_source_id(step.run, source_id, parent).type
                            if temp_type not in source_types:
                                source_types.append(temp_type)
                        source_type = cwl.InputParameter(None, None, None, None, None, None, None, None, cwl.ArraySchema(source_types, 'array'))
                    else:
                        input_source_id = inp.source.split('#')[-1]
                        source_type = param_for_source_id(step.run, input_source_id, parent)
                #target.id = target.id.split('#')[-1]
                if isinstance(original_process, cwl.ExpressionTool):
                    found_JSReq = False
                    reqs: List[cwl.ProcessRequirement] = []
                    if original_process.hints:
                        reqs.extend(original_process.hints)
                    if original_process.requirements:
                        reqs.extend(original_process.requirements)
                    for req in reqs:
                        if isinstance(req, cwl.InlineJavascriptRequirement):
                            found_JSReq = True
                    if not found_JSReq:
                        if not step.run.requirements:
                            step.run.requirements = []
                        expr_lib = find_expressionLib([parent])
                        step.run.requirements.append(cwl.InlineJavascriptRequirement(expr_lib))
                replace_step_valueFrom_expr_with_etool(
                    expression,
                    etool_id,
                    parent,
                    target,
                    step,
                    inp,
                    original_process,
                    original_step_ins,
                    input_source_id,
                    replace_etool,
                    source_type)
                inp.valueFrom = None
                inp.source = "{}/result".format(etool_id)
    # TODO: skip or special process for sub workflows?
    process_modified = process_level_reqs(original_process, step, parent, replace_etool)
    if process_modified:
        modified = True
    if isinstance(original_process, cwl.CommandLineTool):
        clt_modified = traverse_CommandLineTool(original_process, parent, step, replace_etool)
        if clt_modified:
            modified = True
    return modified

def workflow_step_to_InputParameters(step_ins: List[cwl.WorkflowStepInput], parent: cwl.Workflow, except_in_id: str) -> List[cwl.InputParameter]:
    params = []
    for inp in step_ins:
        inp_id = inp.id.split('#')[-1].split('/')[-1]
        if inp.source and inp_id != except_in_id:
            param = copy.deepcopy(param_for_source_id(parent, sourcenames=inp.source))
            param.id = inp_id
            param.type = clean_type_ids(param.type)
            params.append(param)
    return params

def replace_step_valueFrom_expr_with_etool(expr: str,
                                           name: str,
                                           workflow: cwl.Workflow,
                                           target: Union[cwl.CommandInputParameter, cwl.InputParameter],
                                           step: cwl.WorkflowStep,
                                           step_inp: cwl.WorkflowStepInput,
                                           original_process: Union[cwl.CommandLineTool, cwl.ExpressionTool],
                                           original_step_ins: List[cwl.WorkflowStepInput],
                                           source: Union[str, List[Any]],
                                           replace_etool=False,
                                           source_type: Optional[Union[cwl.InputParameter, cwl.CommandInputParameter]] = None) -> None:
    step_inp_id = step_inp.id.split('/')[-1]
    etool_inputs = workflow_step_to_InputParameters(original_step_ins, workflow, step_inp_id)
    if source:
        source_param = cwl.InputParameter(None, None, None, None, 'self', None, None, None, 'Any')
        # TODO: would be nicer to derive a proper type; but in the face of linkMerge, this is easier for now
        etool_inputs.append(source_param)
    temp_etool = generate_etool_from_expr2(expr, target, etool_inputs, "self" if source else None, original_process, [workflow, step])
    if replace_etool:
        processes = [workflow, step]  # type: List[Union[cwl.Workflow, cwl.CommandLineTool, cwl.ExpressionTool, cwl.WorkflowStep]]
        cltool = etool_to_cltool(temp_etool, find_expressionLib(processes))
        etool = cltool  # type: Union[cwl.ExpressionTool, cwl.CommandLineTool]
    else:
        etool = temp_etool
    wf_step_inputs = copy.deepcopy(original_step_ins)
    if source:
        wf_step_inputs.append(cwl.WorkflowStepInput(step_inp.source, None, "self", None, None))
    for wf_step_input in wf_step_inputs:
        wf_step_input.id = wf_step_input.id.split('/')[-1]
        if wf_step_input.valueFrom:
            wf_step_input.valueFrom = None
        if wf_step_input.source:
            if isinstance(wf_step_input.source, MutableSequence):
                for index, inp_source in enumerate(wf_step_input.source):
                    wf_step_input.source[index] = inp_source.split('#')[-1]
            else:
                wf_step_input.source = wf_step_input.source.split('#')[-1]
    wf_step_inputs[:] = [
        x for x  in wf_step_inputs
        if not (x.id.startswith('_') or x.id.endswith(step_inp_id))]
    scatter = copy.deepcopy(step.scatter)
    if isinstance(scatter, str):
        scatter = [scatter]
    if isinstance(scatter, MutableSequence):
        for index, entry in enumerate(scatter):
            scatter[index] = entry.split('/')[-1]
    if scatter and step_inp_id in scatter:
        scatter = ['self']
    # do we still need to scatter?
    else:
        scatter = None
    workflow.steps.append(cwl.WorkflowStep(
        name,
        wf_step_inputs,
        [cwl.WorkflowStepOutput("result")], None, None, None, None, etool, scatter, step.scatterMethod))

def traverse_workflow(workflow: cwl.Workflow, replace_etool=False) -> Tuple[cwl.Workflow, bool]:
    modified = False
    for index, step in enumerate(workflow.steps):
        if isinstance(step.run, cwl.ExpressionTool) and replace_etool:
            workflow.steps[index].run = etool_to_cltool(step.run)
            modified = True
        else:
            step_modified = load_step(step, replace_etool)
            if step_modified:
                modified = True
    for step in workflow.steps:
        if not step.id.startswith('_expression'):
            step_modified = traverse_step(step, workflow)
            if step_modified:
                modified = True
    process_workflow_inputs_and_outputs(workflow, replace_etool)
    process_workflow_reqs_and_hints(workflow, replace_etool)
    if workflow.requirements:
        workflow.requirements[:] = [
            x for x  in workflow.requirements
            if not isinstance(x, (cwl.InlineJavascriptRequirement,
                                  cwl.StepInputExpressionRequirement))]
    else:
        workflow.requirements = None
    return workflow, modified


if __name__ == "__main__":
    sys.exit(main())
