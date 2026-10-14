# External Dependency Map

An external dependency is something outside this plan and this session that a Bolt needs: a fact, an approval or a service. A **Bolt** is one build pass over a piece of the work, here one unit taken through its four design runs. You chose to record each one, carry on with a stated assumption and confirm when the owner answers (`delivery-planning-questions.md` DPQ5 A). The owner for every item is you or the people you name at the gate; the table says which role.

| ID | Dependency | Needed by | Owner (role) | Expected wait | Assumption used meanwhile | If it slips or the answer differs |
|----|------------|-----------|--------------|---------------|---------------------------|-----------------------------------|
| X1 | How Artifactory's Machine Learning layout lists and deletes files in a model repository (the exact file paths are not on the JFrog pages read) | B4 (gateway, retention), B2 (stand-in) | Whoever runs the Artifactory | Unknown; needs access to a real Artifactory | The gateway lists to discover paths; the stand-in imitates a plausible layout and records it as an assumption | Only the gateway and stand-in change; the rest of B4 and all other units do not |
| X2 | The Artifactory version in use supports Hugging Face repositories (7.77.1 or later), the Machine Learning layout, and `jf hf` | B4 | Whoever runs the Artifactory | Quick if asked | The version meets the minimum; versions beyond huggingface_hub 1.19.0 are avoided | If older, hosting for models cannot work as designed; this would reopen the requirements |
| X3 | Keycloak: two client ids (`modelhub`, `modelhub-artifactory-service`) and the realm role `modelhub-admin` accepted and created | B1 (token check), B5 | Keycloak administrators | Days to weeks (approval) | The names in contract C6 | Names are configuration; changing them touches C6 and B1 only |
| X4 | Container registry: where images are pushed, what it allows, the path to the server | B7 | Registry owners | Days | A path of the form named in B7's design | Only B7 changes |
| X5 | Central logging: what format and endpoint it takes from container standard output | B7, B1 (log line shape) | Logging owners | Days | JSON lines on standard output, picked up by the host (contract C7) | B1's log shape and B7 change |
| X6 | Owner's answers on personal-token defaults (import only, 90 days, shown once, hash only) | B3, B5, B6 | The service owner (you) | Quick | The defaults in contract C3 | B3, B5 and B6 adjust a setting and a screen |
| X7 | Server: one Linux host with Docker and enough disk to receive bundle pieces (over 100 GB per package, each piece removed once unpacked) | B4, B7 | Infrastructure owners | Days | Disk is sized in B7's design | B7 sets a minimum; a smaller disk limits the largest package |

## Bolt View

| Bolt | Blocked or shaped by |
|------|----------------------|
| B1 common | X3, X5 |
| B2 artifactory-stand-in | X1 |
| B3 catalog | X6 |
| B4 artifactory-service | X1, X2, X7 |
| B5 portal | X3, X6 |
| B6 import-cli | X6 |
| B7 platform | X4, X5, X7 |

## Rules

- No Bolt waits for an answer; each carries the assumption in its design and a line in its open-questions section.
- When an owner answers differently from the assumption, the affected Bolt's documents are reopened through the usual change request at that Bolt's approval, and the change is listed in its "Effects On Approved Documents" section.
- Items X1 and X2 are the ones that could change more than one Bolt. Ask for them first.
