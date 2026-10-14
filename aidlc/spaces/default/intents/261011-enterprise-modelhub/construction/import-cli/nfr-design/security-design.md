# Security Design: import-cli

How the token and the connection are protected.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR5.1 | Private settings file | The settings file is written with mode 600 on Linux and macOS, and in the person's own profile folder on Windows; a failure to set the permission stops login; there is no option that accepts a token. |
| NFR5.2 | Output filter | All printed and logged text, including server messages, passes through one filter that masks the token and the Authorization header; tests grep every output for the token. |
| NFR5.3 | https rule | Login refuses any address that is not https, except localhost and 127.0.0.1. |
| NFR5.4 | Certificate verification always on | The system's trusted certificates are used; there is no option to switch verification off; a certificate error is not retried. |
| NFR5.5 | Verify before send | The existing verify code runs on each bundle before any request; a tampered piece stops that model. |
| NFR5.6 | One destination | Requests go only to the configured server. |
