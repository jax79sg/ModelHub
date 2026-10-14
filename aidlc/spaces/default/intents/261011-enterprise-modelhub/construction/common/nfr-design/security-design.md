# Security Design: common

How the shared library enforces the token check, secret handling and redaction that every server unit relies on.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR5.1, NFR5.8 | One verification routine with a fixed algorithm list | PyJWT is called with the algorithm list set to RS256 and ES256 and a 60-second leeway; issuer, audience, expiry, not-before and the required claims are checked in the order of rule BR1.1; there is no other path to a valid verdict. |
| NFR5.2 | Default-deny request guard | A single guard wraps the application: only /healthz and /readyz and paths a service names one by one at start-up skip the token check; there is no pattern form (rule BR1.5). |
| NFR5.3 | Reason codes in logs, minimal answers to callers | The verdict carries a fixed reason; the guard answers 401 token_invalid with no detail and logs the code; no part of the token or its claims is formatted into any message (rule BR1.2). |
| NFR5.4 | Secret type that cannot be printed | Secrets are held in a wrapper whose string, representation and serialisation return a fixed mask; the real value is reachable only through one named accessor used at the point of use (rule BR1.6). |
| NFR5.5 | Redaction at the logging boundary | The JSON formatter masks fields whose names contain token, password, secret, pepper, authorization or cookie, and replaces any loaded secret value found in any text field (rule BR1.8). |
| NFR5.6 | Collect-then-stop start-up check | Start-up reads every needed secret and setting, collects each failure by name and type, prints one message of names only and exits; nothing starts half-configured (rules BR1.6, BR1.7). |
| NFR5.7 | Rate-limited key refresh | A refresh is tried only for an unknown key id and at most once per 60 seconds, under a lock so concurrent requests share one fetch; failure keeps the keys already held (rule BR1.4). |
| NFR5.9 | Cached keys, no network on the hot path | Signature checks use keys held in memory; the network is touched only by the refresh above, so a check costs only the signature work. |
| NFR5.10 | Library choice with explicit limits | PyJWT with cryptography; the library never accepts an algorithm named by the token header and never uses a shared secret. |
| NFR5.11 | Few, pinned dependencies | Only PyJWT, cryptography, httpx (key fetch) and the standard library; listed in the project file so dependency scanning sees them. |
