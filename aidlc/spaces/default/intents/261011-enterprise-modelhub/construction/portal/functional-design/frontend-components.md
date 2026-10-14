# Frontend Components: portal

The portal is server-rendered, as the prototype is: each page is built on the server from templates and sent as HTML, with a small amount of optional script for the theme and for copy buttons. Everything is served by the portal itself (no outside files). State lives on the server (the session) or in the address; the only browser state is the theme choice. This file lists the page parts, what each is given, what each does and how forms are checked. Behaviour and rules are in `functional-spec.md` and `rules.md`.

## Page Layout

| Part | Shows | Given | Notes |
|------|-------|-------|-------|
| Header | Product name, models link, trail link, token page link, administrator links (administrators only), the person's name, theme switch, sign-out | session (name, is_admin) | BR1.4, BR1.17 |
| Notice bar | Plain messages: service down, refused, saved | a message code | BR1.11 |
| Footer | Version of the portal | build version | |

## Models List Page

| Component | Props (given) | Interaction | Validation |
|-----------|---------------|-------------|------------|
| Filter panel | facets with counts (task, library, licence, language, parameter band, imported by) | choosing a value adds it to the address and reloads | unknown values are ignored with a notice |
| Date range | imported from, imported to | two date fields | from not after to; a bad date shows a notice |
| Search box | words | submit | at most 200 characters, 10 words |
| Show removed | a tick | reloads | |
| Sort menu | six choices | reloads | |
| Model row | id, task, library, licence, downloads, likes, imported at and by, state | click opens the model | null counts show 'unknown' |
| Pager | page, total | previous, next | 30 per page |

## Model Page

| Component | Props | Interaction |
|-----------|-------|-------------|
| Title bar | model id, state badge, licence | |
| Removed banner | removed date and name | shown for a removed version only |
| Revision menu | branches, tags, captured commits | choosing one opens that revision |
| Card | README as safe HTML with stored pictures | |
| Facts | tags, counts with capture date, parameter counts, created, modified | null as 'unknown' |
| Fetch instructions | repository address, model id, commit, three snippets | copy buttons; snippets use <your-token> |
| Files table | path, size, SHA-256, scan result, 'not in store' | link to the file page |
| Trail panel | this model's trail rows | link to the full trail |

## Token Page

| Component | Props | Interaction | Validation |
|-----------|-------|-------------|------------|
| Make form | name | submit | 1 to 60 characters; form token |
| Shown-once box | value | copy button | the page is not cached and the value is not in the address |
| Token table | name, first characters, created, expires, last used, revoked | revoke button with confirmation | |
| All tokens switch | administrators only | reloads | |

## Retention Page (administrators change; everyone reads the period)

| Component | Props | Interaction | Validation |
|-----------|-------|-------------|------------|
| Period box | days, changed by and when | edit form (administrators) | whole number 1 to 3650 |
| Due table | model, commit, imported at and by, size, last keep | Keep and Remove buttons per row | |
| Confirm page | model, commit, warning text | Confirm, Cancel | form token |
| Result page | outcome and reason | Try again where allowed | |
| Decisions table | model, commit, decision, who, when, outcome | | |

## Trusted Keys Page (administrators)

| Component | Props | Interaction | Validation |
|-----------|-------|-------------|------------|
| Key table | fingerprint, label, added by and when, status | Stop trusting with confirmation | |
| Add form | public key file, label, typed fingerprint | submit | label 1 to 80 characters; the service checks the fingerprint and the page shows a mismatch plainly |

## Trail Page

| Component | Props | Interaction |
|-----------|-------|-------------|
| Filters | model, person | reload |
| Trail table | time, who, what (imported, skipped, repaired, kept, removed), model, commit, outcome | click opens the model |
| Pager | page, total | 30 per page |

## Forms, Tokens And Errors

- Every form that changes something carries a token tied to the session and is refused if the page's origin differs. [BR1.3]
- Error pages: sign-in needed (redirect), not allowed (administrator needed), not found, service unreachable, and a general problem page that shows the request id and no technical detail. [BR1.1, BR1.4, BR1.11]
- Accessibility and look follow the prototype: keyboard-reachable controls, visible focus, labels on every field, colour never the only carrier of meaning, light and dark themes. [BR1.17]
