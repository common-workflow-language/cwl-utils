#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: CommandLineTool
baseCommand: cat
inputs:
  files:
    type: File[]
    inputBinding: {}
stdout: merged.txt
outputs:
  merged: stdout
