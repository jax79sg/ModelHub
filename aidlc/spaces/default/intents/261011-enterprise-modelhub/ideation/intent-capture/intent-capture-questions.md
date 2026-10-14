# Intent Capture Questions

## Sources

- [desc] Initial description: "We now have a working CLI that downloads the artifacts, and a prototype web that reads the artifacts and display the content. Now let's make them enterprise level. For the CLI, it should not just read from a folder on the airgap side, it should also inject the data into the enterprise modelhub. We have Artifactory with limited hfapi installed, you can refer to the specs here https://docs.jfrog.com/artifactory/docs/use-hugging-face-with-jfrog-cli. meta data should also be installed in a database. Now, based on the artifacts we will use, design an architecture to host all the artifacts, metadata, models and whatever we downloaded using CLI. The architecture should be hosted via docker containers."
- [scope] Workflow-selected scope: `classic`.

## Q1. What is the main problem with the way the models are held and used today?

Why we ask: the problem named here is what the whole architecture has to solve. Today the tool unpacks a model into a plain folder on one air-gapped computer, and the prototype web app reads that folder.

A. Models sit in a folder on one computer, so people elsewhere in the organisation cannot find, fetch or reuse them
B. There is no controlled, auditable record of which model versions the organisation has imported and approved
C. Both A and B
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q2. Who will use the enterprise ModelHub? (select all that apply)

Why we ask: users decide what the web app and the stored information must offer, and who needs sign-in and permissions.

A. Machine-learning engineers and data scientists who fetch models to work with
B. The platform or infrastructure team who run Artifactory and the containers
C. Security and compliance reviewers who approve what is brought in
D. Automated systems (training or serving pipelines) that pull models through an interface
E. Not yet defined
X. Other (please specify)

[Answer]: A, B, C, D

## Q3. What does success look like for this first version? (select all that apply)

Why we ask: success measures tell later stages what "done" means. Exact numbers can be pinned down in the requirements step.

A. A model carried in on a drive can be found in the web app and downloaded through Artifactory soon after the import finishes
B. Every imported model can be traced: who imported it, when, from which bundle, and which signing key vouched for it
C. Standard Hugging Face tooling (for example the `huggingface_hub` library or the JFrog CLI) can fetch a model from the enterprise store
D. Not yet defined
X. Other (please specify)

[Answer]: A, B, C

## Q4. What is the trigger for doing this now?

Why we ask: the reason for acting now shows how much time pressure and how much formality the design needs.

A. The prototype worked and the organisation now wants to rely on it
B. An audit, security or compliance requirement
C. More teams are asking for models in the air-gapped environment
D. Not yet defined
X. Other (please specify)

[Answer]: A, B, C

## Q5. What does "limited Hugging Face API" mean on your Artifactory?

Why we ask: this is a fact about your own system that decides what the design can depend on. The linked JFrog page describes uploading and downloading Hugging Face models with the JFrog CLI; the design must not assume anything your installation lacks.

A. We can store a model's files in a Hugging Face-type repository and download them with the JFrog CLI or the `huggingface_hub` library, but there is no model page, search or metadata
B. Only plain file storage works; the Hugging Face repository type is not available
C. I am not sure yet and will check with the Artifactory administrators
D. Not yet defined
X. Other (please specify)

[Answer]: X. It doesn't include advanced hf api calls. This was documented on artifactory website.

## Q6. How should the CLI use Artifactory and the database when it imports a model?

Why we ask: today the CLI's last step on the air-gapped side writes a folder. This decides whether the folder stays.

A. After it has verified a bundle, the CLI uploads the files to Artifactory and records the model information in the database, replacing the folder
B. The CLI does that and also keeps writing the folder, so the prototype web app and the new parts can run side by side for a while
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q7. Which database should hold the model information?

Why we ask: the model information (descriptions, tags, file lists, scan results, who imported what) is to be stored in a database. The choice affects the container design and who must operate it.

A. PostgreSQL, run as a container that is part of this architecture
B. A database the organisation already runs and that we must use (please name it)
C. No preference; choose what fits
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. What should the web app become?

Why we ask: the prototype is a read-only viewer with no sign-in. "Enterprise level" can mean much more or only a little more.

A. The organisation's portal: it reads the database, links to Artifactory for downloads, and uses the organisation's single sign-on
B. It stays a read-only viewer, now reading from the database and Artifactory, with no sign-in beyond the network
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q9. What does "hosted via docker containers" cover?

Why we ask: your Artifactory already exists, so the architecture could leave it as it is or include it.

A. Only the new parts (web app, interface to the data, database, import service); the existing Artifactory stays where it is, outside these containers
B. Everything, including an Artifactory run as a container
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q10. What will run the containers?

Why we ask: it decides whether the design describes a simple file for one machine or something that spreads across many.

A. Docker Compose on one server
B. Kubernetes or another container platform the organisation already operates
C. Not decided; the architecture should work for either and say what changes
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q11. Who else has a stake in this work? (select all that apply)

Why we ask: the stakeholder map lists each group and what it cares about, so later stages know whose needs to check.

A. You (owner of the CLI and the web app)
B. The Artifactory administrators
C. The security and compliance team
D. The teams that will fetch and use the models
E. Auditors
X. Other (please specify)

[Answer]: A, B, C, D

## Q12. Who decides scope and priority for this work?

Why we ask: the person named here approves the plan and settles trade-offs when requirements pull in different directions.

A. You alone
B. You, after agreeing with the Artifactory administrators
C. A group or committee (please name it)
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q13. Are there communication or reporting needs while this is designed?

Why we ask: it shows whether anyone besides you needs updates and in what form.

A. No, the decision record in this project is enough
B. Yes, a short summary at the end of each stage for people outside the project
C. Yes, a regular status update to a named group (please name it and how often)
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q14. What should this first version leave out? (select all that apply)

Why we ask: the workflow scope is already chosen (a design-focused plan, with no code yet). This question is only about the product: what the first enterprise version should not do.

A. Searching inside model files or running the models
B. Importing from anywhere except the bundles the CLI already makes (for example directly from huggingface.co on the air-gapped side)
C. Private or gated models
D. Automatic updates of models already imported
E. Nothing in particular
X. Other (please specify)

[Answer]: C, D

## Assumption Confirmation

The artifacts carry these assumptions. Accepting them keeps each labelled as an assumption; it does not turn it into a fact.

- The version of the Artifactory, and whether a Hugging Face repository is already set up on it, are not known; no instance is available to check.
- JFrog's documentation lists, for Hugging Face repositories, only `jf hf download` and `jf hf upload` as supported commands, says Hugging Face client versions after 1.19.0 are not supported, and says Spaces are not supported. This is the assistant's reading of the pages, which the user has accepted only as a starting point.

A. Accept assumptions
B. Convert to follow-up questions

[Answer]: A. Accept assumptions

## Q15. How soon after an import finishes should a model be findable and downloadable?

Why we ask: you said success is that a model can be found in the web app and downloaded through Artifactory "soon after the import finishes" (Q3). A number turns that into something a test can check.

A. Within a few minutes
B. Within an hour
C. Within a working day
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q16. Which single sign-on system does the organisation use for the web app?

Why we ask: you chose to make the web app the organisation's portal using single sign-on (Q8). Which system it is decides what the web app and its database must connect to.

A. LDAP or Active Directory
B. An OpenID Connect or SAML provider (for example Keycloak, Okta or Azure AD)
C. The same sign-in as the Artifactory
D. Not yet defined, or I will check
X. Other (please specify)

[Answer]: B

## Q17. Which Artifactory version do you have, and is a Hugging Face repository already set up on it?

Why we ask: JFrog documents Hugging Face repositories from Artifactory 7.77.1 and datasets from 7.90.x, so the version decides what the import can rely on.

A. 7.77.1 or newer, and a Hugging Face repository already exists
B. 7.77.1 or newer, but no Hugging Face repository exists yet
C. Older than 7.77.1
D. I do not know yet; I will check with the Artifactory administrators
X. Other (please specify)

[Answer]: X. I don't have it ready for you. You might need to somehow emulate it.

## Q18. JFrog's documentation says only downloading and uploading Hugging Face models is supported, with `huggingface_hub` client versions up to 1.19.0. Is that enough for the "standard tooling can fetch a model" goal (Q3)?

Why we ask: the CLI today uses a newer `huggingface_hub` (2.2 or later) on the online side. Anything that talks to Artifactory must use a supported version, so the design needs to know whether "fetch with the standard download command" is the whole goal.

A. Yes, the standard download command (and upload for the CLI) is all that is needed; listing, search and model pages come from the database and web app
B. No, other Hugging Face calls (for example listing files or reading model information through the Hugging Face interface) must also work against Artifactory
C. Not sure; decide in the design stage
X. Other (please specify)

[Answer]: A

## Q19. You said the Artifactory administrators, the security and compliance team and the teams using the models are stakeholders (Q11) and that you alone decide scope (Q12). How should their needs count?

Why we ask: it decides whether their concerns are requirements the design must satisfy or advice you may take or leave.

A. Their concerns are requirements; the design must satisfy them
B. Their input is advice only; you decide what to do with it
C. Not yet defined
X. Other (please specify)

[Answer]: B

## Q20. What do the Artifactory administrators need from this work?

Why we ask: they run the system the CLI will upload into, and the stakeholder map does not yet say what they need.

A. Only a repository and a service account for the CLI to use
B. To review and approve how the CLI and the web app use Artifactory (permissions, naming, load)
C. Specific rules the integration must follow (for example repository layout, naming or retention); I will list them
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q21. Which OpenID Connect or SAML provider does the organisation use?

Why we ask: you chose an OpenID Connect or SAML provider for single sign-on (Q16). The provider decides how the web app signs people in and how roles reach it.

A. Keycloak
B. Okta
C. Microsoft Entra ID (Azure AD)
D. Not yet defined, or I will check
X. Other (please specify)

[Answer]: A

## Q22. No Artifactory is available to build or test against (Q17). What should the emulation stand in for?

Why we ask: it sets how much of Artifactory the emulation must imitate, and so how much work and risk it carries.

A. Only the Hugging Face download and upload that `jf hf` and `huggingface_hub` use
B. That, plus the other Artifactory calls the CLI and web app would need (for example listing a repository or reading file checksums)
C. Not sure; decide in the design stage
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q23. Should the design treat JFrog's documented behaviour as the contract the emulation must match?

Why we ask: JFrog's documentation says only `jf hf download` and `jf hf upload` are supported, `huggingface_hub` versions after 1.19.0 are not, and Spaces are not. That is my reading of their pages, not something you have confirmed.

A. Yes, JFrog's documentation is the contract; anything it does not describe is not available
B. Partly: use it as a starting point, and I will correct it when I can check the real Artifactory
C. Not sure; decide in the design stage
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q24. Does the emulated Artifactory only stand in while building and testing, or does it ship as part of what is delivered?

Why we ask: it decides whether the container list in the architecture includes the emulation.

A. Stand-in for building and testing only; it is not delivered
B. It is delivered as an optional container for places that have no Artifactory
C. Not sure; decide in the design stage
D. Not yet defined
X. Other (please specify)

[Answer]: A
