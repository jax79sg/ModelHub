# Infrastructure Specification: import-cli

The import command ships inside the existing command-line program. It runs on import computers inside the organisation (Linux and Windows) and reaches the entry point of the server over TLS. Nothing about it is hosted.

## Deployment

| Facet | Choice | Rationale |
|---|---|---|
| Compute model | The existing single-file program (Linux x86-64, Windows, macOS Apple silicon) and the offline packs | NFR10.1; nothing installed beyond the program |
| Networking | Outbound HTTPS to the entry point only; no inbound | NFR5.3, NFR5.6, NFR8.1 |
| Storage | A settings file in the person's own settings folder (owner-only); no other state | NFR5.1 |
| Environments | The person's computer; developers run the command against a local stack with the stand-in | Infrastructure question 1 A |
| Infrastructure as code | None | Nothing to provision |
| Resource sizing | Memory at or below 8 GB at peak; blocks of 8 MiB | NFR7.1, NFR7.3 |

## Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| Import service entry point | The only server the command talks to | Address saved by login; https only except localhost | Hosted by the platform unit |
| Operating system trust store | Certificate verification | The system's trusted certificates; no switch to turn it off | Needs the organisation's certificate authority on the import computer |
