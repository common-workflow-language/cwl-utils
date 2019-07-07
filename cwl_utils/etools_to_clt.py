#!/usr/bin/env python3
import sys
import copy
import cwl_utils.parser_v1_0 as cwl
from ruamel import yaml
from typing import List, MutableSequence, Optional

def main():
    top = cwl.load_document(sys.argv[1])
    result = traverse(top, False)
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
    return contents.replace('${', '$/{')

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

def generate_etool_from_expr(expr: str, target: cwl.Parameter, no_inputs=False) -> cwl.ExpressionTool:
    inputs = yaml.comments.CommentedSeq()
    if not no_inputs:
        inputs.append(cwl.InputParameter(
            target.label, target.secondaryFiles, target.streamable, target.doc, "self",
            target.format, None, None, target.type, target.extension_fields, target.loadingOptions))
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
    for process in processes:
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

def process_workflow_inputs_and_outputs(workflow: cwl.Workflow, replace_etool) -> None:
    for param in workflow.inputs:
        if param.format and param.format.startswith('${'):
            param_copy = copy.deepcopy(param)
            param_copy.format = None
            etool_id = "_expression_workflow_input_{}_format".format(param.id.split('#')[-1])
            replace_wf_input_ref_with_step_output(workflow, param.id, "{}/result".format(etool_id))
            replace_expr_with_etool(
                """${
  self.format=function(){"""+param.format[2:-1]+"""};
  return self;""",
                etool_id,
                workflow,
                param_copy,
                param_copy.id.split('#')[-1],
                replace_etool=replace_etool)
            param.format = None
        if param.secondaryFiles and param.secondaryFiles.startswith('${'):
            # TODO: might be an array of type [str, Expression]
            param_copy = copy.deepcopy(param)
            param_copy.secondaryFiles = None
            etool_id = "_expression_workflow_input_{}_secondaryFiles".format(param.id.split('#')[-1])
            replace_wf_input_ref_with_step_output(workflow, param.id, "{}/result".format(etool_id))
            replace_expr_with_etool(
                """${
  self.secondaryFiles=function(){"""+param.secondaryFiles[2:-1]+"""};
  return self;""",
                etool_id,
                workflow,
                param_copy,
                param_copy.id.split('#')[-1],
                replace_etool=replace_etool)
            param.secondaryFiles = None

def process_workflow_reqs_and_hints(workflow: cwl.Workflow, replace_etool=False) -> None:
    # TODO: consolidate the generated etools/cltools into a single "_expression_workflow_reqs" step
    # TODO: support resourceReq.* references to Workflow.inputs?
    #       ^ By refactoring replace_expr_etool to allow multiple inputs, and connecting all workflow inputs to the generated step
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
                        if envDef.envValue and envDef.envValue.startswith("${"):
                            target = cwl.InputParameter(None, None, None, None, None, None, None, None, "str")
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
                            envVarReq.envDef[index] = "$(inputs._envDef{})".format(index)
                            generated_envVar_reqs.append((etool_id, index))
            if req and isinstance(req, cwl.ResourceRequirement):
                for attr in cwl.ResourceRequirement.attrs:
                    this_attr = getattr(req, attr, None)
                    if this_attr and this_attr.startswith("${"):
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
                    if isinstance(req.listing, str) and req.listing.startswith("${"):
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
                            if entry.startswith("${"):
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
                                if entry.entry and entry.entry.startswith('${'):
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
                                elif entry.entryname and entry.entryname.startswith('${'):
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



def traverse_workflow(workflow: cwl.Workflow, replace_etool=False) -> cwl.Workflow:
    for index, step in enumerate(workflow.steps):
        if isinstance(step.run, cwl.ExpressionTool) and replace_etool:
            workflow.steps[index].run = etool_to_cltool(step.run)
        else:
            load_step(step)
    for index, step in enumerate(workflow.steps):
        for inp in step.in_:
            if inp.valueFrom and inp.valueFrom.startswith('${'):
                etool_id = "_expression_{}_{}".format(step.id.split('#')[-1], inp.id.split('/')[-1])
                replace_expr_with_etool(
                    inp.valueFrom,
                    etool_id,
                    workflow,
                    get_input_for_id(inp.id, step.run),
                    inp.source.split('#')[-1],
                    replace_etool,
                    step)
                inp.valueFrom = None
                inp.source = "{}/result".format(etool_id)
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
