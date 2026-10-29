cwlVersion: v1.0
class: Workflow
inputs:
  inp1:
    type: File
    secondaryFiles:
      - ".2"
    default:
      class: File
      location: hello.txt
outputs: []
steps:
  toolv10:
    in: {inp1: inp1}
    out: []
    run: tool-v1_0.cwl
  toolv11:
    in: {inp1: inp1}
    out: []
    run: tool-v1_1.cwl
  toolv12:
    in: {inp1: inp1}
    out: []
    run: tool-v1_2.cwl