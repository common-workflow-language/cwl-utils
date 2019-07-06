#!/usr/bin/env python3
import sys
import cwl_utils.parser_v1_0 as cwl
from ruamel import yaml

def main():
    top = cwl.load_document(sys.argv[1])
    result = traverse(top)
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

def replace_etool(etool: cwl.ExpressionTool) -> cwl.CommandLineTool:
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


def traverse(process: cwl.Process) -> cwl.Process:
    if isinstance(process, cwl.ExpressionTool):
        return replace_etool(process)
    if isinstance(process, cwl.Workflow):
        return traverse_workflow(process)
    return process


def get_process_from_step(step: cwl.WorkflowStep) -> cwl.Process:
    if isinstance(step.run, str):
        return cwl.load_document(step.run)
    return step.run


def traverse_workflow(workflow: cwl.Workflow) -> cwl.Workflow:
    for index, step in enumerate(workflow.steps):
        if isinstance(step, cwl.ExpressionTool):
            workflow.steps[index] = replace_etool(step)
        else:
            workflow.steps[index] = traverse(get_process_from_step(step))
    return workflow


if __name__ == "__main__":
    sys.exit(main())
