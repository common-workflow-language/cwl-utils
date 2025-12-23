#!/usr/bin/env cwl-runner
class: Workflow
cwlVersion: v1.2
requirements:
  ScatterFeatureRequirement: {}
  MultipleInputFeatureRequirement: {}
  StepInputExpressionRequirement: {}
inputs:
  letters0:
    type: [string, int]
    default: "a0"
  letters1:
    type: string[]
    default: ["a1", "b1"]
  letters2:
    type: [string, int]
    default: "a2"
  letters3:
    type: string[]
    default: ["a3", "b3"]
  letters4:
    type: string
    default: "a4"
  letters5:
    type: string[]
    default: ["a5", "b5", "c5"]
  exec:
    type: bool
    default: False

outputs:
  pair:
    type: File[]
    outputSource:
     - step1/txt
     - step2/txt

steps:
  - id: step1
    run: echo.cwl
    in:
      exec: exec
    out: [txt]
    when: $(inputs.exec)
  - id: step2
    run: echo.cwl
    in: []
    out: [txt]
    when: $(inputs.exec)

