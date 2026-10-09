# Intent Capture Questions

## Sources

- [desc] Initial description: "Create a CLI that will download all the necessary artifacts from huggingface for public models, this would include readme text and other metadata. The purpose of these artifacts is so they can be transfered to an air gapped env where there is a web app that reads the info and displays the information like it was  on the internet. Do review what kind of data can be retrieved, where possible avoid scraping and instead rely on official libraries or CLI.  For large files,  consider downloading over multiple connectins to reduce the time needed. Also consider the best programming lanaguage to build this CLI. Ideally, the CLI can be easily installed and executed from both linux and windows computers."
- [scope] Workflow-selected scope: `security-patch`.

## Q1. Who will use the downloaded model bundles and the web app on the air-gapped side?

Why we ask: it decides who the customer is and whose needs the success measures should reflect.

A. Just me or my own small team
B. Other teams in my organisation
C. People outside my organisation
D. Not yet defined
X. Other (please specify)

[Answer]: X. Can be anyone.

## Q2. What is the main pain today when you need a Hugging Face model in the air-gapped environment?

Why we ask: the pain we name here is the problem the whole initiative has to solve.

A. There is no way to read a model's README and details (the "model page") once you are offline
B. Getting the model files and their documents across the gap is slow, manual, or easy to get wrong
C. Both A and B
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q3. What does success look like for this first version?

Why we ask: success measures tell later stages what "done" means. Exact numbers can be pinned down in the requirements step.

A. A model's page in the air-gapped web app shows the same key information a person sees on huggingface.co
B. Large model files download noticeably faster than with a single connection
C. Both A and B
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q4. What is the trigger for doing this now?

Why we ask: it shows how urgent the work is and what it competes with.

A. An air-gapped environment is being set up or is about to be
B. The current way of getting models across is too slow or unreliable
C. A specific model is needed in the air-gapped environment soon
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q5. Who else has a stake in this work? (select all that apply)

Why we ask: the web app on the air-gapped side consumes what this tool produces, so whoever builds or runs it shapes what the tool must output.

A. I build both the download tool and the web app
B. A different person or team builds the web app and needs to agree on what the tool produces
C. A different person or team runs the transfer into the air-gapped environment
D. None identified
X. Other (please specify)

[Answer]: A, C

## Q6. Who decides scope and priority for this work?

Why we ask: so open trade-offs (for example speed against completeness) go to the right person.

A. Me alone
B. Me, with input from the web app owner
C. A manager or review group above me
D. Not identified
X. Other (please specify)

[Answer]: A

## Q7. Are there communication or reporting needs while this is built?

Why we ask: it decides whether the plan needs any updates or handoff notes beyond the work itself.

A. None needed
B. A written description of the bundle contents, handed to the web app owner
C. Regular status updates to a manager or sponsor
D. Not applicable
X. Other (please specify)

[Answer]: B

## Q8. What should this first version leave out? (select all that apply)

Why we ask: stating what is out keeps the first version small. Your request already names public models; this asks what else to leave for later.

A. Private or gated models (public models only)
B. Datasets and Spaces (models only)
C. Building or running the air-gapped web app itself
D. Updating a bundle later to pick up changes on Hugging Face
E. Not yet defined
X. Other (please specify)

[Answer]: A, B, C

## Q9. You said the users "can be anyone" (Q1). Does that include people outside your organisation?

Why we ask: the stakeholder map and the success measures differ for an internal tool and one used by outside people.

A. Yes, people outside my organisation can use the air-gapped web app
B. No, "anyone" means anyone inside my organisation
C. Not yet defined
X. Other (please specify)

[Answer]: A

## Q10. You build both the tool and the web app (Q5) and want a written description of the bundle contents (Q7). Who is that description for?

Why we ask: it decides whether the description is a lasting reference for a future reader or a note to yourself while you build the web app.

A. Me, as a reference while I build the web app later
B. The person who runs the transfer into the air-gapped environment
C. Both A and B
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Assumption Confirmation

These points are written up as open assumptions, not facts:

- No numeric target has been given for "noticeably faster" large-file downloads, so the speed goal cannot yet be measured
- How much say whoever runs the transfer has over scope or priority is unknown
- How much say the web app users have over scope or priority is unknown

A. Accept assumptions
B. Convert to follow-up questions

[Answer]: A. Accept assumptions
