import os

import pytest
from modelhub_stand_in.server import StandIn

# The Xet transfer layer is not part of what the stand-in imitates (Artifactory supports it only
# up to a certain client version); tests use the Git LFS route, as the design's checklist says.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")


@pytest.fixture
def stand_in(tmp_path):
    with StandIn(token="test-token-abc", repo_key="models-hf", workdir=tmp_path) as s:
        yield s


@pytest.fixture
def api(stand_in):
    from huggingface_hub import HfApi

    return HfApi(endpoint=stand_in.hf_endpoint, token=stand_in.token)
