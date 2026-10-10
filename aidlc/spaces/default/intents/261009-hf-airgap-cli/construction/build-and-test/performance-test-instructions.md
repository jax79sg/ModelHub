# Performance Test Instructions

## Automated

`tests/test_memory_limits.py` (block reading, small memory use on a 1 GB sparse file),
`tests/test_scale.py` (1 TB file planned without reading; 10,000 version folders listed in under 5 s;
one bundle never looks at the rest of the store), `tests/test_progress.py`.

## By hand: speed against the connection (NFR1.1)

```bash
.venv/bin/python tools/benchmark_download.py Qwen/Qwen2.5-0.5B model.safetensors --out benchmark-result.json
```

The link rate is measured with plain parallel range requests on the same file; the tool rate is
bytes over the whole pull. Target: tool at least 0.8 times link. Exit status 1 if below.
Run on the real connection of the download computer, for a file of at least 500 MB.
