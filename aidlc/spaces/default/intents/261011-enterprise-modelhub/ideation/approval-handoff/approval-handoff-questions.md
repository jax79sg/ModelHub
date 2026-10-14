# Approval & Handoff Questions

Context: this is the last step of the Ideation phase. It gathers what was decided so far into an initiative brief, then asks you to approve moving on to Inception (requirements and design). Market research, team formation and rough mock-ups were not part of your approved plan, so the brief says they were not done. Because you decide scope and priority alone (intent capture Q12 and Q19), these questions are about you, not a group.

## Q1. Do you accept the intent and the scope as recorded?

Why we ask: the brief carries the intent statement, the scope document and the prioritized backlog forward as the agreed starting point for requirements and design. The main points are: the CLI imports into Artifactory with a record in PostgreSQL; the web app grows into the portal with Keycloak sign-in; the first build is import plus portal plus retention rule plus logging; the old folder's models, backup and restore come later; and the whole is designed for Docker Compose on one Linux server.

A. Yes, accept them as they are
B. Yes, but with changes (please say what)
C. Not yet; I need to think about it
X. Other (please specify)

[Answer]: A

## Q2. Have you seen the main risks and accepted how the plan responds to them?

Why we ask: the risk log has ten risks. The ones that matter most are: the upload needs a second, older Python and Hugging Face client next to the CLI (R1); the Artifactory is emulated and may behave differently from the real one (R2, R3); and the two stores can disagree after a half-finished import (R9).

A. Yes, I have seen them and accept the responses recorded
B. I have questions about some of them (please say which)
C. Not yet; I need to read the risk log first
X. Other (please specify)

[Answer]: A

## Q3. Do you have the time and resources to take the work through requirements and design?

Why we ask: you need a design within about a month (feasibility Q7). The next stages are requirements, design of the data and its interfaces, quality targets, and the container layout; each pauses for your answers.

A. Yes, I can give the time those stages need
B. Only partly; the time is limited (please say how)
C. Not yet defined
X. Other (please specify)

[Answer]: A
