# modelhub

Pull Hugging Face repos (weights, README, metadata) on an internet-connected host, carry them
across the airgap as a single verified tar, and restore them on-prem.

```
online host                          airgap                    on-prem host
modelhub pull org/name  ->  modelhub bundle  ->  (transfer)  ->  modelhub unpack --hf-cache
```

## Usage

```bash
# online
modelhub pull meta-llama/Llama-3.1-8B -o pulled --exclude "original/*"   # HF_TOKEN for gated repos
modelhub bundle pulled/meta-llama/Llama-3.1-8B -o llama.tar

# on-prem (no internet)
modelhub unpack llama.tar -d /srv/models/meta-llama/Llama-3.1-8B --hf-cache /srv/hf-cache
HF_HUB_CACHE=/srv/hf-cache HF_HUB_OFFLINE=1 python -c "from transformers import AutoModel; AutoModel.from_pretrained('meta-llama/Llama-3.1-8B')"
```

Pulled layout: `snapshot/` (repo files verbatim), `metadata/` (`repo_info.json`, `refs.json`),
`manifest.json` (pinned commit sha + size/sha256 per file). `verify` re-checks it anywhere.

## Development

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest                      # single test: pytest tests/test_airgap_roundtrip.py::test_verify_detects_corruption
ruff check .
```
