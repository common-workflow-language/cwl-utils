cwlVersion: v1.2
class: Workflow
requirements:
  InlineJavascriptRequirement: {}
inputs:
  inp1:
    type: File
    default:
      class: File
      location: hello.txt
    secondaryFiles:
      - pattern: ".2"
        required: true
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
    when: $(true)
    run: tool-v1_2.cwl