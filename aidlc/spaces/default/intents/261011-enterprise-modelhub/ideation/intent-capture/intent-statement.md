# Intent Statement

## Problem Statement

- The CLI downloads Hugging Face model artifacts and, on the air-gapped side, the prototype web app reads them from a folder. [desc]
- Models held that way sit in a folder on one computer, so people elsewhere in the organisation cannot find, fetch or reuse them. [Q1]
- There is no controlled, auditable record of which model versions the organisation has imported and approved. [Q1]
- The organisation wants the CLI to inject the data into the enterprise ModelHub instead of only reading a folder, the model information to be held in a database, and an architecture designed to host all the artifacts, metadata, models and everything the CLI downloads, in Docker containers. [desc]

## Target Customer

- The users are machine-learning engineers and data scientists, the platform team, security and compliance reviewers, and automated systems such as training or serving pipelines. [Q2]
- Security and compliance reviewers approve what is brought in; the platform team runs Artifactory and the containers; engineers and pipelines fetch models. [Q2]

## Success Metrics

- A model carried in on a drive can be found in the web app and downloaded through Artifactory within an hour of the import finishing. [Q3] [Q15]
- Every imported model can be traced: who imported it, when, from which bundle, and which signing key vouched for it. [Q3]
- Standard Hugging Face tooling (the `huggingface_hub` library or the JFrog CLI) can fetch a model from the enterprise store. The standard download command (and upload, for the CLI) is all that is needed, because listing, search and model pages come from the database and the web app. [Q3] [Q18]

## Initiative Trigger

- The prototype worked and the organisation now wants to rely on it. [Q4]
- An audit, security or compliance requirement. [Q4]
- More teams are asking for models in the air-gapped environment. [Q4]

## Initial Scope Signal

- Workflow-selected scope: `classic` (workflow-selected). [scope]
- User-confirmed, in the first version: after the CLI has verified a bundle it uploads the files to Artifactory and records the model information in the database, replacing the folder. [Q6]
- User-confirmed, in the first version: the database is PostgreSQL, run as a container that is part of the architecture. [Q7]
- User-confirmed, in the first version: the web app becomes the organisation's portal. It reads the database, links to Artifactory for downloads, and uses the organisation's single sign-on through Keycloak. [Q8] [Q16] [Q21]
- User-confirmed, in the first version: only the new parts run in Docker containers (web app, interface to the data, database, import service); the existing Artifactory stays outside them. Docker Compose on one server runs the containers. [Q9] [Q10]
- User-confirmed constraint: the Artifactory has a limited Hugging Face API that does not include advanced Hugging Face API calls; this is documented on the Artifactory website. [Q5]
- User-confirmed constraint: no Artifactory is available now to build or test against, so it has to be emulated. [Q17]
- User-confirmed: the emulation stands in for the Hugging Face download and upload that `jf hf` and `huggingface_hub` use, plus the other Artifactory calls the CLI and web app would need (for example listing a repository or reading file checksums). It is a stand-in for building and testing only and is not delivered. [Q22] [Q24]
- User-confirmed: JFrog's documented behaviour is the starting point for what the emulation must match, to be corrected when the real Artifactory can be checked. [Q23]
- User-confirmed product boundary, left out of the first version: private or gated models, and automatic updates of models already imported. [Q14]

## Assumptions & Open Questions

- The version of the Artifactory, and whether a Hugging Face repository is already set up on it, are not known; no instance is available to check. [assumption]
- JFrog's documentation lists, for Hugging Face repositories, only `jf hf download` and `jf hf upload` as supported commands, says Hugging Face client versions after 1.19.0 are not supported, and says Spaces are not supported. This is the assistant's reading of the pages, which the user has accepted only as a starting point. [assumption] [Q23]
