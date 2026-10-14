# Scalability Design: artifactory-stand-in

How it holds many versions and concurrent uploads in a test run.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR7.1 | Plain dictionaries keyed by repository, organisation, model and revision | 1,000 versions of 10,000 files are a few tens of megabytes of records; no index structure is needed. |
| NFR7.2 | One lock per version | Uploads to different versions run in parallel; two commits to one version are applied one after the other, so the second sees the first's result (rule BR1.3). |
