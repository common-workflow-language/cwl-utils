#!/usr/bin/env cwl-runner
cwlVersion: v1.1
class: CommandLineTool
baseCommand: echo
inputs:
  echo_in:
    type:
      - string
      - string[]
    inputBinding: {}
stdout: out.txt
outputs:
  txt:
    type: stdout
