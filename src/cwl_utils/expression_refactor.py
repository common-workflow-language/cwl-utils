#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2018-2021 Michael R. Crusoe
"""CWL Expression refactoring tool for CWL."""

import argparse
import copy
import logging
import shutil
import sys
from collections.abc import MutableMapping, MutableSequence, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any, Protocol, cast, Literal, overload

from ruamel.yaml.main import YAML
from ruamel.yaml.scalarstring import walk_tree
from schema_salad.runtime import save, LoadingOptions

from cwl_utils import (
    cwl_v1_0_expression_refactor,
    cwl_v1_1_expression_refactor,
    cwl_v1_2_expression_refactor,
)
from cwl_utils.errors import WorkflowException
from cwl_utils.loghandler import _logger as _cwlutilslogger
from cwl_utils.parser import (
    cwl_v1_0,
    cwl_v1_1,
    cwl_v1_2,
    WorkflowStep,
    Process,
    WorkflowInputParameter,
    OperationInputParameter,
    CommandInputParameter,
    Workflow,
    CommandOutputParameter,
    ExpressionTool,
    InitialWorkDirRequirement,
    InlineJavascriptRequirement,
    ProcessRequirement,
    CommandLineTool,
    load_document_by_uri,
    CommandLineBinding,
    AbstractProcess,
)
from cwl_utils.parser.utils import type_for_source
from cwl_utils.types import CWLFileType, CWLDirectoryType
from cwl_utils.utils import get_step_uri

_logger = logging.getLogger("cwl-expression-refactor")  # pylint: disable=invalid-name
defaultStreamHandler = logging.StreamHandler()  # pylint: disable=invalid-name
_logger.addHandler(defaultStreamHandler)
_logger.setLevel(logging.INFO)
_cwlutilslogger.setLevel(100)

save_type = (
    MutableMapping[str, Any] | MutableSequence[Any] | int | float | bool | str | None
)


class saveCWL(Protocol):
    """Shortcut type for CWL v1.x parse.save()."""

    def __call__(
        self,
        val: Any,
        top: bool = True,
        base_url: str = "",
        relative_uris: bool = True,
    ) -> save_type:
        """Must use this instead of a Callable due to the keyword args."""
        ...


def arg_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Tool to refactor CWL documents so that any CWL expression "
        "are separate steps as either ExpressionTools or CommandLineTools. Exit code 7 "
        "means a single CWL document was provided but it did not need modification."
    )
    parser.add_argument(
        "--etools",
        help="Output ExpressionTools, don't go all the way to CommandLineTools.",
        action="store_true",
    )
    parser.add_argument(
        "--skip-some1",
        help="Don't process CommandLineTool.inputs.inputBinding and CommandLineTool.arguments sections.",
        action="store_true",
    )
    parser.add_argument(
        "--skip-some2",
        help="Don't process CommandLineTool.outputEval or "
        "CommandLineTool.requirements.InitialWorkDirRequirement.",
        action="store_true",
    )
    parser.add_argument("dir", help="Directory in which to save converted files")
    parser.add_argument(
        "inputs",
        nargs="+",
        help="One or more CWL documents.",
    )
    return parser


def parse_args(args: list[str]) -> argparse.Namespace:
    """Parse the command line options."""
    return arg_parser().parse_args(args)


def add_input_to_process(
    process: Process,
    cwlVersion: Literal["v1.0", "v1.1", "v1.2"],
    name: str,
    inptype: Any,
    loadingOptions: LoadingOptions,
) -> None:
    match process.cwlVersion or cwlVersion:
        case "v1.0":
            return cwl_v1_0_expression_refactor.add_input_to_process(
                cast(cwl_v1_0.Process, process), name, inptype, loadingOptions
            )
        case "v1.1":
            return cwl_v1_1_expression_refactor.add_input_to_process(
                cast(cwl_v1_1.Process, process), name, inptype, loadingOptions
            )
        case "v1.2":
            return cwl_v1_2_expression_refactor.add_input_to_process(
                cast(cwl_v1_2.Process, process), name, inptype, loadingOptions
            )
        case _:
            raise WorkflowException(
                f"Sorry, {process.cwlVersion or cwlVersion} is not a supported CWL version by this tool.",
            )


def cltool_inputs_to_etool_inputs(
    tool: CommandLineTool, cwlVersion: Literal["v1.0", "v1.1", "v1.2"]
) -> Sequence[WorkflowInputParameter]:
    match tool.cwlVersion or cwlVersion:
        case "v1.0":
            return cwl_v1_0_expression_refactor.cltool_inputs_to_etool_inputs(
                cast(cwl_v1_0.CommandLineTool, tool)
            )
        case "v1.1":
            return cwl_v1_1_expression_refactor.cltool_inputs_to_etool_inputs(
                cast(cwl_v1_1.CommandLineTool, tool)
            )
        case "v1.2":
            return cwl_v1_2_expression_refactor.cltool_inputs_to_etool_inputs(
                cast(cwl_v1_2.CommandLineTool, tool)
            )
        case _:
            raise WorkflowException(
                f"Sorry, {tool.cwlVersion or cwlVersion} is not a supported CWL version by this tool.",
            )


@overload
def empty_inputs(
    process_or_step: Process,
    context: dict[str, tuple[Process, bool]] | None = ...,
    parent: Workflow | None = ...,
) -> dict[str, Any]: ...


@overload
def empty_inputs(
    process_or_step: WorkflowStep,
    context: dict[str, tuple[Process, bool]],
    parent: Workflow,
) -> dict[str, Any]: ...


def empty_inputs(
    process_or_step: Process | WorkflowStep,
    context: dict[str, tuple[Process, bool]] | None = None,
    parent: Workflow | None = None,
) -> dict[str, Any]:
    """Produce a mock input object for the given inputs."""
    result = {}
    if isinstance(process_or_step, Process):
        for param in process_or_step.inputs:
            result[param.id.split("#")[-1]] = example_input(param.type_)
    else:
        for param1 in process_or_step.in_:
            param_id = param1.id.split("/")[-1]
            if param1.source is None and param1.valueFrom:
                result[param_id] = example_input("string")
            elif param1.source is None and param1.default:
                result[param_id] = param1.default
            elif param1.source is not None:
                with suppress(WorkflowException):
                    if isinstance(process_or_step.run, str):
                        process = cast(dict[str, tuple[Process, bool]], context)[
                            get_step_uri(process_or_step)
                        ][0]
                    else:
                        process = cast(Process, process_or_step.run)
                    if (cwlVersion := process.cwlVersion) is not None:
                        result[param_id] = example_input(
                            type_for_source(
                                process,
                                cast(Literal["v1.0", "v1.1", "v1.2"], cwlVersion),
                                param1.source,
                                parent,
                            )
                        )
                    elif (cwlVersion := cast(Workflow, parent).cwlVersion) is not None:
                        result[param_id] = example_input(
                            type_for_source(
                                process,
                                cast(Literal["v1.0", "v1.1", "v1.2"], cwlVersion),
                                param1.source,
                                parent,
                            )
                        )
    return result


def etool_to_cltool(
    etool: ExpressionTool,
    cwlVersion: Literal["v1.0", "v1.1", "v1.2"],
    expressionLib: list[str] | None = None,
) -> CommandLineTool:
    cwlVersion = etool.cwlVersion if etool.cwlVersion is not None else cwlVersion
    match cwlVersion:
        case "v1.0":
            return cwl_v1_0_expression_refactor.etool_to_cltool(
                cast(cwl_v1_0.ExpressionTool, etool), expressionLib
            )
        case "v1.1":
            return cwl_v1_1_expression_refactor.etool_to_cltool(
                cast(cwl_v1_1.ExpressionTool, etool), expressionLib
            )
        case "v1.2":
            return cwl_v1_2_expression_refactor.etool_to_cltool(
                cast(cwl_v1_2.ExpressionTool, etool), expressionLib
            )
        case _:
            raise WorkflowException(
                f"Sorry, {cwlVersion} is not a supported CWL version by this tool.",
            )


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


def find_expressionLib(
    processes: Sequence[Process | WorkflowStep],
) -> list[str] | None:
    """
    Return the expressionLib from the highest priority InlineJavascriptRequirement.

    processes: should be in order of least important to most important
    (Workflow, WorkflowStep, ... CommandLineTool/ExpressionTool)
    """
    for process in reversed(copy.copy(processes)):
        if process.requirements:
            for req in process.requirements:
                if isinstance(req, InlineJavascriptRequirement):
                    return cast(list[str] | None, copy.deepcopy(req.expressionLib))
    return None


def generate_etool_from_expr2(
    expr: str,
    cwlVersion: Literal["v1.0", "v1.1", "v1.2"],
    target: CommandInputParameter | WorkflowInputParameter | OperationInputParameter,
    inputs: Sequence[
        CommandInputParameter | CommandOutputParameter | WorkflowInputParameter
    ],
    self_name: str | None = None,
    process: Process | None = None,
    extra_processes: Sequence[Process | WorkflowStep] | None = None,
) -> ExpressionTool:
    """Generate an ExpressionTool to achieve the same result as the given expression."""
    procs: list[Process | WorkflowStep] = []
    hints: Sequence[Any] = []
    requirements: Sequence[ProcessRequirement] = []
    if process:
        procs.append(process)
    if extra_processes:
        procs.extend(extra_processes)
    if process:
        if process.hints:
            hints = [
                x for x in process.hints if not isinstance(x, InitialWorkDirRequirement)
            ]
        if process.requirements:
            requirements = [
                x
                for x in process.requirements
                if not isinstance(x, InitialWorkDirRequirement)
            ]
    cwlVersion = (
        process.cwlVersion if process and process.cwlVersion is not None else cwlVersion
    )
    match cwlVersion:
        case "v1.0":
            return cwl_v1_0_expression_refactor.generate_etool_from_expr2(
                expr=expr,
                target=cast(cwl_v1_0.InputParameter, target),
                inputs=cast(
                    Sequence[cwl_v1_0.InputParameter | cwl_v1_0.CommandOutputParameter],
                    inputs,
                ),
                expression_lib=find_expressionLib(procs),
                hints=hints,
                requirements=cast(Sequence[cwl_v1_0.ProcessRequirement], requirements),
                self_name=self_name,
            )
        case "v1.1":
            return cwl_v1_1_expression_refactor.generate_etool_from_expr2(
                expr=expr,
                target=cast(
                    cwl_v1_1.CommandInputParameter | cwl_v1_1.WorkflowInputParameter,
                    target,
                ),
                inputs=cast(
                    Sequence[
                        cwl_v1_1.CommandInputParameter
                        | cwl_v1_1.CommandOutputParameter
                        | cwl_v1_1.WorkflowInputParameter
                    ],
                    inputs,
                ),
                expression_lib=find_expressionLib(procs),
                hints=hints,
                requirements=cast(Sequence[cwl_v1_1.ProcessRequirement], requirements),
                self_name=self_name,
            )
        case "v1.2":
            return cwl_v1_2_expression_refactor.generate_etool_from_expr2(
                expr=expr,
                target=cast(
                    cwl_v1_2.CommandInputParameter
                    | cwl_v1_2.WorkflowInputParameter
                    | cwl_v1_2.OperationInputParameter,
                    target,
                ),
                inputs=cast(
                    Sequence[
                        cwl_v1_2.CommandInputParameter
                        | cwl_v1_2.CommandOutputParameter
                        | cwl_v1_2.WorkflowInputParameter
                    ],
                    inputs,
                ),
                expression_lib=find_expressionLib(procs),
                hints=hints,
                requirements=cast(Sequence[cwl_v1_2.ProcessRequirement], requirements),
                self_name=self_name,
            )
        case _:
            raise WorkflowException(
                f"Sorry, {cwlVersion} is not a supported CWL version by this tool.",
            )


@overload
def get_command_input_parameter(
    cwlVersion: Literal["v1.0"], id_: str, type_: Any
) -> cwl_v1_0.CommandInputParameter: ...


@overload
def get_command_input_parameter(
    cwlVersion: Literal["v1.1"], id_: str, type_: Any
) -> cwl_v1_1.CommandInputParameter: ...


@overload
def get_command_input_parameter(
    cwlVersion: Literal["v1.2"], id_: str, type_: Any
) -> cwl_v1_2.CommandInputParameter: ...


def get_command_input_parameter(
    cwlVersion: Literal["v1.0", "v1.1", "v1.2"], id_: str, type_: Any
) -> CommandInputParameter:
    match cwlVersion:
        case "v1.0":
            return cwl_v1_0_expression_refactor.get_command_input_parameter(id_, type_)
        case "v1.1":
            return cwl_v1_1_expression_refactor.get_command_input_parameter(id_, type_)
        case "v1.2":
            return cwl_v1_2_expression_refactor.get_command_input_parameter(id_, type_)
        case _:
            raise WorkflowException(
                f"Sorry, {cwlVersion} is not a supported CWL version by this tool.",
            )


@overload
def get_command_line_binding(
    cwlVersion: Literal["v1.0"],
    valueFrom: str | None = ...,
    loadContents: bool | None = ...,
) -> cwl_v1_0.CommandLineBinding: ...


@overload
def get_command_line_binding(
    cwlVersion: Literal["v1.1"],
    valueFrom: str | None = ...,
    loadContents: bool | None = ...,
) -> cwl_v1_1.CommandLineBinding: ...


@overload
def get_command_line_binding(
    cwlVersion: Literal["v1.2"],
    valueFrom: str | None = ...,
    loadContents: bool | None = ...,
) -> cwl_v1_2.CommandLineBinding: ...


def get_command_line_binding(
    cwlVersion: Literal["v1.0", "v1.1", "v1.2"],
    valueFrom: str | None = None,
    loadContents: bool | None = None,
) -> CommandLineBinding:
    match cwlVersion:
        case "v1.0":
            return cwl_v1_0_expression_refactor.get_command_line_binding(
                valueFrom, loadContents
            )
        case "v1.1":
            return cwl_v1_1_expression_refactor.get_command_line_binding(
                valueFrom, loadContents
            )
        case "v1.2":
            return cwl_v1_2_expression_refactor.get_command_line_binding(
                valueFrom, loadContents
            )
        case _:
            raise WorkflowException(
                f"Sorry, {cwlVersion} is not a supported CWL version by this tool.",
            )


@overload
def get_inline_javascript_requirement(
    etool: ExpressionTool,
    cwlVersion: Literal["v1.0"],
    expression_lib: list[str] | None,
) -> cwl_v1_0.InlineJavascriptRequirement: ...


@overload
def get_inline_javascript_requirement(
    etool: ExpressionTool,
    cwlVersion: Literal["v1.1"],
    expression_lib: list[str] | None,
) -> cwl_v1_1.InlineJavascriptRequirement: ...


@overload
def get_inline_javascript_requirement(
    etool: ExpressionTool,
    cwlVersion: Literal["v1.2"],
    expression_lib: list[str] | None,
) -> cwl_v1_2.InlineJavascriptRequirement: ...


def get_inline_javascript_requirement(
    etool: ExpressionTool,
    cwlVersion: Literal["v1.0", "v1.1", "v1.2"],
    expression_lib: list[str] | None,
) -> InlineJavascriptRequirement:
    match etool.cwlVersion or cwlVersion:
        case "v1.0":
            return cwl_v1_0_expression_refactor.get_inline_javascript_requirement(
                cast(cwl_v1_0.ExpressionTool, etool), expression_lib
            )
        case "v1.1":
            return cwl_v1_1_expression_refactor.get_inline_javascript_requirement(
                cast(cwl_v1_1.ExpressionTool, etool), expression_lib
            )
        case "v1.2":
            return cwl_v1_2_expression_refactor.get_inline_javascript_requirement(
                cast(cwl_v1_2.ExpressionTool, etool), expression_lib
            )
        case _:
            raise WorkflowException(
                f"Sorry, {etool.cwlVersion or cwlVersion} is not a supported CWL version by this tool.",
            )


def get_input_for_id(
    name: str, tool: Process
) -> CommandInputParameter | WorkflowInputParameter | OperationInputParameter | None:
    """Determine the CommandInputParameter for the given input name."""
    name = name.split("/")[-1]

    for inp in cast(
        list[CommandInputParameter | WorkflowInputParameter | OperationInputParameter],
        tool.inputs,
    ):
        if inp.id and inp.id.split("#")[-1].split("/")[-1] == name:
            return inp
    if isinstance(tool, Workflow) and "/" in name:
        stepname, stem = name.split("/", 1)
        for step in tool.steps:
            if step.id == stepname:
                result = get_input_for_id(stem, step.run)
                if result:
                    return result
    return None


def load_step(
    step: WorkflowStep,
    replace_etool: bool,
    skip_command_line1: bool,
    skip_command_line2: bool,
    context: dict[str, tuple[Process, bool]],
) -> bool:
    """If the step's Process is not inline, load and process it."""
    modified = False
    if isinstance(step.run, str):
        if (uri := get_step_uri(step)) not in context:
            process = cast(
                AbstractProcess,
                load_document_by_uri(
                    path=uri,
                    loadingOptions=step.loadingOptions,
                ),
            )
            if not isinstance(process, Process):
                raise Exception(
                    f"Unsupported process type: {process.__class__.__name__}"
                )
            match process.cwlVersion:
                case "v1.0":
                    process, modified = cwl_v1_0_expression_refactor.traverse(
                        cast(
                            cwl_v1_0.CommandLineTool
                            | cwl_v1_0.ExpressionTool
                            | cwl_v1_0.Workflow,
                            process,
                        ),
                        replace_etool,
                        True,
                        skip_command_line1,
                        skip_command_line2,
                        context,
                    )
                case "v1.1":
                    process, modified = cwl_v1_1_expression_refactor.traverse(
                        cast(
                            cwl_v1_1.CommandLineTool
                            | cwl_v1_1.ExpressionTool
                            | cwl_v1_1.Workflow,
                            process,
                        ),
                        replace_etool,
                        True,
                        skip_command_line1,
                        skip_command_line2,
                        context,
                    )
                case "v1.2":
                    process, modified = cwl_v1_2_expression_refactor.traverse(
                        cast(
                            cwl_v1_2.CommandLineTool
                            | cwl_v1_2.ExpressionTool
                            | cwl_v1_2.Workflow
                            | cwl_v1_2.Operation,
                            process,
                        ),
                        replace_etool,
                        True,
                        skip_command_line1,
                        skip_command_line2,
                        context,
                    )
                case _:
                    raise WorkflowException(
                        f"Sorry, {process.cwlVersion} is not a supported CWL version by this tool.",
                    )
            context[uri] = (process, modified)
    else:
        process = step.run
        if not isinstance(process, Process):
            raise Exception(f"Unsupported process type: {process.__class__.__name__}")
    return modified


def process_CommandLineTool_output(
    ctool: CommandLineTool, cwlVersion: Literal["v1.0", "v1.1", "v1.2"], outp_id: str
) -> None:
    match ctool.cwlVersion or cwlVersion:
        case "v1.0":
            cwl_v1_0_expression_refactor.process_CommandLineTool_output(
                cast(cwl_v1_0.CommandLineTool, ctool), outp_id
            )
        case "v1.1":
            cwl_v1_1_expression_refactor.process_CommandLineTool_output(
                cast(cwl_v1_1.CommandLineTool, ctool), outp_id
            )
        case "v1.2":
            cwl_v1_2_expression_refactor.process_CommandLineTool_output(
                cast(cwl_v1_2.CommandLineTool, ctool), outp_id
            )
        case _:
            raise WorkflowException(
                f"Sorry, {ctool.cwlVersion or cwlVersion} is not a supported CWL version by this tool.",
            )


def remove_JSReq(
    process: CommandLineTool | WorkflowStep | Workflow,
    skip_command_line1: bool,
) -> None:
    """Since the InlineJavascriptRequirement is longer needed, remove it."""
    if skip_command_line1 and isinstance(process, CommandLineTool):
        return
    if process.hints:
        process.hints[:] = [
            hint
            for hint in process.hints
            if not isinstance(hint, InlineJavascriptRequirement)
        ]
        if not process.hints:
            process.hints = None
    if process.requirements:
        process.requirements[:] = [
            req
            for req in process.requirements
            if not isinstance(req, InlineJavascriptRequirement)
        ]
        if not process.requirements:
            process.requirements = None


def main() -> None:
    """Console entry point."""
    sys.exit(run(sys.argv[1:]))


def run(args: list[str]) -> int:
    """Collect the arguments and run."""
    return refactor(parse_args(args))


def refactor(args: argparse.Namespace) -> int:
    """Primary processing loop."""
    return_code = 0
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    for document in args.inputs:
        _logger.info("Processing %s.", document)
        with open(document) as doc_handle:
            result = yaml.load(doc_handle)
        uri = Path(document).resolve().as_uri()
        context: dict[str, tuple[Process, bool]] = {}
        try:
            match result["cwlVersion"]:
                case "v1.0":
                    result, modified = cwl_v1_0_expression_refactor.traverse(
                        cwl_v1_0.load_document_by_yaml(result, uri),
                        not args.etools,
                        False,
                        args.skip_some1,
                        args.skip_some2,
                        context,
                    )
                case "v1.1":
                    result, modified = cwl_v1_1_expression_refactor.traverse(
                        cwl_v1_1.load_document_by_yaml(result, uri),
                        not args.etools,
                        False,
                        args.skip_some1,
                        args.skip_some2,
                        context,
                    )
                case "v1.2":
                    result, modified = cwl_v1_2_expression_refactor.traverse(
                        cwl_v1_2.load_document_by_yaml(result, uri),
                        not args.etools,
                        False,
                        args.skip_some1,
                        args.skip_some2,
                        context,
                    )
                case _:
                    _logger.error(
                        "Sorry, %s is not a supported CWL version by this tool.",
                        result["cwlVersion"],
                    )
                    return -1
            if not modified and len(args.inputs) == 1:
                return 7
            context[document] = (result, modified)
            for path, (process, modified) in context.items():
                output = Path(args.dir) / Path(path).name
                if not modified:
                    if len(args.inputs) > 1:
                        shutil.copyfile(path, output)
                        continue
                if not isinstance(process, MutableSequence):
                    result_json = save(
                        process,
                        base_url=(process.loadingOptions.fileuri or ""),
                    )
                #   ^^ Setting the base_url and keeping the default value
                #      for relative_uris=True means that the IDs in the generated
                #      JSON/YAML are kept clean of the path to the input document
                else:
                    result_json = [
                        save(result_item, base_url=result_item.loadingOptions.fileuri)
                        for result_item in process
                    ]
                walk_tree(result_json)
                # ^ converts multiline strings to nice multiline YAML
                with output.open("w", encoding="utf-8") as output_filehandle:
                    output_filehandle.write(
                        "#!/usr/bin/env cwl-runner\n"
                    )  # TODO: teach the codegen to do this?
                    yaml.dump(result_json, output_filehandle)
        except WorkflowException as exc:
            return_code = 1
            _logger.exception("Skipping %s due to error.", document, exc_info=exc)

    return return_code


if __name__ == "__main__":
    main()
