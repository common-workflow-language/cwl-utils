from cwl_utils.parser.cwl_v1_2 import ResourceRequirement, WorkflowStep, Workflow, CommandLineTool, save
import pytest
from schema_salad.exceptions import ValidationException

# Helper functions
def create_commandlinetool(requirements=None, inputs=None, outputs=None):
    return CommandLineTool(
        requirements=requirements or [],
        inputs=inputs or [],
        outputs=outputs or [],
    )


def create_workflow(requirements=None, steps=None, inputs=None, outputs=None):
    return Workflow(
        requirements=requirements or [],
        steps=steps or [],
        inputs=inputs or [],
        outputs=outputs or [],
    )


def create_step(requirements=None, run=None, in_=None, out=None):
    return WorkflowStep(
        requirements=requirements or [],
        run=run,
        in_=in_ or [],
        out=out or [],
    )

@pytest.mark.parametrize(
    "bad_min_max_reqs",
    [
        # cores
        ResourceRequirement(coresMin=4, coresMax=2),
        # ram
        ResourceRequirement(ramMin=2048, ramMax=1024),
        # tmpdir
        ResourceRequirement(tmpdirMin=1024, tmpdirMax=512),
        # outdir
        ResourceRequirement(outdirMin=512, outdirMax=256),
    ],
)
def test_bad_min_max_resource_reqs(bad_min_max_reqs):
    """
    Test invalid min/max resource requirements in CWL objects.
    """

    # CommandlineTool with bad minmax reqs
    clt = create_commandlinetool(requirements=[bad_min_max_reqs])
    with pytest.raises(ValidationException):
        save(clt)

    # WorkflowStep.run with bad minmax reqs
    step_bad_run = create_step(run=clt)
    workflow = create_workflow(steps=[step_bad_run])
    with pytest.raises(ValidationException):
        save(workflow)

    # WorkflowStep with bad minmax reqs
    clt = create_commandlinetool()
    step = create_step(run=clt, requirements=[bad_min_max_reqs])
    workflow = create_workflow(steps=[step])
    with pytest.raises(ValidationException):
        save(workflow)

    # Workflow with bad minmax reqs
    workflow = create_workflow(requirements=[bad_min_max_reqs])
    with pytest.raises(ValidationException):
        save(workflow)

    # NestedWorkflow with bad minmax reqs
    nest_workflow = create_workflow(requirements=[bad_min_max_reqs])
    step = create_step(run=nest_workflow)
    workflow = create_workflow(steps=[step])
    with pytest.raises(ValidationException):
        save(workflow)

    # DeepNestedWorkflow with bad minmax reqs
    deep_workflow = create_workflow(requirements=[bad_min_max_reqs])
    deep_step = create_step(run=deep_workflow)
    nest_workflow = create_workflow(steps=[deep_step])
    step = create_step(run=nest_workflow)
    workflow = create_workflow(steps=[step])
    with pytest.raises(ValidationException):
        save(workflow)
