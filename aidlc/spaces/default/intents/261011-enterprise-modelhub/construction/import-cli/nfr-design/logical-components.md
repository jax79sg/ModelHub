# Logical Components: import-cli

The import command is part of the existing single program; its logical parts follow.

| Component | Role | Failure domain | Blast radius if it fails |
|-----------|------|----------------|--------------------------|
| Login and logout | Save or delete the settings | The person's computer | Importing cannot start; other commands unaffected |
| Package reader | Finds bundles and verifies them locally | The person's computer | That model fails; others continue |
| Transfer engine | Create, send pieces, start, watch | The person's computer and the network | The model in progress; resumable |
| Retry helper | Timed retries and busy waits | The person's computer | None beyond the model in progress |
| Report writer | Lines, counts and exit status | The person's computer | None |
| Output filter | Masks the token | The person's computer | None; a failure here must not print |
