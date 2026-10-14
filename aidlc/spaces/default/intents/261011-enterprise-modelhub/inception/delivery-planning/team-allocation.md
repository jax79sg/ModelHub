# Team Allocation

This file says who does each Bolt. A **Bolt** is one build pass over a piece of the work, here one unit of work taken through its four design runs. A **mob** is a group working on one thing together; here there is only one worker, so there is no Program Board (the cross-team planning view used when several teams share a plan).

## Allocation

Team formation did not run for this plan (the plan skips it), and you chose to have this session do all the work (`delivery-planning-questions.md` DPQ6 A). So every Bolt is done by the developer agent (an AI), with the human as the approver at every gate.

| Bolt | Unit | Worker | Human role |
|------|------|--------|-----------|
| B1 | U1 common | developer agent | answers design questions; approves each run |
| B2 | U3 artifactory-stand-in | developer agent | same |
| B3 | U2 catalog | developer agent | same |
| B4 | U4 artifactory-service | developer agent | same; also the person who can confirm Artifactory facts |
| B5 | U5 portal | developer agent | same |
| B6 | U6 import-cli | developer agent | same |
| B7 | U7 platform | developer agent | same; also the contact for the Keycloak, registry and logging administrators |

## Rules

- No sub-agents are used (your standing instruction); the work is done in this session, one Bolt after another (DPQ4 A).
- The human stays the only approver. A failed check, a plan approval or a verification-command choice always stops for the human.
- If more people join later, team ownership by unit can be turned on at any Construction checkpoint; the unit boundaries already allow it. Nobody has been named, so it is not planned.
