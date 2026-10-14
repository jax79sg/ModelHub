# Logical Components: portal

One container; its logical parts follow.

| Component | Role | Failure domain | Blast radius if it fails |
|-----------|------|----------------|--------------------------|
| Sign-in handler | Login, callback and logout with Keycloak | Portal container, Keycloak | New sign-ins fail; signed-in people continue while tokens are valid |
| Session store | Holds sessions and tokens in memory | Portal container | Everyone signed out on a restart |
| Page renderers | Lists, model pages, trail, account and admin screens | Portal container | The pages of that kind |
| Service clients | Calls to the Catalog and the retention service | Portal container, those services | Pages that need them say so plainly |
| Safe renderer | Sanitises README text; serves pictures as data | Portal container | Cards; lists continue |
| Static files | Styles, scripts, fonts | Portal container | Look only |
