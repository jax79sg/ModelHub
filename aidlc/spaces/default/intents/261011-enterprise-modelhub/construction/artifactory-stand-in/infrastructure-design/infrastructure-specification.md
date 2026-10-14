# Infrastructure Specification: artifactory-stand-in

The stand-in is test-only and never deployed. This document records what it runs on and why it needs nothing more.

## Deployment

| Facet | Choice | Rationale |
|---|---|---|
| Compute model | A thread inside the test process; no container, no service | Starts in under 2 seconds and needs no Docker on build machines (NFR9.1) |
| Networking | Binds 127.0.0.1 on a free port; no inbound or outbound network | Cannot be reached from outside the machine (NFR5.1, NFR8.1) |
| Storage | A temporary folder per run for kept file content; deleted at the end | No state survives a run (rule BR1.14) |
| Environments | Developer machines and the CI runners (Linux, Windows, macOS; Python 3.10 and 3.12); never staging or production | Tests of the import command must run everywhere it is delivered (NFR10.1) |
| Infrastructure as code | None | Nothing to provision |
| Sizing | Under 500 MB of memory; a few megabytes of disk for kept files | Virtual files above 1 MiB are not stored (NFR9.3) |

## Infrastructure Services

| Service | Role | Configuration | Notes |
|---|---|---|---|
| Test web server | In-process HTTP server (FastAPI with uvicorn) | Free local port; one token; layout flat or nested | Started and stopped by the test fixture |
| Temporary folder | Content area for kept files | Operating system temporary directory | Removed on stop |

## Not delivered

A check in the platform unit's pipeline fails the build if any image or the single-file program contains the stand-in's files (NFR5.5).
