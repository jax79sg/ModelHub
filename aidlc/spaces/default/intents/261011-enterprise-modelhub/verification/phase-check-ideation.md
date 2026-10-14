# Ideation To Inception Check

Checks that the Ideation documents agree with each other before the work moves on to requirements and design. Documents checked: `intent-statement`, `stakeholder-map` (`ideation/intent-capture/`), `feasibility-assessment`, `constraint-register`, `raid-log` (`ideation/feasibility/`), `scope-document`, `intent-backlog` (`ideation/scope-definition/`), and `initiative-brief`, `decision-log` (`ideation/approval-handoff/`).

## Verdict

**Pass, with four warnings.** No contradiction was found between the intent, the scope and the backlog. Every part in scope has feasibility backing, with the gaps noted below.

## Intent To Scope To Backlog

| Intent element | In scope document | In backlog |
|----------------|-------------------|------------|
| CLI injects data into the enterprise store instead of a folder | Model import | B3 |
| Model information in a database | Metadata database | B1 |
| Web app made enterprise level | Portal | B4 |
| Everything hosted in Docker containers | Container hosting | B5 |
| Build against a system that is not available | Artifactory stand-in | B2 |
| Traceability of who imported what | Metadata database (import trail) | B1, B3 |
| Licence kept and shown; retention period | Retention rule; database holds licences | B6, B1 |
| Old folder models imported | Import of the old folder store (later) | B8 |

Coverage: 8 of 8 intent elements appear in the scope document and the backlog (100%). Every backlog item B1 to B12 traces to a scope-document entry or an explicit exclusion.

## Scope Items With Feasibility Backing

| Scope item | Backed by | Strength |
|------------|-----------|----------|
| Model import | `feasibility-assessment` (documented upload and download), CT-8, CT-12 | Medium-High |
| Metadata database | `feasibility-assessment` (Artifactory holds only a generated revision hash), CT-3 | High |
| Portal and Keycloak sign-in | CT-4, intent capture Q16 and Q21 | High |
| Container hosting | CT-1, CT-5, CT-6 | High |
| Artifactory stand-in | CT-14, R2, R3 | Medium |
| Retention rule | CR-2 | Low: the period has no length |
| Central logging and monitoring | CT-6 | High |
| Import of the old folder store | D30 in the decision log | Medium |

## Warnings

1. **The retention period has no length** (CR-2, raid-log A5). The rule can be designed as a setting, but cannot be tested until a value exists.
2. **The store size is undefined** (feasibility Q5). Sizing uses the earlier planning figure until a number is given.
3. **The real Artifactory is unavailable and may stay so** (D31). The most uncertain part of the plan rests on the emulation.
4. **The sign-in roles are not defined.** Keycloak is chosen, but which roles the portal needs, and who gets them, has not been asked. This is for requirements.

## Consistency Between Phases

- Scope Definition SQ1 B leaves out the old-folder import while Feasibility Q12 asked for it; resolved by SQ8 A (later, designed now). No open contradiction remains.
- The approved plan stops at the architecture; SQ4 A makes the design cover the whole system. The first build is marked in the backlog and is not part of this workflow.

## Human Approval

- [ ] The person approves moving from Ideation to Inception (recorded at the Approval & Handoff gate)
