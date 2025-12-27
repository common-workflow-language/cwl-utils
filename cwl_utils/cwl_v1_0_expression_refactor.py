#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2018-2021 Michael R. Crusoe
"""CWL Expression refactoring tool for CWL v1.0 ."""
import copy
import hashlib
import uuid
from collections.abc import MutableSequence, Sequence
from contextlib import suppress
from typing import Any, cast

from ruamel import yaml
from schema_salad.sourceline import SourceLine
from schema_salad.utils import json_dumps

import cwl_utils.parser.cwl_v1_0 as cwl
import cwl_utils.parser.cwl_v1_0_utils as utils
from cwl_utils.errors import JavascriptException, WorkflowException
from cwl_utils.expression import do_eval, interpolate
from cwl_utils.parser.cwl_v1_0_utils import (
    AnyTypeSchema,
    BasicCommandInputTypeSchemas,
    BasicCommandOutputTypeSchemas,
    BasicInputTypeSchemas,
    BasicOutputTypeSchemas,
    CommandInputTypeSchemas,
    CommandOutputTypeSchemas,
    InputTypeSchemas,
    OutputTypeSchemas,
)
from cwl_utils.types import (
    CWLDirectoryType,
    CWLFileType,
    CWLObjectType,
    CWLOutputType,
    CWLParameterContext,
    CWLRuntimeParameterContext,
    is_file_or_directory,
    is_sequence,
)


def expand_stream_shortcuts(process: cwl.CommandLineTool) -> cwl.CommandLineTool:
    """Rewrite the "type: stdout" shortcut to use an explicit random filename."""
    if not process.outputs:
        return process
    result = None
    for index, output in enumerate(process.outputs):
        if output.type_ == "stdout":  # TODO: add 'stdin' for CWL v1.1
            if not result:
                result = copy.deepcopy(process)
            stdout_path = process.stdout
            if not stdout_path:
                stdout_path = hashlib.sha1(  # nosec
                    json_dumps(cwl.save(process)).encode("utf-8")
                ).hexdigest()
                result.stdout = stdout_path
            result.outputs[index].type_ = "File"
            output.outputBinding = cwl.CommandOutputBinding(stdout_path, None, None)
    if result:
        return result
    return process


def escape_expression_field(contents: str) -> str:
    """Escape sequences similar to CWL expressions or param references."""
    return contents.replace("${", "$/{").replace("$(", "$/(")


def _clean_type_ids(
    cwltype: InputTypeSchemas | CommandOutputTypeSchemas,
) -> None:
    if isinstance(cwltype, cwl.ArraySchema):
        if is_sequence(cwltype.items):
            for item in cwltype.items:
                if hasattr(item, "id"):
                    item.id = item.id.split("#")[-1]
        elif isinstance(cwltype.items, cwl.RecordSchema):
            if (
                isinstance(
                    cwltype.items,
                    (cwl.InputRecordSchema, cwl.CommandOutputRecordSchema),
                )
                and cwltype.items.name
            ):
                cwltype.items.name = cwltype.items.name.split("/")[-1]
            if cwltype.items.fields:
                for field in cwltype.items.fields:
                    field.name = field.name.split("/")[-1]
    elif isinstance(cwltype, cwl.RecordSchema):
        if cwltype.fields:
            for field in cwltype.fields:
                field.name = field.name.split("/")[-1]


def clean_type_ids(
    cwltype: AnyTypeSchema,
) -> AnyTypeSchema:
    """Simplify type identifiers."""
    result = copy.deepcopy(cwltype)
    if is_sequence(result):
        for item in result:
            _clean_type_ids(item)
    else:
        _clean_type_ids(result)
    return result


def _has_expression(string: str) -> bool:
    if "${" in string:
        return True
    if "$(" in string:
        return True
    return False


def has_expression(field: str | Sequence[str]) -> bool:
    if is_sequence(field):
        for entry in field:
            if _has_expression(entry):
                return True
        return False
    return _has_expression(field)


def get_expression(
    string: Any, inputs: CWLObjectType, self: CWLOutputType | None
) -> str | None:
    """
    Find and return a normalized CWL expression, if any.

    CWL expressions in the $() form are converted to the ${} form.
    """
    if not isinstance(string, str):
        return None
    if string.strip().startswith("${"):
        return string
    if "$(" in string:
        runtime = CWLRuntimeParameterContext(
            cores=0,
            ram=0,
            outdir="/root",
            tmpdir="/tmp",  # nosec
            outdirSize=0,
            tmpdirSize=0,
        )
        try:
            do_eval(
                string,
                inputs,
                context=self,
                requirements=[],
                outdir="",
                tmpdir="",
                resources={},
            )
        except (WorkflowException, JavascriptException):
            if (
                string[0:2] != "$("
                or not string.endswith(")")
                or len(string.split("$(")) > 2
            ):
                # then it is a string interpolation
                return cast(
                    str,
                    interpolate(
                        scan=string,
                        rootvars=CWLParameterContext(
                            inputs=inputs, self=self, runtime=runtime
                        ),
                        fullJS=True,
                        escaping_behavior=2,
                        convert_to_expression=True,
                    ),
                )
            else:
                # it is a CWL Expression in $() with no string interpolation
                return "${return " + string.strip()[2:-1] + ";}"
    return None


def _plain_input_schema_to_clt_input_schema(
    input_type: BasicInputTypeSchemas,
) -> BasicCommandInputTypeSchemas:
    match input_type:
        case cwl.InputArraySchema():
            return cwl.CommandInputArraySchema.fromDoc(
                input_type.save(),
                input_type.loadingOptions.baseuri,
                input_type.loadingOptions,
            )
        case cwl.InputEnumSchema():
            return cwl.CommandInputEnumSchema.fromDoc(
                input_type.save(),
                input_type.loadingOptions.baseuri,
                input_type.loadingOptions,
            )
        case cwl.InputRecordSchema():
            return cwl.CommandInputRecordSchema.fromDoc(
                input_type.save(),
                input_type.loadingOptions.baseuri,
                input_type.loadingOptions,
            )
        case str():
            return input_type
    raise WorkflowException(f"Unexpected ExpressionTool input type: {input_type}.")


def plain_input_schema_to_clt_input_schema(
    input_type: InputTypeSchemas,
) -> CommandInputTypeSchemas:
    if is_sequence(input_type):
        return [
            _plain_input_schema_to_clt_input_schema(input_type_item)
            for input_type_item in input_type
        ]
    if input_type is None:
        return None
    return _plain_input_schema_to_clt_input_schema(input_type)


def _plain_input_schema_to_plain_output_schema(
    input_type: BasicInputTypeSchemas,
) -> BasicOutputTypeSchemas:
    match input_type:
        case cwl.InputArraySchema():
            return cwl.OutputArraySchema.fromDoc(
                input_type.save(),
                input_type.loadingOptions.baseuri,
                input_type.loadingOptions,
            )
        case cwl.InputEnumSchema():
            return cwl.OutputEnumSchema.fromDoc(
                input_type.save(),
                input_type.loadingOptions.baseuri,
                input_type.loadingOptions,
            )
        case cwl.InputRecordSchema():
            return cwl.OutputRecordSchema.fromDoc(
                input_type.save(),
                input_type.loadingOptions.baseuri,
                input_type.loadingOptions,
            )
        case str():
            return input_type
    raise WorkflowException(f"Unexpected ExpressionTool input type: {input_type}.")


def plain_input_schema_to_plain_output_schema(
    input_type: InputTypeSchemas,
) -> OutputTypeSchemas:
    if is_sequence(input_type):
        return [
            _plain_input_schema_to_plain_output_schema(input_type_item)
            for input_type_item in input_type
        ]
    if input_type is None:
        return None
    return _plain_input_schema_to_plain_output_schema(input_type)


def _plain_output_type_to_clt_output_type(
    output_type: BasicOutputTypeSchemas,
) -> BasicCommandOutputTypeSchemas:
    match output_type:
        case cwl.OutputArraySchema():
            return cwl.CommandOutputArraySchema.fromDoc(
                output_type.save(),
                output_type.loadingOptions.baseuri,
                output_type.loadingOptions,
            )
        case cwl.OutputEnumSchema():
            return cwl.CommandOutputEnumSchema.fromDoc(
                output_type.save(),
                output_type.loadingOptions.baseuri,
                output_type.loadingOptions,
            )
        case cwl.OutputRecordSchema():
            return cwl.CommandOutputRecordSchema.fromDoc(
                output_type.save(),
                output_type.loadingOptions.baseuri,
                output_type.loadingOptions,
            )
        case str():
            return output_type
    raise WorkflowException(f"Unexpected ExpressionTool output type: {output_type}.")


def plain_output_type_to_clt_output_type(
    output_type: OutputTypeSchemas,
) -> CommandOutputTypeSchemas:
    if is_sequence(output_type):
        return [
            _plain_output_type_to_clt_output_type(output_type_item)
            for output_type_item in output_type
        ]
    if output_type is None:
        return None
    return _plain_output_type_to_clt_output_type(output_type)


def parameter_to_plain_input_paramater(
    parameter: (
        cwl.InputParameter
        | cwl.CommandInputParameter
        | cwl.CommandOutputParameter
        | cwl.ExpressionToolOutputParameter
        | cwl.WorkflowOutputParameter
    ),
) -> cwl.InputParameter:
    return cwl.InputParameter.fromDoc(
        parameter.save(), parameter.loadingOptions.baseuri, parameter.loadingOptions
    )


def parameters_to_plain_input_paramaters(
    parameters: Sequence[
        cwl.InputParameter | cwl.CommandInputParameter | cwl.CommandOutputParameter
    ],
) -> Sequence[cwl.InputParameter]:
    return [parameter_to_plain_input_paramater(parameter) for parameter in parameters]


def etool_to_cltool(
    etool: cwl.ExpressionTool, expressionLib: list[str] | None = None
) -> cwl.CommandLineTool:
    """Convert a ExpressionTool to a CommandLineTool."""
    inputs = yaml.comments.CommentedSeq()  # preserve the order
    for inp in etool.inputs:
        inputs.append(
            cwl.CommandInputParameter(
                id=inp.id,
                label=inp.label,
                secondaryFiles=inp.secondaryFiles,
                streamable=inp.streamable,
                doc=inp.doc,
                format=inp.format,
                default=inp.default,
                type_=plain_input_schema_to_clt_input_schema(inp.type_),
                extension_fields=inp.extension_fields,
                loadingOptions=inp.loadingOptions,
            )
        )
    outputs = yaml.comments.CommentedSeq()
    for outp in etool.outputs:
        outputs.append(
            cwl.CommandOutputParameter(
                id=outp.id,
                label=outp.label,
                secondaryFiles=outp.secondaryFiles,
                streamable=outp.streamable,
                doc=outp.doc,
                format=outp.format,
                type_=plain_output_type_to_clt_output_type(outp.type_),
                extension_fields=outp.extension_fields,
                loadingOptions=outp.loadingOptions,
            )
        )
    contents = """"use strict";
var inputs=$(inputs);
var runtime=$(runtime);"""
    if expressionLib:
        contents += "\n" + "\n".join(expressionLib)
    contents += (
        """
var ret = function(){"""
        + escape_expression_field(etool.expression.strip()[2:-1])
        + """}();
process.stdout.write(JSON.stringify(ret));"""
    )
    listing = [cwl.Dirent(entryname="expression.js", entry=contents, writable=None)]
    iwdr = cwl.InitialWorkDirRequirement(listing)
    containerReq = cwl.DockerRequirement(dockerPull="node:alpine")
    softwareHint = cwl.SoftwareRequirement(
        packages=[cwl.SoftwarePackage(package="nodejs")]
    )
    return cwl.CommandLineTool(
        inputs=inputs,
        outputs=outputs,
        id=etool.id,
        requirements=[iwdr],
        hints=[containerReq, softwareHint],
        label=etool.label,
        doc=etool.doc,
        cwlVersion=etool.cwlVersion,
        baseCommand=["nodejs", "expression.js"],
        stdout="cwl.output.json",
        extension_fields=etool.extension_fields,
        loadingOptions=etool.loadingOptions,
    )


def traverse(
    process: cwl.CommandLineTool | cwl.ExpressionTool | cwl.Workflow,
    replace_etool: bool,
    inside: bool,
    skip_command_line1: bool,
    skip_command_line2: bool,
) -> tuple[cwl.CommandLineTool | cwl.ExpressionTool | cwl.Workflow, bool]:
    """Convert the given process and any subprocesses."""
    match process:
        case cwl.CommandLineTool() if not inside:
            process = expand_stream_shortcuts(process)
            wf_inputs = []
            wf_outputs = []
            step_inputs = []
            step_outputs = []
            if process.inputs:
                for inp in process.inputs:
                    inp_id = inp.id.split("#")[-1]
                    step_inputs.append(
                        cwl.WorkflowStepInput(
                            id=inp_id,
                            source=inp_id,
                            extension_fields=inp.extension_fields,
                            loadingOptions=inp.loadingOptions,
                        )
                    )
                    wf_inputs.append(
                        cwl.InputParameter(
                            id=inp_id,
                            label=inp.label,
                            secondaryFiles=inp.secondaryFiles,
                            streamable=inp.streamable,
                            doc=inp.doc,
                            format=inp.format,
                            default=inp.default,
                            type_=inp.type_,
                            extension_fields=inp.extension_fields,
                            loadingOptions=inp.loadingOptions,
                        )
                    )
            if process.outputs:
                for outp in process.outputs:
                    outp_id = outp.id.split("#")[-1]
                    step_outputs.append(outp_id)
                    wf_outputs.append(
                        cwl.WorkflowOutputParameter(
                            id=outp_id,
                            label=outp.label,
                            secondaryFiles=outp.secondaryFiles,
                            streamable=outp.streamable,
                            doc=outp.doc,
                            format=outp.format,
                            outputSource=f"main/{outp_id}",
                            type_=outp.type_,
                            extension_fields=outp.extension_fields,
                            loadingOptions=outp.loadingOptions,
                        )
                    )
            step = cwl.WorkflowStep(
                id="#main",
                in_=step_inputs,
                out=step_outputs,
                run=copy.deepcopy(process),
            )
            workflow = cwl.Workflow(
                inputs=wf_inputs,
                outputs=wf_outputs,
                steps=[step],
                cwlVersion=process.cwlVersion,
            )
            result, modified = traverse_workflow(
                workflow, replace_etool, skip_command_line1, skip_command_line2
            )
            if modified:
                return result, True
            else:
                return process, False
        case cwl.ExpressionTool() if replace_etool:
            expression = get_expression(process.expression, empty_inputs(process), None)
            # Why call get_expression on an ExpressionTool?
            # It normalizes the form of $() CWL expressions into the ${} style
            if expression:
                process2 = copy.deepcopy(process)
                process2.expression = expression
            else:
                process2 = process
            return etool_to_cltool(process2), True
        case cwl.Workflow():
            return traverse_workflow(
                process, replace_etool, skip_command_line1, skip_command_line2
            )
        case _:
            return process, False


def load_step(
    step: cwl.WorkflowStep,
    replace_etool: bool,
    skip_command_line1: bool,
    skip_command_line2: bool,
) -> bool:
    """If the step's Process is not inline, load and process it."""
    modified = False
    if isinstance(step.run, str):
        step.run, modified = traverse(
            cwl.load_document(step.run, baseuri=step.loadingOptions.fileuri),
            replace_etool,
            True,
            skip_command_line1,
            skip_command_line2,
        )
    return modified


def generate_etool_from_expr(
    expr: str,
    target: cwl.CommandInputParameter | cwl.InputParameter,
    no_inputs: bool = False,
    self_type: None | (
        cwl.InputParameter
        | cwl.CommandInputParameter
        | list[cwl.InputParameter | cwl.CommandInputParameter]
    ) = None,  # if the "self" input should be a different type than the "result" output
    extra_processes: None | (
        Sequence[
            cwl.Workflow
            | cwl.WorkflowStep
            | cwl.CommandLineTool
            | cwl.ExpressionTool
            | cwl.ProcessGenerator
        ]
    ) = None,
) -> cwl.ExpressionTool:
    """Convert a CWL Expression into an ExpressionTool."""
    inputs: list[cwl.InputParameter] = []
    if not no_inputs:
        if self_type is None:
            self_type = target
        assert self_type is not None
        new_type: InputTypeSchemas
        if is_sequence(self_type):
            new_type_list: MutableSequence[BasicInputTypeSchemas] = []
            for entry in self_type:
                clean_type = clean_type_ids(entry.type_)
                if is_sequence(clean_type):
                    new_type_list.extend(clean_type)
                elif clean_type is None:
                    pass
                else:
                    new_type_list.append(clean_type)
            new_type = new_type_list
        else:
            new_type = clean_type_ids(self_type.type_)
        inputs.append(
            cwl.InputParameter(
                id="self",
                label=self_type.label if not is_sequence(self_type) else None,
                secondaryFiles=(
                    self_type.secondaryFiles if not is_sequence(self_type) else None
                ),
                streamable=(
                    self_type.streamable if not is_sequence(self_type) else None
                ),
                doc=self_type.doc if not is_sequence(self_type) else None,
                format=(self_type.format if not is_sequence(self_type) else None),
                type_=new_type,
                extension_fields=(
                    self_type.extension_fields if not is_sequence(self_type) else None
                ),
                loadingOptions=(
                    self_type.loadingOptions if not is_sequence(self_type) else None
                ),
            )
        )
    outputs: list[cwl.ExpressionToolOutputParameter] = []
    outputs.append(
        cwl.ExpressionToolOutputParameter(
            id="result",
            label=target.label,
            secondaryFiles=target.secondaryFiles,
            streamable=target.streamable,
            doc=target.doc,
            format=target.format[0] if target.format else None,
            type_=plain_input_schema_to_plain_output_schema(target.type_),
            extension_fields=target.extension_fields,
            loadingOptions=target.loadingOptions,
        )
    )
    expression = "${"
    if not no_inputs:
        expression += "\n  var self=inputs.self;"
    expression += (
        """
  return {"result": function(){"""
        + expr[2:-2]
        + """}()};
 }"""
    )
    inlineJSReq = cwl.InlineJavascriptRequirement(
        find_expressionLib(extra_processes) if extra_processes else None
    )
    return cwl.ExpressionTool(
        id="_:" + str(uuid.uuid4()),
        inputs=inputs,
        outputs=outputs,
        expression=expression,
        requirements=[inlineJSReq],
        cwlVersion="v1.0",
    )


def get_input_for_id(
    name: str,
    tool: (
        cwl.CommandLineTool | cwl.Workflow | cwl.ProcessGenerator | cwl.ExpressionTool
    ),
) -> cwl.CommandInputParameter | None:
    """Determine the CommandInputParameter for the given input name."""
    name = name.split("/")[-1]

    for inp in cast(list[cwl.CommandInputParameter], tool.inputs):
        if inp.id and inp.id.split("#")[-1].split("/")[-1] == name:
            return cwl.CommandInputParameter.fromDoc(
                inp.save(), inp.loadingOptions.baseuri, inp.loadingOptions
            )
    if isinstance(tool, cwl.Workflow) and "/" in name:
        stepname, stem = name.split("/", 1)
        for step in tool.steps:
            if step.id == stepname:
                assert not isinstance(step.run, str)
                result = get_input_for_id(stem, step.run)
                if result:
                    return result
    return None


def find_expressionLib(
    processes: Sequence[
        cwl.CommandLineTool
        | cwl.Workflow
        | cwl.ExpressionTool
        | cwl.WorkflowStep
        | cwl.ProcessGenerator
    ],
) -> list[str] | None:
    """
    Return the expressionLib from the highest priority InlineJavascriptRequirement.

    processes: should be in order of least important to most important
    (Workflow, WorkflowStep, ... CommandLineTool/ExpressionTool)
    """
    for process in reversed(copy.copy(processes)):
        if process.requirements:
            for req in process.requirements:
                if isinstance(req, cwl.InlineJavascriptRequirement):
                    return cast(list[str] | None, copy.deepcopy(req.expressionLib))
    return None


def replace_expr_with_etool(
    expr: str,
    name: str,
    workflow: cwl.Workflow,
    target: cwl.CommandInputParameter | cwl.InputParameter,
    source: str | list[Any] | None,
    replace_etool: bool = False,
    extra_process: None | (
        cwl.Workflow
        | cwl.WorkflowStep
        | cwl.CommandLineTool
        | cwl.ExpressionTool
        | cwl.ProcessGenerator
    ) = None,
    source_type: cwl.CommandInputParameter | None = None,
) -> None:
    """Modify the given workflow, replacing the expr with an standalone ExpressionTool."""
    extra_processes: list[
        cwl.WorkflowStep
        | cwl.Workflow
        | cwl.CommandLineTool
        | cwl.ExpressionTool
        | cwl.ProcessGenerator
    ] = [workflow]
    if extra_process:
        extra_processes.append(extra_process)
    etool: cwl.ExpressionTool = generate_etool_from_expr(
        expr, target, source is None, source_type, extra_processes
    )
    if replace_etool:
        processes: list[
            cwl.WorkflowStep
            | cwl.Workflow
            | cwl.CommandLineTool
            | cwl.ExpressionTool
            | cwl.ProcessGenerator
        ] = [workflow]
        if extra_process:
            processes.append(extra_process)
        final_tool: cwl.ExpressionTool | cwl.CommandLineTool = etool_to_cltool(
            etool, find_expressionLib(processes)
        )
    else:
        final_tool = etool
    inps = []
    if source:
        inps.append(cwl.WorkflowStepInput(id="self", source=source))
    new_steps: list[cwl.WorkflowStep] = [
        cwl.WorkflowStep(
            id=name,
            in_=inps,
            out=[cwl.WorkflowStepOutput("result")],
            run=final_tool,
        )
    ]
    new_steps.extend(workflow.steps)
    workflow.steps = new_steps


def replace_wf_input_ref_with_step_output(
    workflow: cwl.Workflow, name: str, target: str
) -> None:
    """Refactor all reference to a workflow input to the specified step output."""
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


def empty_inputs(
    process_or_step: (
        cwl.CommandLineTool
        | cwl.WorkflowStep
        | cwl.ExpressionTool
        | cwl.Workflow
        | cwl.ProcessGenerator
    ),
    parent: cwl.Workflow | None = None,
) -> dict[str, Any]:
    """Produce a mock input object for the given inputs."""
    result = {}
    if isinstance(process_or_step, cwl.Process):
        for param1 in process_or_step.inputs:
            result[param1.id.split("#")[-1]] = example_input(param1.type_)
    else:
        for param2 in process_or_step.in_:
            param2_id = param2.id.split("/")[-1]
            if param2.source is None and param2.valueFrom:
                result[param2_id] = example_input("string")
            elif param2.source is None and param2.default:
                result[param2_id] = param2.default
            elif param2.source is not None:
                with suppress(WorkflowException):
                    assert not isinstance(process_or_step.run, str)
                    result[param2_id] = example_input(
                        utils.type_for_source(
                            process_or_step.run, param2.source, parent
                        )
                    )
    return result


def example_input(some_type: Any) -> Any:
    """Produce a fake input for the given type."""
    # TODO: accept some sort of context object with local custom type definitions
    if some_type == "Directory":
        return CWLDirectoryType(
            **{
                "class": "Directory",
                "location": "https://www.example.com/example",
                "basename": "example",
                "listing": [
                    CWLFileType(
                        **{
                            "class": "File",
                            "basename": "example.txt",
                            "size": 23,
                            "contents": "hoopla",
                            "nameroot": "example",
                            "nameext": "txt",
                        }
                    )
                ],
            }
        )
    if some_type == "File":
        return CWLFileType(
            **{
                "class": "File",
                "location": "https://www.example.com/example.txt",
                "basename": "example.txt",
                "size": 23,
                "contents": "hoopla",
                "nameroot": "example",
                "nameext": "txt",
            }
        )
    if some_type == "int":
        return 23
    if some_type == "string":
        return "hoopla!"
    if some_type == "boolean":
        return True
    return None


EMPTY_FILE = CWLFileType(
    **{
        "class": "File",
        "basename": "em.pty",
        "nameroot": "em",
        "nameext": "pty",
    }
)

TOPLEVEL_SF_EXPR_ERROR = (
    "Input '{}'. Sorry, CWL Expressions as part of a secondaryFiles "
    "specification in a Workflow level input or standalone CommandLine Tool "
    "are not able to be refactored into separate ExpressionTool or "
    "CommandLineTool steps."
)

TOPLEVEL_FORMAT_EXPR_ERROR = (
    "Input '{}'. Sorry, CWL Expressions as part of a format "
    "specification in a Workflow level input are not able to be refactored "
    "into separate ExpressionTool/CommandLineTool steps."
)


def process_workflow_inputs_and_outputs(
    workflow: cwl.Workflow, replace_etool: bool
) -> bool:
    """Do any needed conversions on the given Workflow's inputs and outputs."""
    modified = False
    for index, param in enumerate(workflow.inputs):
        with SourceLine(workflow.inputs, index, WorkflowException):
            if param.format is not None and has_expression(param.format):
                raise SourceLine(
                    param.loadingOptions.original_doc,
                    "format",
                    raise_type=WorkflowException,
                ).makeError(TOPLEVEL_FORMAT_EXPR_ERROR.format(param.id.split("#")[-1]))
            if param.secondaryFiles is not None and has_expression(
                param.secondaryFiles
            ):
                raise SourceLine(
                    param.loadingOptions.original_doc,
                    "secondaryFiles",
                    raise_type=WorkflowException,
                ).makeError(TOPLEVEL_SF_EXPR_ERROR.format(param.id.split("#")[-1]))
    return modified


def process_workflow_reqs_and_hints(
    workflow: cwl.Workflow, replace_etool: bool
) -> bool:
    """
    Convert any expressions in a workflow's reqs and hints.

    Each expression will be converted to an additional step.
    The converted requirement will be copied to all workflow steps that don't have that
    requirement type. Those affected steps will gain an additional input from the relevant
    synthesized expression step.
    """
    # TODO: consolidate the generated etools/cltools into a single "_expression_workflow_reqs" step
    # TODO: support resourceReq.* references to Workflow.inputs?
    #       ^ By refactoring replace_expr_etool to allow multiple inputs,
    #         and connecting all workflow inputs to the generated step
    modified = False
    inputs = empty_inputs(workflow)
    generated_res_reqs: list[tuple[str, int | str]] = []
    generated_iwdr_reqs: list[tuple[str, int | str]] = []
    generated_envVar_reqs: list[tuple[str, int | str]] = []
    prop_reqs: tuple[
        (
            type[cwl.EnvVarRequirement]
            | type[cwl.ResourceRequirement]
            | type[cwl.InitialWorkDirRequirement]
        ),
        ...,
    ] = ()
    resourceReq: cwl.ResourceRequirement | None = None
    envVarReq: cwl.EnvVarRequirement | None = None
    iwdr: cwl.InitialWorkDirRequirement | None = None
    if workflow.requirements is not None:
        for req in cast(list[cwl.ProcessRequirement], workflow.requirements):
            match req:
                case cwl.EnvVarRequirement() if req.envDef:
                    for index, envDef in enumerate(req.envDef):
                        if envDef.envValue:
                            expression = get_expression(envDef.envValue, inputs, None)
                            if expression:
                                modified = True
                                target = cwl.InputParameter(
                                    id="",
                                    type_="string",
                                )
                                etool_id = (
                                    "_expression_workflow_EnvVarRequirement_{}".format(
                                        index
                                    )
                                )
                                replace_expr_with_etool(
                                    expression,
                                    etool_id,
                                    workflow,
                                    target,
                                    None,
                                    replace_etool,
                                )
                                if envVarReq is None:
                                    envVarReq = copy.deepcopy(req)
                                    prop_reqs += (cwl.EnvVarRequirement,)
                                newEnvDef = copy.deepcopy(envDef)
                                newEnvDef.envValue = f"$(inputs._envDef{index})"
                                new_envDef = list(envVarReq.envDef)
                                new_envDef[index] = newEnvDef
                                envVarReq.envDef = new_envDef
                                generated_envVar_reqs.append((etool_id, index))
                case cwl.ResourceRequirement():
                    for attr in cwl.ResourceRequirement.attrs:
                        this_attr = getattr(req, attr, None)
                        if this_attr:
                            expression = get_expression(this_attr, inputs, None)
                            if expression:
                                modified = True
                                target = cwl.InputParameter(id="", type_="long")
                                etool_id = "_expression_workflow_ResourceRequirement_{}".format(
                                    attr
                                )
                                replace_expr_with_etool(
                                    expression,
                                    etool_id,
                                    workflow,
                                    target,
                                    None,
                                    replace_etool,
                                )
                                if not resourceReq:
                                    resourceReq = cwl.ResourceRequirement(
                                        loadingOptions=workflow.loadingOptions,
                                    )
                                    prop_reqs += (cwl.ResourceRequirement,)
                                setattr(resourceReq, attr, f"$(inputs._{attr})")
                                generated_res_reqs.append((etool_id, attr))
                case cwl.InitialWorkDirRequirement() if req.listing:
                    if isinstance(req.listing, str):
                        expression = get_expression(req.listing, inputs, None)
                        if expression:
                            modified = True
                            target = cwl.InputParameter(
                                id="",
                                type_=cwl.InputArraySchema(
                                    ["File", "Directory"], "array", None, None
                                ),
                            )
                            etool_id = "_expression_workflow_InitialWorkDirRequirement"
                            replace_expr_with_etool(
                                expression,
                                etool_id,
                                workflow,
                                target,
                                None,
                                replace_etool,
                            )
                            iwdr = cwl.InitialWorkDirRequirement(
                                listing="$(inputs._iwdr_listing)",
                                loadingOptions=workflow.loadingOptions,
                            )
                            prop_reqs += (cwl.InitialWorkDirRequirement,)
                    else:
                        iwdr = copy.deepcopy(req)
                        for index1, entry1 in enumerate(req.listing):
                            expression = get_expression(entry1, inputs, None)
                            if expression:
                                modified = True
                                target = cwl.InputParameter(
                                    id="",
                                    type_=cwl.InputArraySchema(
                                        ["File", "Directory"], "array", None, None
                                    ),
                                )
                                etool_id = "_expression_workflow_InitialWorkDirRequirement_{}".format(
                                    index1
                                )
                                replace_expr_with_etool(
                                    expression,
                                    etool_id,
                                    workflow,
                                    target,
                                    None,
                                    replace_etool,
                                )
                                new_listing = list(iwdr.listing)
                                new_listing[index1] = f"$(inputs._iwdr_listing_{index1}"
                                iwdr.listing = new_listing
                                generated_iwdr_reqs.append((etool_id, index1))
                            elif isinstance(entry1, cwl.Dirent):
                                if entry1.entry:
                                    expression = get_expression(
                                        entry1.entry, inputs, None
                                    )
                                    if expression:
                                        expr: str = expression
                                        expr_result = do_eval(
                                            ex=entry1.entry,
                                            jobinput=inputs,
                                            requirements=[],
                                            outdir="",
                                            tmpdir="",
                                            resources={},
                                        )
                                        modified = True
                                        if is_file_or_directory(expr_result):
                                            target = cwl.InputParameter(
                                                id="",
                                                type_=expr_result["class"],
                                            )
                                            replace_expr_with_etool(
                                                expr,
                                                etool_id,
                                                workflow,
                                                target,
                                                None,
                                                replace_etool,
                                            )
                                            new_listing = list(iwdr.listing)
                                            new_listing[index1] = (
                                                f"$(inputs._iwdr_listing_{index1}"
                                            )
                                            iwdr.listing = new_listing
                                            generated_iwdr_reqs.append(
                                                (etool_id, index1)
                                            )
                                        elif isinstance(expr_result, str):
                                            target = cwl.InputParameter(
                                                id="",
                                                type_=["File"],
                                            )
                                            if entry1.entryname is None:
                                                raise SourceLine(
                                                    entry1.loadingOptions.original_doc,
                                                    index1,
                                                    raise_type=WorkflowException,
                                                ).makeError(
                                                    f"Entry {index1},"
                                                    + "Invalid CWL, if 'entry' "
                                                    "is a string, then entryName must be specified."
                                                )
                                            expr = (
                                                '${return {"class": "File", "basename": "'
                                                + entry1.entryname
                                                + '", "contents": (function(){'
                                                + expr[2:-1]
                                                + "})() }; }"
                                            )
                                        etool_id = "_expression_workflow_InitialWorkDirRequirement_{}".format(
                                            index1
                                        )
                                        replace_expr_with_etool(
                                            expr,
                                            etool_id,
                                            workflow,
                                            target,
                                            None,
                                            replace_etool,
                                        )
                                        new_listing = list(iwdr.listing)
                                        new_listing[index1] = (
                                            f"$(inputs._iwdr_listing_{index1}"
                                        )
                                        iwdr.listing = new_listing
                                        generated_iwdr_reqs.append((etool_id, index1))

                                elif entry1.entryname:
                                    expression = get_expression(
                                        entry1.entryname, inputs, None
                                    )
                                    if expression:
                                        modified = True
                                        target = cwl.InputParameter(
                                            id="",
                                            type_="string",
                                        )
                                        etool_id = f"_expression_workflow_InitialWorkDirRequirement_{index1}"
                                        replace_expr_with_etool(
                                            expression,
                                            etool_id,
                                            workflow,
                                            target,
                                            None,
                                            replace_etool,
                                        )
                                        new_listing = list(iwdr.listing)
                                        new_listing[index1] = (
                                            f"$(inputs._iwdr_listing_{index1}"
                                        )
                                        iwdr.listing = new_listing
                                        generated_iwdr_reqs.append((etool_id, index1))
                        if generated_iwdr_reqs:
                            prop_reqs += (cwl.InitialWorkDirRequirement,)
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
            new_requirements = list(step.requirements)
            new_requirements.append(envVarReq)
            step.requirements = new_requirements
            new_ins = list(step.in_)
            for entry2 in generated_envVar_reqs:
                new_ins.append(
                    cwl.WorkflowStepInput(
                        id=f"_envDef{entry2[1]}",
                        source=f"{entry2[0]}/result",
                    )
                )
            step.in_ = new_ins

    if resourceReq and workflow.steps:
        for step in workflow.steps:
            if step.id.split("#")[-1].startswith("_expression_"):
                continue
            if step.requirements:
                for req in step.requirements:
                    if isinstance(req, cwl.ResourceRequirement):
                        continue
            else:
                step.requirements = []
            new_requirements = list(step.requirements)
            new_requirements.append(resourceReq)
            step.requirements = new_requirements
            new_ins = list(step.in_)
            for entry3 in generated_res_reqs:
                new_ins.append(
                    cwl.WorkflowStepInput(
                        id=f"_{entry3[1]}",
                        source=f"{entry3[0]}/result",
                    )
                )
            step.in_ = new_ins

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
            new_requirements = list(step.requirements)
            new_requirements.append(resourceReq)
            new_requirements.append(iwdr)
            step.requirements = new_requirements
            new_ins = list(step.in_)
            if generated_iwdr_reqs:
                for entry4 in generated_iwdr_reqs:
                    new_ins.append(
                        cwl.WorkflowStepInput(
                            id=f"_iwdr_listing_{index}",
                            source=f"{entry4[0]}/result",
                        )
                    )
            else:
                new_ins.append(
                    cwl.WorkflowStepInput(
                        id="_iwdr_listing",
                        source="_expression_workflow_InitialWorkDirRequirement/result",
                    )
                )
            step.in_ = new_ins

    if workflow.requirements:
        workflow.requirements = [
            x for x in workflow.requirements if not isinstance(x, prop_reqs)
        ]
    return modified


def process_level_reqs(
    process: (
        cwl.CommandLineTool | cwl.ExpressionTool | cwl.ProcessGenerator | cwl.Workflow
    ),
    step: cwl.WorkflowStep,
    parent: cwl.Workflow,
    replace_etool: bool,
    skip_command_line1: bool,
    skip_command_line2: bool,
) -> bool:
    """Convert expressions inside a process into new adjacent steps."""
    # This is for reqs inside a Process (CommandLineTool, ExpressionTool)
    # differences from process_workflow_reqs_and_hints() are:
    # - the name of the generated ETools/CTools contains the name of the step, not "workflow"
    # - Generated ETools/CTools are adjacent steps
    # - Replace the CWL Expression inplace with a CWL parameter reference
    # - Don't create a new Requirement, nor delete the existing Requirement
    # - the Process is passed to replace_expr_with_etool for later searching for JS expressionLibs
    # - in addition to adding the input to the step for the ETool/CTool result,
    #   add it to the Process.inputs as well
    if not process.requirements:
        return False
    modified = False
    assert not isinstance(step.run, str)
    target_process = step.run
    inputs = empty_inputs(process)
    generated_res_reqs: list[tuple[str, str]] = []
    generated_iwdr_reqs: list[tuple[str, int | str, Any]] = []
    generated_envVar_reqs: list[tuple[str, int | str]] = []
    if not step.id:
        return False
    step_name = step.id.split("#", 1)[-1]
    for req_index, req in enumerate(process.requirements):
        assert target_process.requirements is not None
        match req:
            case cwl.EnvVarRequirement() if req.envDef:
                for env_index, envDef in enumerate(req.envDef):
                    if envDef.envValue:
                        expression = get_expression(envDef.envValue, inputs, None)
                        if expression:
                            modified = True
                            target = cwl.InputParameter(id="", type_="string")
                            etool_id = "_expression_{}_EnvVarRequirement_{}".format(
                                step_name, env_index
                            )
                            replace_expr_with_etool(
                                expression,
                                etool_id,
                                parent,
                                target,
                                None,
                                replace_etool,
                                process,
                            )
                            cast(
                                cwl.EnvVarRequirement,
                                target_process.requirements[req_index],
                            ).envDef[
                                env_index
                            ].envValue = f"$(inputs._envDef{env_index})"
                            generated_envVar_reqs.append((etool_id, env_index))
            case cwl.ResourceRequirement():
                for attr in cwl.ResourceRequirement.attrs:
                    this_attr = getattr(req, attr, None)
                    if this_attr:
                        expression = get_expression(this_attr, inputs, None)
                        if expression:
                            modified = True
                            target = cwl.InputParameter(id="", type_="long")
                            etool_id = "_expression_{}_ResourceRequirement_{}".format(
                                step_name, attr
                            )
                            replace_step_process_hintreq_expr_with_etool(
                                expression,
                                etool_id,
                                parent,
                                target,
                                step,
                                replace_etool,
                            )
                            setattr(
                                target_process.requirements[req_index],
                                attr,
                                f"$(inputs._{attr})",
                            )
                            generated_res_reqs.append((etool_id, attr))

            case cwl.InitialWorkDirRequirement() if (
                not skip_command_line2 and req.listing
            ):
                if isinstance(req.listing, str):
                    expression = get_expression(req.listing, inputs, None)
                    if expression:
                        modified = True
                        target_type = cwl.InputArraySchema(
                            ["File", "Directory"], "array", None, None
                        )
                        target = cwl.InputParameter(id="", type_=target_type)
                        etool_id = "_expression_{}_InitialWorkDirRequirement".format(
                            step_name
                        )
                        replace_expr_with_etool(
                            expression,
                            etool_id,
                            parent,
                            target,
                            None,
                            replace_etool,
                            process,
                        )
                        cast(
                            cwl.InitialWorkDirRequirement,
                            target_process.requirements[req_index],
                        ).listing = ("$(inputs._iwdr_listing)",)
                        new_step_ins = list(step.in_)
                        new_step_ins.append(
                            cwl.WorkflowStepInput(
                                id="_iwdr_listing",
                                source=f"{etool_id}/result",
                            )
                        )
                        step.in_ = new_step_ins
                        add_input_to_process(
                            target_process,
                            "_iwdr_listing",
                            target_type,
                            process.loadingOptions,
                        )
                else:
                    for listing_index, entry5 in enumerate(req.listing):
                        expression = get_expression(entry5, inputs, None)
                        if expression:
                            modified = True
                            target_type = cwl.InputArraySchema(
                                ["File", "Directory"], "array", None, None
                            )
                            target = cwl.InputParameter(
                                id="",
                                type_=target_type,
                            )
                            etool_id = (
                                "_expression_{}_InitialWorkDirRequirement_{}".format(
                                    step_name, listing_index
                                )
                            )
                            replace_expr_with_etool(
                                expression,
                                etool_id,
                                parent,
                                target,
                                None,
                                replace_etool,
                                process,
                            )
                            new_iwdr_listing = list(
                                cast(
                                    cwl.InitialWorkDirRequirement,
                                    target_process.requirements[req_index],
                                ).listing
                            )
                            new_iwdr_listing[listing_index] = (
                                f"$(inputs._iwdr_listing_{listing_index}"
                            )
                            cast(
                                cwl.InitialWorkDirRequirement,
                                target_process.requirements[req_index],
                            ).listing = new_iwdr_listing
                            generated_iwdr_reqs.append(
                                (etool_id, listing_index, target_type)
                            )
                        elif isinstance(entry5, cwl.Dirent):
                            if entry5.entry:
                                expression = get_expression(entry5.entry, inputs, None)
                                if expression:
                                    modified = True
                                    if entry5.entryname is not None:
                                        entryname_expr = get_expression(
                                            entry5.entryname, inputs, None
                                        )
                                        entryname = (
                                            entry5.entryname
                                            if entryname_expr
                                            else f'"{entry5.entryname}"'  # noqa: B907
                                        )
                                        new_expression = (
                                            "${var result; var entryname = "
                                            + entryname
                                            + "; var entry = "
                                            + entry5.entry[2:-1]
                                            + """;
if (typeof entry === 'string' || entry instanceof String) {
result = {"class": "File", "basename": entryname, "contents": entry} ;
if (typeof entryname === 'string' || entryname instanceof String) {
result.basename = entryname ;
}
} else {
result = entry ;
}
return result; }"""
                                        )
                                    else:
                                        new_expression = expression
                                    d_target_type = ["File", "Directory"]
                                    target = cwl.InputParameter(
                                        id="",
                                        type_=d_target_type,
                                    )
                                    etool_id = "_expression_{}_InitialWorkDirRequirement_{}".format(
                                        step_name, listing_index
                                    )

                                    replace_step_process_hintreq_expr_with_etool(
                                        new_expression,
                                        etool_id,
                                        parent,
                                        target,
                                        step,
                                        replace_etool,
                                    )
                                    cast(
                                        cwl.Dirent,
                                        cast(
                                            cwl.InitialWorkDirRequirement,
                                            target_process.requirements[req_index],
                                        ).listing[listing_index],
                                    ).entry = "$(inputs._iwdr_listing_{})".format(
                                        listing_index
                                    )
                                    generated_iwdr_reqs.append(
                                        (etool_id, listing_index, d_target_type)
                                    )
                            elif entry5.entryname:
                                expression = get_expression(
                                    entry5.entryname, inputs, None
                                )
                                if expression:
                                    modified = True
                                    target = cwl.InputParameter(
                                        id="",
                                        type_="string",
                                    )
                                    etool_id = "_expression_{}_InitialWorkDirRequirement_{}".format(
                                        step_name, listing_index
                                    )
                                    replace_expr_with_etool(
                                        expression,
                                        etool_id,
                                        parent,
                                        target,
                                        None,
                                        replace_etool,
                                        process,
                                    )
                                    cast(
                                        cwl.Dirent,
                                        cast(
                                            cwl.InitialWorkDirRequirement,
                                            target_process.requirements[req_index],
                                        ).listing[listing_index],
                                    ).entryname = "$(inputs._iwdr_listing_{})".format(
                                        listing_index
                                    )
                                    generated_iwdr_reqs.append(
                                        (etool_id, listing_index, "string")
                                    )
    new_step_ins = list(step.in_)
    for env_entry in generated_envVar_reqs:
        name = f"_envDef{env_entry[1]}"
        new_step_ins.append(
            cwl.WorkflowStepInput(id=name, source=f"{env_entry[0]}/result")
        )
        add_input_to_process(target_process, name, "string", process.loadingOptions)
    for res_entry in generated_res_reqs:
        name = f"_{res_entry[1]}"
        new_step_ins.append(
            cwl.WorkflowStepInput(id=name, source=f"{res_entry[0]}/result")
        )
        add_input_to_process(target_process, name, "long", process.loadingOptions)
    for iwdr_entry in generated_iwdr_reqs:
        name = f"_iwdr_listing_{iwdr_entry[1]}"
        new_step_ins.append(
            cwl.WorkflowStepInput(id=name, source=f"{iwdr_entry[0]}/result")
        )
        add_input_to_process(
            target_process, name, iwdr_entry[2], process.loadingOptions
        )
    step.in_ = new_step_ins
    return modified


def add_input_to_process(
    process: cwl.Process, name: str, inptype: Any, loadingOptions: cwl.LoadingOptions
) -> None:
    """Add a new InputParameter to the given CommandLineTool."""
    if isinstance(process, cwl.CommandLineTool):
        new_process_inputs = list(process.inputs)
        new_process_inputs.append(
            cwl.CommandInputParameter(
                id=name,
                type_=inptype,
                loadingOptions=loadingOptions,
            )
        )
        process.inputs = new_process_inputs


def traverse_CommandLineTool(
    clt: cwl.CommandLineTool,
    parent: cwl.Workflow,
    step: cwl.WorkflowStep,
    replace_etool: bool,
    skip_command_line1: bool,
    skip_command_line2: bool,
) -> bool:
    """Extract any CWL Expressions within the given CommandLineTool into sibling steps."""
    modified = False
    # don't modify clt, modify step.run
    target_clt = cast(cwl.CommandLineTool, step.run)
    inputs = empty_inputs(clt)
    if not step.id:
        return False
    step_id = step.id.split("#")[-1]
    if clt.arguments and not skip_command_line1:
        for index, arg in enumerate(clt.arguments):
            if isinstance(arg, str):
                expression = get_expression(arg, inputs, None)
                if expression:
                    modified = True
                    inp_id = f"_arguments_{index}"
                    etool_id = f"_expression_{step_id}{inp_id}"
                    target_type = "Any"
                    target = cwl.InputParameter(id="", type_=target_type)
                    replace_step_clt_expr_with_etool(
                        expression, etool_id, parent, target, step, replace_etool
                    )
                    new_target_clt_arguments = list(target_clt.arguments or [])
                    new_target_clt_arguments[index] = cwl.CommandLineBinding(
                        valueFrom=f"$(inputs.{inp_id})"
                    )
                    target_clt.arguments = new_target_clt_arguments
                    new_target_clt_inputs = list(target_clt.inputs)
                    new_target_clt_inputs.append(
                        cwl.CommandInputParameter(
                            id=inp_id,
                            type_=target_type,
                        )
                    )
                    target_clt.inputs = new_target_clt_inputs
                    new_step_ins = list(step.in_)
                    new_step_ins.append(
                        cwl.WorkflowStepInput(id=f"{etool_id}/result", source=inp_id)
                    )
                    step.in_ = new_step_ins
                    remove_JSReq(target_clt, skip_command_line1)
            elif isinstance(arg, cwl.CommandLineBinding) and arg.valueFrom:
                expression = get_expression(arg.valueFrom, inputs, None)
                if expression:
                    modified = True
                    inp_id = f"_arguments_{index}"
                    etool_id = f"_expression_{step_id}{inp_id}"
                    target_type = "Any"
                    target = cwl.InputParameter(id="", type_=target_type)
                    replace_step_clt_expr_with_etool(
                        expression, etool_id, parent, target, step, replace_etool
                    )
                    new_target_clt_arguments = list(target_clt.arguments or [])
                    new_target_clt_arguments[index] = cwl.CommandLineBinding(
                        valueFrom="$(inputs.{})".format(inp_id)
                    )
                    target_clt.arguments = new_target_clt_arguments
                    new_target_clt_inputs = list(target_clt.inputs)
                    new_target_clt_inputs.append(
                        cwl.CommandInputParameter(
                            id=inp_id,
                            type_=target_type,
                        )
                    )
                    target_clt.inputs = new_target_clt_inputs
                    new_step_ins = list(step.in_)
                    new_step_ins.append(
                        cwl.WorkflowStepInput(id=inp_id, source=f"{etool_id}/result")
                    )
                    step.in_ = new_step_ins
                    remove_JSReq(target_clt, skip_command_line1)
    for streamtype in "stdout", "stderr":  # add 'stdin' for v1.1 version
        stream_value = getattr(clt, streamtype)
        if stream_value:
            expression = get_expression(stream_value, inputs, None)
            if expression:
                modified = True
                inp_id = f"_{streamtype}"
                etool_id = f"_expression_{step_id}{inp_id}"
                target_type = "string"
                target = cwl.InputParameter(id="", type_=target_type)
                replace_step_clt_expr_with_etool(
                    expression, etool_id, parent, target, step, replace_etool
                )
                setattr(target_clt, streamtype, f"$(inputs.{inp_id})")
                new_target_clt_inputs = list(target_clt.inputs)
                new_target_clt_inputs.append(
                    cwl.CommandInputParameter(id=inp_id, type_=target_type)
                )
                target_clt.inputs = new_target_clt_inputs
                new_step_ins = list(step.in_)
                new_step_ins.append(
                    cwl.WorkflowStepInput(id=inp_id, source=f"{etool_id}/result")
                )
                step.in_ = new_step_ins
    for inp in clt.inputs:
        if not skip_command_line1 and inp.inputBinding and inp.inputBinding.valueFrom:
            expression = get_expression(
                inp.inputBinding.valueFrom, inputs, example_input(inp.type_)
            )
            if expression:
                modified = True
                self_id = inp.id.split("#")[-1]
                inp_id = f"_{self_id}_valueFrom"
                etool_id = f"_expression_{step_id}{inp_id}"
                replace_step_clt_expr_with_etool(
                    expression, etool_id, parent, inp, step, replace_etool, self_id
                )
                inp.inputBinding.valueFrom = f"$(inputs.{inp_id})"
                new_target_clt_inputs = list(target_clt.inputs)
                new_target_clt_inputs.append(
                    cwl.CommandInputParameter(
                        id=inp_id,
                        type_=plain_input_schema_to_clt_input_schema(inp.type_),
                    )
                )
                target_clt.inputs = new_target_clt_inputs
                new_step_ins = list(step.in_)
                new_step_ins.append(
                    cwl.WorkflowStepInput(id=inp_id, source=f"{etool_id}/result")
                )
                step.in_ = new_step_ins
    for outp in clt.outputs:
        if outp.outputBinding:
            if outp.outputBinding.glob:
                expression = get_expression(outp.outputBinding.glob, inputs, None)
                if expression:
                    modified = True
                    inp_id = "_{}_glob".format(outp.id.split("#")[-1])
                    etool_id = f"_expression_{step_id}{inp_id}"
                    glob_target_type: CommandInputTypeSchemas = [
                        "string",
                        cwl.CommandInputArraySchema("string", "array"),
                    ]
                    target = cwl.InputParameter(id="", type_=glob_target_type)
                    replace_step_clt_expr_with_etool(
                        expression, etool_id, parent, target, step, replace_etool
                    )
                    outp.outputBinding.glob = f"$(inputs.{inp_id})"
                    new_target_clt_inputs = list(target_clt.inputs)
                    new_target_clt_inputs.append(
                        cwl.CommandInputParameter(
                            id=inp_id,
                            type_=glob_target_type,
                        )
                    )
                    target_clt.inputs = new_target_clt_inputs
                    new_step_ins = list(step.in_)
                    new_step_ins.append(
                        cwl.WorkflowStepInput(id=inp_id, source=f"{etool_id}/result")
                    )
                    step.in_ = new_step_ins
            if outp.outputBinding.outputEval and not skip_command_line2:
                self: CWLOutputType = [
                    {
                        "class": "File",
                        "basename": "base.name",
                        "nameroot": "base",
                        "nameext": "name",
                        "path": "/tmp/base.name",  # nosec
                        "dirname": "/tmp",  # nosec
                    }
                ]
                if outp.outputBinding.loadContents:
                    cast(dict[Any, Any], self)[0]["contents"] = "stuff"
                expression = get_expression(outp.outputBinding.outputEval, inputs, self)
                if expression:
                    modified = True
                    outp_id = outp.id.split("#")[-1]
                    inp_id = f"_{outp_id}_outputEval"
                    etool_id = f"expression{inp_id}"
                    sub_wf_outputs = cltool_step_outputs_to_workflow_outputs(
                        step, etool_id, outp_id
                    )
                    self_type = cwl.InputParameter(
                        id="",
                        type_=cwl.InputArraySchema("File", "array", None, None),
                    )
                    if isinstance(outp, cwl.CommandOutputParameter):
                        target = parameter_to_plain_input_paramater(outp)
                    else:
                        target = outp
                    etool = generate_etool_from_expr(
                        expression, target, False, self_type, [clt, step, parent]
                    )
                    if outp.outputBinding.loadContents:
                        etool.inputs[0].inputBinding = cwl.CommandLineBinding(
                            loadContents=True
                        )
                    etool.inputs = list(etool.inputs) + process_inputs_to_etool_inputs(
                        clt
                    )
                    sub_wf_inputs = process_inputs_to_etool_inputs(clt)
                    orig_step_inputs = copy.deepcopy(step.in_)
                    for orig_step_input in orig_step_inputs:
                        if is_sequence(orig_step_input.source):
                            new_orig_step_input_source = list(orig_step_input.source)
                            for index, source in enumerate(orig_step_input.source):
                                new_orig_step_input_source[index] = source.split("#")[
                                    -1
                                ]
                            orig_step_input.source = new_orig_step_input_source
                        elif orig_step_input.source is None:
                            continue
                        else:
                            orig_step_input.source = orig_step_input.source.split("#")[
                                -1
                            ]
                    orig_step_inputs = [
                        x for x in orig_step_inputs if not x.id.startswith("_")
                    ]
                    for wsi in orig_step_inputs:
                        wsi.source = wsi.id
                        wsi.linkMerge = None
                    if replace_etool:
                        processes = [parent]
                        final_etool: cwl.CommandLineTool | cwl.ExpressionTool = (
                            etool_to_cltool(etool, find_expressionLib(processes))
                        )
                    else:
                        final_etool = etool
                    etool_step = cwl.WorkflowStep(
                        id=etool_id,
                        in_=orig_step_inputs,
                        out=[cwl.WorkflowStepOutput("result")],
                        run=final_etool,
                        scatterMethod=step.scatterMethod,
                    )
                    new_clt_step = copy.copy(
                        step
                    )  # a deepcopy would be convenient, but params2.cwl gives it problems
                    new_clt_step.id = new_clt_step.id.split("#")[-1]
                    new_clt_step.run = copy.copy(target_clt)
                    new_clt_step.run.id = ""
                    remove_JSReq(new_clt_step.run, skip_command_line1)
                    for new_outp in new_clt_step.run.outputs:
                        if new_outp.id.split("#")[-1] == outp_id:
                            if isinstance(
                                new_outp,
                                (
                                    cwl.WorkflowOutputParameter,
                                    cwl.ExpressionToolOutputParameter,
                                ),
                            ):
                                new_outp.type_ = cwl.OutputArraySchema(
                                    items="File", type_="array"
                                )
                            elif isinstance(new_outp, cwl.CommandOutputParameter):
                                if new_outp.outputBinding:
                                    new_outp.outputBinding.outputEval = None
                                    new_outp.outputBinding.loadContents = None
                                new_outp.type_ = cwl.CommandOutputArraySchema(
                                    items="File",
                                    type_="array",
                                )
                            else:
                                raise Exception(
                                    "Unimplemented OutputParameter type: %s",
                                    type(new_outp),
                                )
                    new_clt_step.in_ = copy.deepcopy(step.in_)
                    for wsi2 in new_clt_step.in_:
                        wsi2.id = wsi2.id.split("/")[-1]
                        wsi2.source = wsi2.id
                        wsi2.linkMerge = None
                    new_clt_step_out = list(new_clt_step.out)
                    for index, out in enumerate(new_clt_step_out):
                        if isinstance(out, str):
                            new_clt_step_out[index] = out.split("/")[-1]
                        else:
                            out.id = out.id.split("/")[-1]
                    new_clt_step.out = new_clt_step_out
                    for tool_inp in new_clt_step.run.inputs:
                        tool_inp.id = tool_inp.id.split("#")[-1]
                    for tool_out in new_clt_step.run.outputs:
                        tool_out.id = tool_out.id.split("#")[-1]
                    sub_wf_steps = [new_clt_step, etool_step]
                    sub_workflow = cwl.Workflow(
                        inputs=sub_wf_inputs,
                        outputs=sub_wf_outputs,
                        steps=sub_wf_steps,
                        cwlVersion=parent.cwlVersion,
                    )
                    if step.scatter:
                        new_clt_step.scatter = None
                    step.run = sub_workflow
                    rename_step_source(
                        sub_workflow,
                        f"{step_id}/{outp_id}",
                        f"{etool_id}/result",
                    )
                    orig_step_inputs.append(
                        cwl.WorkflowStepInput(id="self", source=f"{step_id}/{outp_id}")
                    )
                    if not parent.requirements:
                        parent.requirements = [cwl.SubworkflowFeatureRequirement()]
                    else:
                        has_sub_wf_req = False
                        for req in parent.requirements:
                            if isinstance(req, cwl.SubworkflowFeatureRequirement):
                                has_sub_wf_req = True
                        if not has_sub_wf_req:
                            new_parent_reqs = list(parent.requirements)
                            new_parent_reqs.append(cwl.SubworkflowFeatureRequirement())
                            parent.requirements = new_parent_reqs
    return modified


def rename_step_source(workflow: cwl.Workflow, old: str, new: str) -> None:
    """Update step source names to the new name."""

    def simplify_wf_ids(uris: Sequence[str] | str | None) -> set[str]:
        if isinstance(uris, str):
            uri_seq: Sequence[str] = [uris]
        elif uris is None:
            return set()
        else:
            uri_seq = uris
        return {uri.split("#")[-1].split("/", 1)[1] for uri in uri_seq}

    def simplify_step_id(uri: str) -> str:
        return uri.split("#")[-1]

    for wf_outp in workflow.outputs:
        simplified_wf_ids = simplify_wf_ids(wf_outp.outputSource)
        if wf_outp.outputSource and old in simplified_wf_ids:
            simplified_wf_ids.remove(old)
            simplified_wf_ids.add(new)
            wf_outp.outputSource = list(simplified_wf_ids)
    for step in workflow.steps:
        if step.in_:
            for inp in step.in_:
                if inp.source:
                    if isinstance(inp.source, str):
                        source_id = (
                            simplify_step_id(inp.source)
                            if "#" in inp.source
                            else inp.source
                        )
                        if source_id == old:
                            inp.source = new
                    else:
                        for index, source in enumerate(inp.source):
                            if simplify_step_id(source) == old:
                                new_inp_source = list(inp.source)
                                new_inp_source[index] = new
                                inp.source = new_inp_source


def remove_JSReq(
    process: cwl.CommandLineTool | cwl.WorkflowStep | cwl.Workflow,
    skip_command_line1: bool,
) -> None:
    """Since the InlineJavascriptRequirement is longer needed, remove it."""
    if skip_command_line1 and isinstance(process, cwl.CommandLineTool):
        return
    if process.hints:
        process.hints = [
            hint
            for hint in process.hints
            if not isinstance(hint, cwl.InlineJavascriptRequirement)
        ]
        if not process.hints:
            process.hints = None
    if process.requirements:
        process.requirements = [
            req
            for req in process.requirements
            if not isinstance(req, cwl.InlineJavascriptRequirement)
        ]
        if not process.requirements:
            process.requirements = None


def replace_step_clt_expr_with_etool(
    expr: str,
    name: str,
    workflow: cwl.Workflow,
    target: cwl.InputParameter,
    step: cwl.WorkflowStep,
    replace_etool: bool,
    self_name: str | None = None,
) -> None:
    """Convert a step level CWL Expression to a sibling expression step."""
    assert not isinstance(step.run, str)
    etool_inputs = process_inputs_to_etool_inputs(step.run)
    temp_etool = generate_etool_from_expr2(
        expr, target, etool_inputs, self_name, step.run, [workflow]
    )
    if replace_etool:
        processes = [workflow]
        etool: cwl.ExpressionTool | cwl.CommandLineTool = etool_to_cltool(
            temp_etool, find_expressionLib(processes)
        )
    else:
        etool = temp_etool
    wf_step_inputs = copy.deepcopy(step.in_)
    for wf_step_input in wf_step_inputs:
        wf_step_input.id = wf_step_input.id.split("/")[-1]
    wf_step_inputs = [x for x in wf_step_inputs if not x.id.startswith("_")]
    new_steps = list(workflow.steps)
    new_steps.append(
        cwl.WorkflowStep(
            id=name,
            in_=wf_step_inputs,
            out=[cwl.WorkflowStepOutput("result")],
            run=etool,
        )
    )
    workflow.steps = new_steps


def replace_step_process_hintreq_expr_with_etool(
    expr: str,
    name: str,
    workflow: cwl.Workflow,
    target: cwl.InputParameter,
    step: cwl.WorkflowStep,
    replace_etool: bool,
    self_name: str | None = None,
) -> cwl.CommandLineTool | cwl.ExpressionTool:
    """Factor out an expression inside a CommandLineTool req or hint into a sibling step."""
    # Same as replace_step_clt_expr_with_etool or different?
    assert not isinstance(step.run, str)
    etool_inputs = process_inputs_to_etool_inputs(step.run)
    temp_etool = generate_etool_from_expr2(
        expr, target, etool_inputs, self_name, step.run, [workflow]
    )
    if replace_etool:
        processes = [workflow]
        etool: cwl.CommandLineTool | cwl.ExpressionTool = etool_to_cltool(
            temp_etool, find_expressionLib(processes)
        )
    else:
        etool = temp_etool
    wf_step_inputs = copy.deepcopy(step.in_)
    for wf_step_input in wf_step_inputs:
        wf_step_input.id = wf_step_input.id.split("/")[-1]
    wf_step_inputs = [x for x in wf_step_inputs if not x.id.startswith("_")]
    new_steps = list(workflow.steps)
    new_steps.append(
        cwl.WorkflowStep(
            id=name,
            in_=wf_step_inputs,
            out=[cwl.WorkflowStepOutput("result")],
            run=etool,
        )
    )
    workflow.steps = new_steps
    return etool


def process_inputs_to_etool_inputs(
    tool: (
        cwl.CommandLineTool | cwl.ExpressionTool | cwl.ProcessGenerator | cwl.Workflow
    ),
) -> list[cwl.InputParameter]:
    """Copy Process input parameters to matching ExpressionTool versions."""
    inputs = []
    if tool.inputs:
        for process_inp in tool.inputs:
            process_inp_id = process_inp.id.split("#")[-1].split("/")[-1]
            if not process_inp_id.startswith("_"):
                inputs.append(
                    cwl.InputParameter(
                        id=process_inp_id,
                        label=process_inp.label,
                        secondaryFiles=process_inp.secondaryFiles,
                        streamable=process_inp.streamable,
                        doc=process_inp.doc,
                        format=process_inp.format,
                        default=process_inp.default,
                        type_=process_inp.type_,
                        extension_fields=process_inp.extension_fields,
                        loadingOptions=process_inp.loadingOptions,
                    )
                )
    return inputs


def cltool_step_outputs_to_workflow_outputs(
    cltool_step: cwl.WorkflowStep, etool_step_id: str, etool_out_id: str
) -> list[cwl.WorkflowOutputParameter]:
    """
    Copy CommandLineTool outputs into the equivalent Workflow output parameters.

    Connects the outputSources for each of the new output parameters to the step
    they came from.
    """
    outputs: list[cwl.WorkflowOutputParameter] = []
    if not cltool_step.id:
        raise WorkflowException(f"Missing step id from {cltool_step}.")
    default_step_id = cltool_step.id.split("#")[-1]
    assert not isinstance(cltool_step.run, str)
    if cltool_step.run.outputs:
        for clt_out in cltool_step.run.outputs:
            clt_out_id = clt_out.id.split("#")[-1].split("/")[-1]
            if clt_out_id == etool_out_id:
                outputSource = f"{etool_step_id}/result"
            else:
                outputSource = f"{default_step_id}/{clt_out_id}"
            if not clt_out_id.startswith("_"):
                outputs.append(
                    cwl.WorkflowOutputParameter(
                        id=clt_out_id,
                        label=clt_out.label,
                        secondaryFiles=clt_out.secondaryFiles,
                        streamable=clt_out.streamable,
                        doc=clt_out.doc,
                        format=clt_out.format,
                        outputSource=outputSource,
                        type_=clt_out.type_,
                        extension_fields=clt_out.extension_fields,
                        loadingOptions=clt_out.loadingOptions,
                    )
                )
    return outputs


def generate_etool_from_expr2(
    expr: str,
    target: cwl.InputParameter,
    inputs: Sequence[
        cwl.InputParameter | cwl.CommandInputParameter | cwl.CommandOutputParameter
    ],
    self_name: str | None = None,
    process: (
        cwl.CommandLineTool
        | cwl.ExpressionTool
        | cwl.Workflow
        | cwl.ProcessGenerator
        | None
    ) = None,
    extra_processes: None | (
        Sequence[cwl.Workflow | cwl.WorkflowStep | cwl.CommandLineTool]
    ) = None,
) -> cwl.ExpressionTool:
    """Generate an ExpressionTool to achieve the same result as the given expression."""
    outputs = yaml.comments.CommentedSeq()
    outputs.append(
        cwl.ExpressionToolOutputParameter(
            id="result",
            label=target.label,
            secondaryFiles=target.secondaryFiles,
            streamable=target.streamable,
            doc=target.doc,
            format=target.format[0] if target.format else None,
            type_=plain_input_schema_to_plain_output_schema(target.type_),
        )
    )
    expression = "${"
    if self_name:
        expression += f"\n  var self=inputs.{self_name};"
    expression += (
        """
  return {"result": function(){"""
        + expr[2:-2]
        + """}()};
 }"""
    )
    hints = None
    procs: list[
        cwl.CommandLineTool
        | cwl.ExpressionTool
        | cwl.Workflow
        | cwl.WorkflowStep
        | cwl.ProcessGenerator
    ] = []
    if process:
        procs.append(process)
    if extra_processes:
        procs.extend(extra_processes)
    inlineJSReq = cwl.InlineJavascriptRequirement(find_expressionLib(procs))
    reqs: MutableSequence[
        cwl.CUDARequirement
        | cwl.DockerRequirement
        | cwl.EnvVarRequirement
        | cwl.InitialWorkDirRequirement
        | cwl.InlineJavascriptRequirement
        | cwl.InplaceUpdateRequirement
        | cwl.LoadListingRequirement
        | cwl.MPIRequirement
        | cwl.MultipleInputFeatureRequirement
        | cwl.NetworkAccess
        | cwl.ResourceRequirement
        | cwl.ScatterFeatureRequirement
        | cwl.SchemaDefRequirement
        | cwl.Secrets
        | cwl.ShellCommandRequirement
        | cwl.ShmSize
        | cwl.SoftwareRequirement
        | cwl.StepInputExpressionRequirement
        | cwl.SubworkflowFeatureRequirement
        | cwl.TimeLimit
        | cwl.WorkReuse
    ] = [inlineJSReq]
    if process:
        if process.hints:
            hints = copy.deepcopy(process.hints)
            hints = [
                x
                for x in copy.deepcopy(hints)
                if not isinstance(x, cwl.InitialWorkDirRequirement)
            ]
        if process.requirements:
            reqs.extend(copy.deepcopy(process.requirements))
            reqs[:] = [
                x for x in reqs if not isinstance(x, cwl.InitialWorkDirRequirement)
            ]
    return cwl.ExpressionTool(
        id="_:" + str(uuid.uuid4()),
        inputs=parameters_to_plain_input_paramaters(inputs),
        outputs=outputs,
        expression=expression,
        requirements=reqs,
        cwlVersion="v1.0",
    )


def traverse_step(
    step: cwl.WorkflowStep,
    parent: cwl.Workflow,
    replace_etool: bool,
    skip_command_line1: bool,
    skip_command_line2: bool,
) -> bool:
    """Process the given WorkflowStep."""
    modified = False
    inputs = empty_inputs(step, parent)
    if not step.id:
        return False
    step_id = step.id.split("#")[-1]
    original_process = copy.deepcopy(step.run)
    assert not isinstance(original_process, str)
    assert not isinstance(step.run, str)
    original_step_ins = copy.deepcopy(step.in_)
    for inp in step.in_:
        if inp.valueFrom:
            if not inp.source:
                self = None
            else:
                self = []
                for source in inp.source:
                    if not step.scatter:
                        self.append(
                            example_input(
                                utils.type_for_source(parent, source.split("#")[-1])
                            )
                        )
                    else:
                        scattered_source_type = utils.type_for_source(parent, source)
                        if is_sequence(scattered_source_type):
                            for stype in scattered_source_type:
                                self.append(example_input(stype.type_))
                        else:
                            self.append(example_input(scattered_source_type.type_))
            expression = get_expression(inp.valueFrom, inputs, self)
            if expression:
                modified = True
                etool_id = "_expression_{}_{}".format(step_id, inp.id.split("/")[-1])
                target = get_input_for_id(inp.id, original_process)
                if not target:
                    raise WorkflowException("target not found")
                input_source_id = None
                source_type: (
                    None
                    | MutableSequence[cwl.InputParameter | cwl.CommandOutputParameter]
                    | cwl.InputParameter
                    | cwl.CommandOutputParameter
                ) = None
                if inp.source:
                    input_source_id = []
                    source_types: list[BasicInputTypeSchemas] = []
                    for source in inp.source:
                        source_id = source.split("#")[-1]
                        input_source_id.append(source_id)
                        temp_type = utils.type_for_source(step.run, source_id, parent)
                        if is_sequence(temp_type):
                            for ttype in temp_type:
                                if ttype not in source_types:
                                    source_types.append(ttype)
                        else:
                            if temp_type not in source_types:
                                source_types.append(temp_type)
                    source_type = cwl.InputParameter(
                        id="",
                        type_=cwl.InputArraySchema(source_types, "array"),
                    )
                # target.id = target.id.split('#')[-1]
                if isinstance(original_process, cwl.ExpressionTool):
                    found_JSReq = False
                    reqs: list[cwl.ProcessRequirement] = []
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
                        new_step_run_requirements = list(step.run.requirements)
                        new_step_run_requirements.append(
                            cwl.InlineJavascriptRequirement(expr_lib)
                        )
                        step.run.requirements = new_step_run_requirements
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
                    source_type,
                )
                inp.valueFrom = None
                inp.source = f"{etool_id}/result"
    # TODO: skip or special process for sub workflows?
    assert not isinstance(original_process, str)
    process_modified = process_level_reqs(
        original_process,
        step,
        parent,
        replace_etool,
        skip_command_line1,
        skip_command_line2,
    )
    if process_modified:
        modified = True
    if isinstance(original_process, cwl.CommandLineTool):
        clt_modified = traverse_CommandLineTool(
            original_process,
            parent,
            step,
            replace_etool,
            skip_command_line1,
            skip_command_line2,
        )
        if clt_modified:
            modified = True
    return modified


def workflow_step_to_InputParameters(
    step_ins: Sequence[cwl.WorkflowStepInput], parent: cwl.Workflow, except_in_id: str
) -> list[cwl.InputParameter]:
    """Create ExpressionTool InputParameters to match the given WorkflowStep inputs."""
    params = []
    for inp in step_ins:
        inp_id = inp.id.split("#")[-1].split("/")[-1]
        if inp.source and inp_id != except_in_id:
            param = copy.deepcopy(
                utils.param_for_source_id(parent, sourcenames=inp.source)
            )
            if is_sequence(param):
                for p in param:
                    if not p.type_:
                        raise WorkflowException(
                            f"Don't know how to get type id for {p!r}."
                        )
                    new_param = parameter_to_plain_input_paramater(p)
                    new_param.id = inp_id
                    new_param.type_ = clean_type_ids(new_param.type_)
                    params.append(new_param)
            else:
                if not param.type_:
                    raise WorkflowException(
                        f"Don't know how to get type id for {param!r}."
                    )
                new_param = parameter_to_plain_input_paramater(param)
                new_param.id = inp_id
                new_param.type_ = clean_type_ids(new_param.type_)
                params.append(new_param)
    return params


def replace_step_valueFrom_expr_with_etool(
    expr: str,
    name: str,
    workflow: cwl.Workflow,
    target: cwl.CommandInputParameter | cwl.InputParameter,
    step: cwl.WorkflowStep,
    step_inp: cwl.WorkflowStepInput,
    original_process: (
        cwl.CommandLineTool | cwl.ExpressionTool | cwl.ProcessGenerator | cwl.Workflow
    ),
    original_step_ins: Sequence[cwl.WorkflowStepInput],
    source: str | list[str] | None,
    replace_etool: bool,
    source_type: (
        cwl.InputParameter
        | cwl.CommandOutputParameter
        | Sequence[cwl.InputParameter | cwl.CommandOutputParameter]
        | None
    ) = None,
) -> None:
    """Replace a WorkflowStep level 'valueFrom' expression with a sibling ExpressionTool step."""
    if not step_inp.id:
        raise WorkflowException(f"Missing id in {step_inp}.")
    step_inp_id = step_inp.id.split("/")[-1]
    etool_inputs = workflow_step_to_InputParameters(
        original_step_ins, workflow, step_inp_id
    )
    if source:
        source_param = cwl.InputParameter(id="self", type_="Any")
        # TODO: would be nicer to derive a proper type; but in the face of linkMerge, this is easier for now
        etool_inputs.append(source_param)
    temp_etool = generate_etool_from_expr2(
        expr,
        target,
        etool_inputs,
        "self" if source else None,
        original_process,
        [workflow, step],
    )
    if replace_etool:
        processes: list[
            (cwl.Workflow | cwl.CommandLineTool | cwl.ExpressionTool | cwl.WorkflowStep)
        ] = [
            workflow,
            step,
        ]
        cltool = etool_to_cltool(temp_etool, find_expressionLib(processes))
        etool: cwl.ExpressionTool | cwl.CommandLineTool = cltool
    else:
        etool = temp_etool
    wf_step_inputs = list(original_step_ins)
    if source:
        wf_step_inputs.append(cwl.WorkflowStepInput(id="self", source=step_inp.source))
    for wf_step_input in wf_step_inputs:
        wf_step_input.id = wf_step_input.id.split("/")[-1]
        if wf_step_input.valueFrom:
            wf_step_input.valueFrom = None
        if wf_step_input.source:
            new_source = list(wf_step_input.source)
            for index, inp_source in enumerate(wf_step_input.source):
                new_source[index] = inp_source.split("#")[-1]
            wf_step_input.source = new_source
    wf_step_inputs = [
        x
        for x in wf_step_inputs
        if x.id and not (x.id.startswith("_") or x.id.endswith(step_inp_id))
    ]
    scatter = copy.deepcopy(step.scatter)
    if isinstance(scatter, str):
        scatter = [scatter]
    if isinstance(scatter, MutableSequence):
        for index, entry in enumerate(scatter):
            scatter[index] = entry.split("/")[-1]
    if scatter and step_inp_id in scatter:
        scatter = ["self"]
    # do we still need to scatter?
    else:
        scatter = None
    new_steps = list(workflow.steps)
    new_steps.append(
        cwl.WorkflowStep(
            id=name,
            in_=wf_step_inputs,
            out=[cwl.WorkflowStepOutput("result")],
            run=etool,
            scatter=scatter,
            scatterMethod=step.scatterMethod,
        )
    )
    workflow.steps = new_steps


def traverse_workflow(
    workflow: cwl.Workflow,
    replace_etool: bool,
    skip_command_line1: bool,
    skip_command_line2: bool,
) -> tuple[cwl.Workflow, bool]:
    """Traverse a workflow, processing each step."""
    modified = False
    for index, step in enumerate(workflow.steps):
        if isinstance(step.run, cwl.ExpressionTool) and replace_etool:
            workflow.steps[index].run = etool_to_cltool(step.run)
            modified = True
        else:
            step_modified = load_step(
                step, replace_etool, skip_command_line1, skip_command_line2
            )
            if step_modified:
                modified = True
    for step in workflow.steps:
        if not step.id.startswith("_expression"):
            step_modified = traverse_step(
                step, workflow, replace_etool, skip_command_line1, skip_command_line2
            )
            if step_modified:
                modified = True
    if process_workflow_inputs_and_outputs(workflow, replace_etool):
        modified = True
    if process_workflow_reqs_and_hints(workflow, replace_etool):
        modified = True
    if workflow.requirements:
        workflow.requirements = [
            x
            for x in workflow.requirements
            if not isinstance(
                x, (cwl.InlineJavascriptRequirement, cwl.StepInputExpressionRequirement)
            )
        ]
    else:
        workflow.requirements = None
    return workflow, modified
