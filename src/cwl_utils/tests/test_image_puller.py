# SPDX-License-Identifier: Apache-2.0
"""Tests for classes for docker-extract."""

from cwl_utils.image_puller import SingularityImagePuller
from cwl_utils.singularity import get_version as get_singularity_version
from cwl_utils.singularity import is_version_2_6 as is_singularity_version_2_6
from cwl_utils.singularity import (
    is_version_3_or_newer as is_singularity_version_3_or_newer,
)

from .util import needs_singularity


@needs_singularity
class TestSingularityImagePuller:
    """Tests for SingularityImagePuller."""

    def test_get_image_name_matches_cwltool(self) -> None:
        """Make sure image names generated match those expected by cwltool."""
        if is_singularity_version_2_6():
            suffix = ".img"
        elif is_singularity_version_3_or_newer():
            suffix = ".sif"
        else:
            raise Exception(
                f"Don't know how to handle this version of singularity: {get_singularity_version()}."
            )

        def get_name(s: str) -> str:
            return SingularityImagePuller(s, None, "", False).get_image_name()

        assert get_name("some_name/repo:123") == f"some___name_s_repo:123{suffix}"
        assert get_name("some/name_repo:123") == f"some_s_name___repo:123{suffix}"
