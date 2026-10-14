# Security Design: portal

How sign-in, sessions, forms and rendering are protected.

| Requirements | Design decision | How it works |
|--------------|-----------------|--------------|
| NFR5.1 | Default-deny middleware | Every route needs a session except the named open paths; a test requests every route without a session. |
| NFR5.2, NFR5.10 | Server-side sessions | A random session id in a Secure, HTTP-only, same-site cookie points to server memory holding the tokens; idle limit 8 hours; sign-out ends the Keycloak session; refresh tokens renew access tokens before expiry. |
| NFR5.3 | Code exchange with proof key via Authlib | The browser flow uses the authorization code with PKCE, a random state and a nonce; no implicit flow. |
| NFR5.4 | Form token and origin check | Each form carries a token tied to the session; the Origin or Referer must be the portal's own address; otherwise 403. |
| NFR5.5 | Role from the sign-in, rechecked by services | The session notes the administrator role; admin routes check it; the services check it again from the token on every call. |
| NFR5.6 | Existing sanitiser kept | README text goes through markdown-it-py and nh3 with the prototype's allowed list; the prototype's hostile-content tests are kept and extended. |
| NFR5.7 | Documents as data | Pictures and documents come from the Catalog and are re-served with nosniff, a restrictive content security policy, and no html or svg rendering. |
| NFR5.8 | Show-once page | The made token's value is rendered only in the response to the make request, with no-store headers, not in any address and not logged. |
| NFR5.9 | No file routes | The prototype's download and raw routes are deleted; there is no route that reads a model file. |
| NFR5.11 | Secret from a file | The sign-in client secret comes from the secret file via the shared loader. |
