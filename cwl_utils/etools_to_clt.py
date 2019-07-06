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

def generate_etool_from_expr(expr: str, target: cwl.Parameter ) -> cwl.ExpressionTool:
    inputs = yaml.comments.CommentedSeq()
    inputs.append(cwl.InputParameter(
        target.label, target.secondaryFiles, target.streamable, target.doc, "self",
        target.format, None, None, target.type, target.extension_fields, target.loadingOptions))
    outputs = yaml.comments.CommentedSeq()
    outputs.append(cwl.ExpressionToolOutputParameter(
        target.label, target.secondaryFiles, target.streamable, target.doc,
        "result", None, target.format, target.type))
    expression = """${
  var self=inputs.self;
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
                            source: str,
                            target: cwl.Parameter,
                            replace_etool=False,
                            extra_process: cwl.Process = None) -> None:
    etool = generate_etool_from_expr(expr, target)
    if replace_etool:
        processes = [workflow]
        if extra_process:
            processes.append(extra_process)
        etool = etool_to_cltool(etool, find_expressionLib(processes))
    workflow.steps.append(cwl.WorkflowStep(
        name,
        [cwl.WorkflowStepInput(source, None, "self", None, None)],
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
                    inp.source.split('#')[-1],
                    get_input_for_id(inp.id, step.run),
                    replace_etool,
                    step)
                inp.valueFrom = None
                inp.source = "{}/result".format(etool_id)
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
                param_copy.id.split('#')[-1],
                param_copy,
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
                param_copy.id.split('#')[-1],
                param_copy,
                replace_etool=replace_etool)
            param.secondaryFiles = None


    workflow.requirements[:] = [
        x for x  in workflow.requirements
        if not isinstance(x, (cwl.InlineJavascriptRequirement,
                              cwl.StepInputExpressionRequirement))]
    if not workflow.requirements:
        workflow.requirements = None
    return workflow


if __name__ == "__main__":
    sys.exit(main())
