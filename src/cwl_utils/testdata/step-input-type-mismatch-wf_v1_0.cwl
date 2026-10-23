#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: Workflow
doc: An int workflow input wired into a File[] step input, which no runner can accept.

inputs:
  files: int

outputs:
  merged:
    type: File
    outputSource: merge/merged

steps:
  merge:
    run:
      class: CommandLineTool
      baseCommand: cat
      inputs:
        files:
          type: File[]
          inputBinding: {}
      stdout: merged.txt
      outputs:
        merged: stdout
    in:
      files: files
    out: [merged]
