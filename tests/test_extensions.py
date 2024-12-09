from pathlib import Path

from cwl_utils.parser import cwl_v1_0, cwl_v1_1, cwl_v1_2, load_document_by_uri

from .util import get_data


def test_cuda_requirement_v1_0() -> None:
    """Test that CUDARequirement objects are correctly loaded for CWL v1.0."""
    uri = (
        Path(get_data("testdata/extensions/cuda-requirement_v1_0.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_0.CUDARequirement)


def test_cuda_requirement_v1_1() -> None:
    """Test that CUDARequirement objects are correctly loaded for CWL v1.1."""
    uri = (
        Path(get_data("testdata/extensions/cuda-requirement_v1_1.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_1.CUDARequirement)


def test_cuda_requirement_v1_2() -> None:
    """Test that CUDARequirement objects are correctly loaded for CWL v1.2."""
    uri = (
        Path(get_data("testdata/extensions/cuda-requirement_v1_2.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_2.CUDARequirement)


def test_load_listing_requirement_v1_0() -> None:
    """Test that LoadListingRequirement objects are correctly loaded for CWL v1.0."""
    uri = (
        Path(get_data("testdata/extensions/load-listing-requirement_v1_0.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_0.LoadListingRequirement)


def test_loop_v1_2() -> None:
    """Test that Loop and LoopInput objects are correctly loaded for CWL v1.2."""
    uri = (
        Path(get_data("testdata/extensions/single-var-loop_v1_2.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    cwl_step = next(iter(cwl_obj.steps))
    loop_req = next(iter(cwl_step.requirements))
    assert isinstance(loop_req, cwl_v1_2.Loop)
    assert isinstance(next(iter(loop_req.loop)), cwl_v1_2.LoopInput)


def test_inplace_update_requirement_v1_0() -> None:
    """Test that InplaceUpdateRequirement objects are correctly loaded for CWL v1.0."""
    uri = (
        Path(get_data("testdata/extensions/inplace-update-requirement_v1_0.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(
        next(iter(cwl_obj.requirements)), cwl_v1_0.InplaceUpdateRequirement
    )


def test_mpi_requirement_v1_0() -> None:
    """Test that MPIRequirement objects are correctly loaded for CWL v1.0."""
    uri = (
        Path(get_data("testdata/extensions/mpi-requirement_v1_0.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_0.MPIRequirement)


def test_mpi_requirement_v1_1() -> None:
    """Test that MPIRequirement objects are correctly loaded for CWL v1.1."""
    uri = (
        Path(get_data("testdata/extensions/mpi-requirement_v1_1.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_1.MPIRequirement)


def test_mpi_requirement_v1_2() -> None:
    """Test that MPIRequirement objects are correctly loaded for CWL v1.2."""
    uri = (
        Path(get_data("testdata/extensions/mpi-requirement_v1_2.cwl"))
        .resolve()
        .as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_2.MPIRequirement)


def test_network_access_v1_0() -> None:
    """Test that NetworkAccess objects are correctly loaded for CWL v1.0."""
    uri = (
        Path(get_data("testdata/extensions/network-access_v1_0.cwl")).resolve().as_uri()
    )
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_0.NetworkAccess)


def test_process_generator_v1_0() -> None:
    """Test that ProcessGenerator objects are correctly loaded for CWL v1.0."""
    uri = (
        Path(get_data("testdata/extensions/process-generator_v1_0.cwl"))
        .resolve()
        .as_uri()
    )
    assert isinstance(load_document_by_uri(uri), cwl_v1_0.ProcessGenerator)


def test_process_generator_v1_1() -> None:
    """Test that ProcessGenerator objects are correctly loaded for CWL v1.1."""
    uri = (
        Path(get_data("testdata/extensions/process-generator_v1_1.cwl"))
        .resolve()
        .as_uri()
    )
    assert isinstance(load_document_by_uri(uri), cwl_v1_1.ProcessGenerator)


def test_process_generator_v1_2() -> None:
    """Test that ProcessGenerator objects are correctly loaded for CWL v1.2."""
    uri = (
        Path(get_data("testdata/extensions/process-generator_v1_2.cwl"))
        .resolve()
        .as_uri()
    )
    assert isinstance(load_document_by_uri(uri), cwl_v1_2.ProcessGenerator)


def test_secrets_v1_0() -> None:
    """Test that Secrets objects are correctly loaded for CWL v1.0."""
    uri = Path(get_data("testdata/extensions/secrets_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_0.Secrets)


def test_secrets_v1_1() -> None:
    """Test that Secrets objects are correctly loaded for CWL v1.1."""
    uri = Path(get_data("testdata/extensions/secrets_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_1.Secrets)


def test_secrets_v1_2() -> None:
    """Test that Secrets objects are correctly loaded for CWL v1.2."""
    uri = Path(get_data("testdata/extensions/secrets_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_2.Secrets)


def test_shm_size_v1_0() -> None:
    """Test that ShmSize objects are correctly loaded for CWL v1.0."""
    uri = Path(get_data("testdata/extensions/shm-size_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_0.ShmSize)


def test_shm_size_v1_1() -> None:
    """Test that ShmSize objects are correctly loaded for CWL v1.1."""
    uri = Path(get_data("testdata/extensions/shm-size_v1_1.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_1.ShmSize)


def test_shm_size_v1_2() -> None:
    """Test that ShmSize objects are correctly loaded for CWL v1.2."""
    uri = Path(get_data("testdata/extensions/shm-size_v1_2.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_2.ShmSize)


def test_time_limit_v1_0() -> None:
    """Test that TimeLimit objects are correctly loaded for CWL v1.0."""
    uri = Path(get_data("testdata/extensions/time-limit_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_0.TimeLimit)


def test_work_reuse_v1_0() -> None:
    """Test that WorkReuse objects are correctly loaded for CWL v1.0."""
    uri = Path(get_data("testdata/extensions/work-reuse_v1_0.cwl")).resolve().as_uri()
    cwl_obj = load_document_by_uri(uri)
    assert isinstance(next(iter(cwl_obj.requirements)), cwl_v1_0.WorkReuse)
