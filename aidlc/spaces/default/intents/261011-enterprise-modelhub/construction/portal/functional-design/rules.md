# Rules: portal

The decisions the portal makes. A UI unit does not owe a rules file; this one is written because the portal has real rules (who sees what, how it fails, what it never does) and the traceability check ties requirements to rule IDs. Sources are requirement, contract and decision IDs and the answers in `functional-design-questions.md` (FDQ).

```yaml
unit: portal
rules:
  - id: BR1.1
    statement: Every page needs a signed-in person, except the sign-in steps, the health paths and the static files.
    category: authorization
    applies_to: [PortalSession]
    trigger: any request
    logic: "IF the request has no valid session THEN redirect to the Keycloak sign-in (the standard browser redirect flow) and show nothing about any model. Open paths: /healthz, /readyz, the sign-in callback, the sign-out, and the static files (styles, scripts, fonts, icons) that carry no model data. Every signed-in person may browse and fetch; there are no other roles for browsing."
    violation: redirect to sign-in
    source: [FR3.1, FR4.1, AC3.1, FDQ1 A]
  - id: BR1.2
    statement: The portal's server holds the person's tokens and gives the browser only a session cookie.
    category: policy
    applies_to: [PortalSession]
    trigger: sign-in; each request; sign-out
    logic: "After the sign-in callback, the server keeps the tokens in memory against a random session id and sets a cookie that is Secure, HTTP-only and same-site. A session ends after 8 idle hours (setting), at sign-out (which also ends the Keycloak session), or when the tokens can no longer be refreshed. The portal calls the Catalog and the retention service with the person's access token and refreshes it with the refresh token before it expires. A restart of the portal ends all sessions."
    violation: redirect to sign-in
    source: [FR3.1, FR3.8, NFR5, FDQ1 A, FDQ2 A]
  - id: BR1.3
    statement: Every request that changes something is checked against forged requests.
    category: validation
    applies_to: [PortalSession]
    trigger: any POST
    logic: "Every form carries a token tied to the session, and the request's Origin or Referer must be the portal's own address. A request that fails either check is refused with 403 and changes nothing."
    violation: 403
    source: [NFR5, corner checklist: forged request]
  - id: BR1.4
    statement: Administrator screens are shown, and their actions accepted, only for a person with the administrator role.
    category: authorization
    applies_to: [PortalSession]
    trigger: any request under /admin or any retention, setting or key action
    logic: "The session records whether the sign-in token holds modelhub-admin. IF not THEN refuse with a page saying the action needs an administrator (403) and change nothing; links to these screens are not shown. The services check the role again, so a changed session cannot give rights."
    violation: 403 page
    source: [FR4.2, FR4.3, AC4.1]
  - id: BR1.5
    statement: The models list asks the Catalog for exactly what the person chose, and shows what it answers.
    category: policy
    applies_to: [PortalSession]
    trigger: GET /models
    logic: "Pass these choices to the Catalog: task, library, licence, language, parameter-size band, imported by, imported from and to, show removed, search words, sort and page. 30 per page. Show the counts per value as filters. An empty answer says 'no models match'; a Catalog refusal of a value (invalid_query) says so in plain words and shows the unfiltered page. The portal reads nothing but the Catalog."
    violation: message shown
    source: [FR3.2, FR3.3, FR3.4, FR3.5, AC3.2, AC3.3]
  - id: BR1.6
    statement: A model's page shows what the Catalog stored and says plainly what is missing.
    category: policy
    applies_to: [PortalSession]
    trigger: GET a model or version page
    logic: "Show the card fields, tags, counts with their capture date, files, commit history, branches and tags, and the README with its stored pictures. A value that is null is shown as 'unknown' (never 0). A null licence shows 'no licence given'. No README shows 'no README stored'. A file that was listed but never downloaded is marked 'not in store'. A picture that could not be fetched shows a plain placeholder. A revision menu offers the branches, tags and captured commits."
    violation: not applicable
    source: [FR3.3, FR2.4, FR2.7, FR2.8, AC2.2]
  - id: BR1.7
    statement: A removed version still has a page, with a clear banner, and is hidden from the list unless asked for.
    category: policy
    applies_to: [PortalSession]
    trigger: GET a removed version; GET /models
    logic: "A removed version's page shows its card fields, file list marked removed, the trail including the removal decision, and a banner 'this version was removed on <date> by <name>; the README is no longer stored'. The models list leaves removed-only models out unless 'show removed' is ticked."
    violation: not applicable
    source: [FR5.5, FDQ3 A]
  - id: BR1.8
    statement: Each model page shows how to fetch the model from Artifactory, with no secret in it.
    category: policy
    applies_to: [PortalSession]
    trigger: GET a model or version page
    logic: "Show the Artifactory repository address, the model id and the commit, a link to Artifactory, and three copy-ready snippets: the JFrog command jf hf download, a Python huggingface_hub call with the endpoint set to the Artifactory address, and the endpoint setting for tools that read HF_ENDPOINT. The address and repository key are portal settings (ARTIFACTORY_URL, HF_REPO_KEY). Snippets use the placeholder <your-token> and never a real token."
    violation: not applicable
    source: [FR3.6, AC3.4, FDQ4 A]
  - id: BR1.9
    statement: The portal never serves a model file.
    category: constraint
    applies_to: [PortalSession]
    trigger: file pages
    logic: "The prototype's download and raw routes are removed. A file's page shows its size, SHA-256, type, safety-scan result and 'not in store' status from the Catalog's record, and the fetch snippets; it shows no file content and offers no file download."
    violation: not applicable
    source: [FR3.6, NFR5d]
  - id: BR1.10
    statement: The safe rendering of the prototype is kept.
    category: constraint
    applies_to: [PortalSession]
    trigger: any page
    logic: "Model-card text is turned into safe HTML by the existing sanitiser; no script or style from the card runs; nothing is requested from outside the organisation (no CDN, remote font, remote avatar or remote picture); pictures come from the Catalog's stored documents and are served as data with nosniff, a restrictive content security policy and no rendering of html or svg; the security headers of the prototype stay."
    violation: not applicable
    source: [FR3.7]
  - id: BR1.11
    statement: When a service is down the portal says so plainly and shows no stale data.
    category: policy
    applies_to: [PortalSession]
    trigger: a call to the Catalog, retention service or Keycloak fails
    logic: "IF the Catalog cannot be reached or answers with a server error THEN the page says 'the model database cannot be reached' with a retry link and shows no model data (no cache). IF the retention service cannot be reached the admin screens say so. IF Keycloak cannot be reached, new sign-ins show a message, and signed-in people continue while their access token is valid; when it expires and cannot be refreshed they are asked to sign in again."
    violation: message shown
    source: [FR3.8, AC3.5]
  - id: BR1.12
    statement: A person can make, see and revoke personal tokens for the CLI, and the value is shown once.
    category: policy
    applies_to: [PortalSession]
    trigger: the token page
    logic: "Make: a name of 1 to 60 characters posted to the Catalog; the answer page shows the value once, with no-store cache headers, never in a link, and tells the person to copy it now. List: the person's own tokens with name, first characters, created, expires, last used and revoked; an administrator can switch to all tokens. Revoke: asks for confirmation, then revokes at once. The value is never logged or kept by the portal."
    violation: not applicable
    source: [FR4.4, FR4.6, AC4.3]
  - id: BR1.13
    statement: Retention actions are taken one version at a time, with a confirmation and a clear result.
    category: policy
    applies_to: [PortalSession]
    trigger: the retention screens
    logic: "Everyone signed in can read the retention period. Administrators can change it, see the versions past it, and decide keep or remove for one version. Remove first shows a confirmation page: 'Remove <model> <commit>? This deletes its files from Artifactory and cannot be undone.' The result page says done, failed with the reason (and the version stays listed), or files deleted but not marked, with a try-again button. There is no bulk action."
    violation: 403 for non-administrators
    source: [FR5.3, FR5.4, FR5.6, AC5.1, AC5.2, FDQ5 A]
  - id: BR1.14
    statement: Administrators manage trusted signing keys by typing back the fingerprint.
    category: policy
    applies_to: [PortalSession]
    trigger: the trusted keys screen
    logic: "Administrators see the keys (fingerprint, label, added by, when, status). Adding takes the public key file, a label and the fingerprint the administrator has confirmed; a mismatch is shown plainly and nothing is added. Stopping trust asks for confirmation and says that imports already done stay."
    violation: 403 or message
    source: [FR1.14, AC1.10]
  - id: BR1.15
    statement: The trail view joins import records and retention decisions, newest first.
    category: policy
    applies_to: [PortalSession]
    trigger: the trail screens
    logic: "Merge the Catalog's import records with the retention service's decisions into one list ordered by time, newest first, filterable by model and by person, 30 per page. Each row says who, what and when."
    violation: not applicable
    source: [FR3.4, FR5.7, ADR-007]
  - id: BR1.16
    statement: Logs name the person and the request, never a token or a cookie.
    category: policy
    applies_to: [PortalSession]
    trigger: any request
    logic: "Uses the shared logging of the common library: the person's user name and the request id appear; tokens, cookies, form tokens and token values are redacted."
    violation: not applicable
    source: [NFR5b, FR6.5]
  - id: BR1.17
    statement: The dark and light themes and the look of the prototype are kept without external files.
    category: policy
    applies_to: [PortalSession]
    trigger: any page
    logic: "Styles, scripts and fonts are served by the portal itself; the theme choice is kept in the person's browser; nothing is fetched from outside."
    violation: not applicable
    source: [FR3.3, FR3.7]
```

## Rules Summary

| ID | Rule | Category |
|----|------|----------|
| BR1.1 | Sign-in needed everywhere except open paths | authorization |
| BR1.2 | Server holds tokens; cookie only | policy |
| BR1.3 | Forged-request check | validation |
| BR1.4 | Administrator screens | authorization |
| BR1.5 | List asks the Catalog | policy |
| BR1.6 | Model page and what is missing | policy |
| BR1.7 | Removed versions | policy |
| BR1.8 | Fetch instructions | policy |
| BR1.9 | No model file served | constraint |
| BR1.10 | Safe rendering | constraint |
| BR1.11 | Service down messages | policy |
| BR1.12 | Personal tokens page | policy |
| BR1.13 | Retention screens | policy |
| BR1.14 | Trusted keys screen | policy |
| BR1.15 | Trail view | policy |
| BR1.16 | Logging | policy |
| BR1.17 | Themes and no external files | policy |
