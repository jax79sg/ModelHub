# Reliability Design: artifactory-stand-in

How it fails on request and keeps a version invisible until its commit.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR4.1 | Failure switches checked first on every call | A small table of switches (kind, scope, after N calls, times, sticky) is consulted before any rule; each failure kind in the functional design has a test that sets it (rule BR1.10). |
| NFR4.2 | Commit moves a version from partial to complete in one step | Files received before the commit sit in a staging area of the version; the commit swaps the staging set into the visible set under the version lock, so listing never sees a half-version (rule BR1.5). |
| NFR3.1 | No availability design | It lives for one test run and has no restart or health design beyond a ready line. |
