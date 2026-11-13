#!/usr/bin/env cwl-runner
cwlVersion: v1.0
class: Workflow
doc: |
  Each enum declares its own name, as generated workflows often do: the
  workflow's enum and the tool's are different names for the same symbols.

inputs:
  colour:
    type:
      type: enum
      name: WorkflowColour
      symbols: [red, blue]
  shade:
    type:
      type: enum
      symbols: [light, dark]

outputs:
  echoed:
    type: File
    outputSource: echo/echoed

steps:
  echo:
    run:
      class: CommandLineTool
      baseCommand: echo
      inputs:
        colour:
          type:
            type: enum
            name: ToolColour
            symbols: [red, blue]
          inputBinding: {}
        shade:
          type:
            type: enum
            symbols: [light, dark]
          inputBinding: {}
      stdout: echoed.txt
      outputs:
        echoed: stdout
    in:
      colour: colour
      shade: shade
    out: [echoed]
