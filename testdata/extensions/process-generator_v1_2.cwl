#!/usr/bin/env cwl-runner
cwlVersion: v1.2
$namespaces:
  cwltool: "http://commonwl.org/cwltool#"
class: cwltool:ProcessGenerator
inputs:
  script: string
  dir: Directory
outputs: {}
run:
  class: CommandLineTool
  inputs:
    script: string
    dir: Directory
  outputs:
    runProcess:
      type: File
      outputBinding:
        glob: main.cwl
  requirements:
    InlineJavascriptRequirement: {}
    LoadListingRequirement:
      loadListing: shallow_listing
    InitialWorkDirRequirement:
      listing: |
        ${
         var v = inputs.dir.listing;
         v.push({entryname: "inp.py", entry: inputs.script});
         return v;
        }
  arguments: [python3, inp.py]
  stdout: main.cwl