#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: Workflow
doc: |
  An int workflow input wired into a File[] input of a tool in another file.
  The tool's input id is scoped by its file ("tool.cwl#files"), the step
  input's by the step ("wf.cwl#merge/files").

inputs:
  files: int

outputs:
  merged:
    type: File
    outputSource: merge/merged

steps:
  merge:
    run: step-input-type-mismatch-tool_v1_0.cwl
    in:
      files: files
    out: [merged]
