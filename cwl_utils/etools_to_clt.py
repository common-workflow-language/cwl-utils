#!/usr/bin/env python3
import sys
import cwl_utils.parser_v1_0 as cwl
from ruamel import yaml

def main():
    top = cwl.load_document(sys.argv[1])
    result = traverse(top, True)
    result_json = cwl.save(
        result,
        base_url=result.loadingOptions.fileuri)
    #   ^^ Setting the base_url and keeping the default value
    #      for relative_uris=True means that the IDs in the generated
    #      JSON/YAML are kept clean of the path to the input document
    yaml.scalarstring.walk_tree(result_json)
    # ^ converts multine line strings to nice multiline YAML
    print("#!/usr/bin/env cwl-runner")  # todo, teach the codegen to do this?
    yaml.round_trip_dump(result_json, sys.stdout)


def escape_expression_field(contents: str) -> str:
    return contents.replace('${', '$/{')

def etool_to_cltool(etool: cwl.ExpressionTool) -> cwl.CommandLineTool:
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
    contents = escape_expression_field(""""use strict";
var inputs=$(inputs);
var runtime=$(runtime);
var ret = function(){"""+etool.expression.strip()[2:-1]+"""}();
process.stdout.write(JSON.stringify(ret));""")
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

def generate_etool_from_expr(expr: str, target: cwl.CommandInputParameter ) -> cwl.ExpressionTool:
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
    #import ipdb; ipdb.set_trace()
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

def traverse_workflow(workflow: cwl.Workflow, replace_etool=False) -> cwl.Workflow:
    for index, step in enumerate(workflow.steps):
        if isinstance(step.run, cwl.ExpressionTool) and replace_etool:
            workflow.steps[index].run = etool_to_cltool(step.run)
        else:
            load_step(step)
    for index, step in enumerate(workflow.steps):
        for inp in step.in_:
            if inp.valueFrom and inp.valueFrom.startswith('${'):
                etool = generate_etool_from_expr(
                    inp.valueFrom, get_input_for_id(inp.id, step.run))
                if replace_etool:
                    etool = etool_to_cltool(etool)
                etool_id = "_expression_{}_{}".format(step.id.split('#')[-1], inp.id.split('/')[-1])
                workflow.steps.append(cwl.WorkflowStep(
                    etool_id,
                    [cwl.WorkflowStepInput(inp.source.split('#')[-1], None, "self", None, None)],
                    [cwl.WorkflowStepOutput("result")], None, None, None, None, etool, None, None))
                inp.valueFrom = None
                inp.source = "{}/result".format(etool_id)
    workflow.requirements[:] = [
        x for x  in workflow.requirements
        if not isinstance(x, (cwl.InlineJavascriptRequirement,
                              cwl.StepInputExpressionRequirement))]
    if not workflow.requirements:
        workflow.requirements = None
    return workflow


if __name__ == "__main__":
    sys.exit(main())
