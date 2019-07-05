#!/usr/bin/env python3
import sys
import cwl_utils.parser_v1_0 as cwl
from ruamel import yaml

def main():
    top = cwl.load_document(sys.argv[1])
    yaml.dump(cwl.save(traverse(top)), sys.stdout, Dumper=yaml.SafeDumper)


def replace_etool(etool: cwl.ExpressionTool) -> cwl.CommandLineTool:
    inputs = {}
    for inp in etool.inputs:
        inputs[inp.id] = cwl.CommandInputParameter(
            inp.label, inp.secondaryFiles, inp.streamable, inp.doc, inp.id,
            inp.format, None, inp.default, inp.type, inp.extension_fields,
            inp.loadingOptions)
    outputs = {}
    for outp in etool.outputs:
        outputs[outp.id] = cwl.CommandOutputParameter(
            outp.label, outp.secondaryFiles, outp.streamable, outp.doc,
            outp.id, None, outp.format, outp.type, outp.extension_fields,
            outp.loadingOptions)
    listing = [cwl.Dirent("expression.js", """
"use strict";
var inputs=$(inputs);
var runtime=$(runtime);
var ret = """+etool.expression.strip()+""";
process.stdout.write(JSON.stringify(ret));""", writable=False)]
    iwdr = cwl.InitialWorkDirRequirement(listing)
    return cwl.CommandLineTool(
        etool.id, inputs, outputs, [iwdr, cwl.InlineJavascriptRequirement(None)],
        None, etool.label, etool.doc,
        "v1.0", ["nodejs", "expression.js"], None, None, None, 
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
