# CI/CD Pipeline: common

How the shared library is built, tested and delivered. It has no infrastructure of its own: it is installed into the images of the three server units.

## Steps

1. A pull request runs ruff (check and format, line length 100) and pytest for the library on Python 3.10 and 3.12 (the existing CI matrix).
2. Tests are written first. They cover every refusal reason of the token check (expired, tampered, wrong issuer, wrong audience, wrong algorithm, unknown key, missing claim), the key refresh limit, secret and setting loading with each item missing, redaction of every secret field name, and the ready check with each dependency down.
3. A test blocks all sockets except the one it serves, to prove the library connects nowhere else.
4. A test prints, logs and serialises a loaded secret and a token and finds neither in any output.
5. The library is versioned together with the release; each server unit's image build installs it from the same commit, so the three services never run different token checks.
6. Dependencies (PyJWT, cryptography, httpx) are pinned to ranges in the project file; Dependabot and code scanning stay on.
7. There is no deployment, rollback or secret in this pipeline.
