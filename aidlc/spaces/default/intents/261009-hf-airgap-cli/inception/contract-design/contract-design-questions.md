# Contract Design Questions

A contract here is a formal agreement about something that crosses a boundary. This work has three boundaries, all owned by you (feasibility Q6 and the intent's Q6):

- **The bundle**: what the download side produces and the air-gapped side reads (the pieces and the manifest, `requirements.md` FR6 and FR7).
- **The rebuilt model folder**: what the air-gapped side leaves on disk for your web app to read (FR7.2). The web app is built separately and later (out of scope).
- **The command line**: the commands, their options, and their exit status (FR8, FR9).

The earlier steps settle what is kept per model (`requirements.md` FR3) and that every item is stored as Hugging Face returned it (FR3.5). These questions cover what they do not.

## Q1. How will your web app get its data from the rebuilt model folder?

Why we ask: it decides whether the folder itself is the contract or whether this tool must also answer queries.

A. The web app reads the files straight from the folder on disk; this tool never runs as a server
B. This tool also runs a small local lookup service that the web app asks
C. The web app loads everything into its own database first
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q2. Should the web app depend on Hugging Face's own response shapes, or on a stable summary the tool writes?

Why we ask: Hugging Face can change the shape of its responses over time (risk R4 in `raid-log.md`). A stable summary shields your web app from that, at the cost of one more file to maintain.

A. Only Hugging Face's responses as they were returned (kept exactly)
B. Only a stable summary file written by this tool
C. Both: the exact responses are kept for fidelity, and a stable summary is what the web app reads
D. Not yet defined
X. Other (please specify)

[Answer]:C

## Q3. How should changes to the bundle and folder layout be handled over time?

Why we ask: bundles made today may be read months later by a newer version of the tool, inside an environment where the tool cannot easily be updated.

A. Every bundle and summary file carries a format version number; a newer tool must always read older bundles, and a change that breaks reading bumps the major version
B. Best effort: one current format, with no promise to read older bundles
C. Not yet defined
X. Other (please specify)

[Answer]:A

## Q4. When the same model is brought across more than once at different versions, how should the folder look?

Why we ask: the Hugging Face page lets people look at older versions. Keeping versions side by side takes more space but keeps that possible.

A. Keep each version (commit) side by side, with a marker for which one is the latest
B. Keep only the newest version and replace the older one
C. Not yet defined
X. Other (please specify)

[Answer]:A

## Q5. At what point does the content scan happen on the files coming in? (feasibility Q2)

Why we ask: if the scan looks at the pieces before they are put back together, a scanner sees only fragments of big files, not whole files. That affects how the pieces must be made.

A. On the pieces as they are received, before they are put back together
B. On the rebuilt files, after the pieces are put back together inside
C. On the download side, before the pieces are made
D. Not yet defined
X. Other (please specify)

[Answer]:C

## Q6. Should the pieces be plain slices of the original files, so they can be rejoined by hand with standard operating-system tools if the tool cannot be run?

Why we ask: it makes recovery possible in a bad situation, and it keeps each slice easy to scan or inspect. It limits what the tool can add inside a piece (for example, compression, which model files rarely benefit from anyway).

A. Yes: plain, uncompressed slices that can also be rejoined by hand
B. No: any format the tool chooses is fine
C. Not yet defined
X. Other (please specify)

[Answer]:A
