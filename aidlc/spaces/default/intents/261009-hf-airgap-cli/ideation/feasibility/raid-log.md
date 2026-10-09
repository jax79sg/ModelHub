# RAID Log

Risks, Assumptions, Issues and Dependencies for the work in `intent-statement` (`ideation/intent-capture/`). Evidence references (E1 to E13) are in `feasibility-assessment.md`; constraint references (CO, CT, CR) are in `constraint-register.md`. Likelihood and impact are my conservative judgements: High, Medium or Low.

## Risks

| ID | Risk | Likelihood | Impact | Response |
|----|------|------------|--------|----------|
| R1 | The one-month deadline (CO-4) is tight for fast downloads, splitting into small pieces, two operating systems on two sides, and offline install | Medium-High | High | Order the scope in requirements; deliver the essentials first; agree what slips |
| R2 | Splitting a model over 100 GB into pieces that fit a drive under 1 GB means hundreds of drives or swaps per model (calculation from Q5 and Q9) | High | Medium | Let the piece size be chosen per transfer; confirm in requirements that this effort is acceptable; keep a way to resume after a failed piece |
| R3 | The tool cannot be installed on the air-gapped Linux and Windows computers because they have no internet and may lack Python (CT-1, CT-2, CT-5) | Medium | High | Resolve before design: check what the air-gapped machines have; keep a packaged-executable or offline package route open (hypothesis, untested) |
| R4 | Hugging Face changes its libraries or services again, as it did when it retired the older fast-transfer add-on (CT-6, E8) | Medium | Medium | Record the library version with each bundle; avoid retired features |
| R5 | Many models or many files exceed the anonymous request limits (CT-8, E9) | Low-Medium | Medium | Allow an optional access token; rely on the library's wait-and-retry behaviour |
| R6 | The content scan or approval rejects or delays files, for example older file formats that can contain runnable code (CO-3, E4) | Medium | Medium | Include Hugging Face's own scan results in the bundle to support the approval; let users leave out certain file types |
| R7 | Pictures and links in READMEs that point to other websites break offline (E5) | High | Medium | Decide in requirements whether to fetch and rewrite them or accept the gap |
| R8 | "Same key information as huggingface.co" (`intent-statement`) cannot be fully met and is not yet measurable | High | Medium | Define the list of key information and what is excluded in requirements |
| R9 | On Windows without Developer Mode, the default cache duplicates files and uses extra disk (CT-7, E10) | Medium | Low | Offer downloading straight to a chosen folder |
| R10 | Real download speed on your network is unmeasured, so the "noticeably faster" goal may not be provable (A1) | Medium | Medium | Measure on your network early; set a numeric target in requirements |

## Assumptions

All are unconfirmed and labelled as assumptions.

- A1: Download-side bandwidth is unknown; no speed target can be set until it is measured [assumption]
- A2: The internet-connected computers can run Python 3.10 or newer, or a packaged equivalent [assumption]
- A3: The air-gapped computers can accept a packaged tool or an offline package set once approved (CO-3) [assumption]
- A4: A licence identifier in the model's settings header, or a licence file in the repository, is enough to "keep and show the licence text" (CR-2); this was not checked across models [assumption]
- A5: Hugging Face keeps anonymous reads of public models available at roughly the stated limits [assumption]
- A6: The sample results hold for models in general; only one or two samples were tested [assumption]

## Issues

None identified.

## Dependencies

- D1: Availability of huggingface.co and its content-delivery hosts during download (CO-5)
- D2: Hugging Face's official library, command-line tool and fast-transfer component (E1, E8)
- D3: The scan and approval process before files enter the air-gapped environment (CO-3)
- D4: Removable drives of varying sizes, supplied by you (CO-1, CO-2)
- D5: The future air-gapped web app, built separately and out of the first version, which will read what the tool produces (CO-7)
