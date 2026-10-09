# Constraint Register

Constraints on the work described in `intent-statement` (`ideation/intent-capture/`). "Source" points to your answers in `feasibility-questions.md` (Q1 to Q10), to the request, or to the evidence list (E1 to E13) in `feasibility-assessment.md`.

## Organisational Constraints

| ID | Constraint | Source | Effect |
|----|------------|--------|--------|
| CO-1 | Files are moved into the air-gapped environment on removable drives, with no practical per-file size limit | Q1 | Splitting is driven by drive capacity, not file size |
| CO-2 | Drive sizes vary, and the smallest is under 1 GB | Q1, Q9 | Bundles must be splittable into very small pieces |
| CO-3 | A malware or content scan and an approval or review are both required before files enter | Q2 | Scan or review may reject or delay files; delivery time is partly outside the tool |
| CO-4 | The first usable version is needed within about one month, tied to the air-gapped environment going live | Q8, Q10 | Scope must be ordered and trimmed |
| CO-5 | The internet-connected computer has direct access to the open internet | Q4 | No proxy or allow-list work needed on the download side |
| CO-6 | The builder works in Python | Q7 | Candidate language is narrowed (see `feasibility-assessment.md`) |
| CO-7 | Private and gated models, datasets and Spaces, and the web app itself are out of the first version | `intent-statement` (Q8 of intent capture) | Keeps the scope to public models |

## Technical Constraints

| ID | Constraint | Source | Effect |
|----|------------|--------|--------|
| CT-1 | The tool must run on both Linux and Windows, on the internet side and inside the air-gapped environment | Q3, request | Four environments to support |
| CT-2 | The air-gapped side has no internet, so nothing can be installed from the internet there | Request (air-gapped) | The tool must be installable offline |
| CT-3 | Models are many and large, including some over 100 GB | Q5 | Download speed, disk space and splitting all matter |
| CT-4 | Use official libraries or the official command-line tool rather than scraping | Request | Narrows the data sources to what the official routes expose (E1 to E6) |
| CT-5 | The official Python library needs Python 3.10 or newer | E1 | The download host must have a suitable Python or a packaged equivalent |
| CT-6 | The older fast-transfer add-on (`hf_transfer`) is retired; the fast path is `hf_xet` | E8 | Do not build on the retired add-on |
| CT-7 | On Windows, the default cache needs Developer Mode or administrator rights for symlinks | E10 | Without them the cache duplicates files and uses more disk |
| CT-8 | Anonymous use is limited per internet address: about 500 information requests and 3,000 file requests per 5 minutes | E9 | Many models or many files per model may hit the limit unless a token is used |

## Regulatory And Legal Constraints

| ID | Constraint | Source | Effect |
|----|------------|--------|--------|
| CR-1 | No rules on which models may be brought in beyond what Hugging Face already allows | Q6 | No licence filtering is required |
| CR-2 | Each model's licence text must be kept and shown with the model | Q6 | The licence information must travel with the model (open item A4 in `raid-log.md`) |
| CR-3 | No data-residency or compliance regime has been named | Q2, Q6 (none stated) | Nothing further recorded; the approval process in CO-3 may add rules |

## Assumptions And Open Questions

- Download-side network bandwidth is unknown, so speed targets cannot be set yet [assumption]
- Whether Python or a packaged equivalent can be placed on the air-gapped computers is unknown [assumption]
