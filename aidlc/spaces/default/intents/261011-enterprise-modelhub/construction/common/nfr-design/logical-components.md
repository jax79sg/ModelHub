# Logical Components: common

The library is code built into the images of the three server units, not a program. Its logical parts are listed with where a failure would show.

| Component | Role | Failure domain | Blast radius if it fails |
|-----------|------|----------------|--------------------------|
| Token verifier | Checks a token and builds the verdict | Each service process | The service using it; every request is refused if it is broken |
| Key set holder | Keeps and refreshes the signing keys | Each service process | Token checks for that service; stays up on Keycloak failure with the keys held |
| Request guard | Applies default-deny and the admin check | Each service process | The service using it |
| Secrets loader | Reads secret files once | Start-up of each service | Start-up only; a failure stops the service by design |
| Settings loader | Reads and types environment settings | Start-up of each service | Start-up only |
| Log formatter | Writes redacted JSON lines | Each service process | Logging for that service; never the request path |
| Health helper | Serves /healthz and /readyz from registered checks | Each service process | Health answers of that service |
