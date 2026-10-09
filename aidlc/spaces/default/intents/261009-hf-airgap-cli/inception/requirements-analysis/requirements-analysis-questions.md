# Requirements Analysis Questions

These questions settle what the first version must do. Earlier answers are not asked again: your intent (`intent-statement`), the feasibility research (`feasibility-assessment.md`, `constraint-register.md`, `raid-log.md`) and the practices in `team-practices.md` already cover the audience, deadline, drive sizes, Python skills, licence handling, and test approach.

## Q1. By default, which files of a model should be downloaded?

Why we ask: many models store the same weights in several formats (for example both a safe numbers-only format and an older format that can contain runnable code), which can double or triple the size. You said a content scan and approval are required (feasibility Q2).

A. Everything in the model's repository, in all formats
B. Everything except duplicate weight formats: prefer the safe numbers-only format (safetensors) when it exists
C. Show me the file list and total size first, and let me choose for each model
D. Not yet defined
X. Other (please specify)

[Answer]:

## Q2. How will you tell the tool which models to fetch?

Why we ask: it decides whether the tool must read a list of models or only one name at a time.

A. One model name per command
B. A list of model names in a file, fetched in one run
C. Both A and B
D. Not yet defined
X. Other (please specify)

[Answer]:

## Q3. What should be kept for each model so the web app can show a model page? (select all that apply)

Why we ask: your success measure is that the web app shows "the same key information" as huggingface.co. Everything listed here is available without logging in (feasibility research, E3 to E6). The more you keep, the more the web app can show, and the larger the bundle.

A. The README text and its settings header (licence name, language, tags)
B. Summary details: task type, library, dates, download and like counts, size, parameter counts
C. The file list with sizes and checksums, plus Hugging Face's own safety-scan results
D. The change history and named versions (branches and tags)
E. The community discussions
X. Other (please specify)

[Answer]:

## Q4. What should happen to pictures and links in a README that point to other websites?

Why we ask: the web app is offline, so those pictures would show as broken. The sample README checked loaded a badge image from another website.

A. Download those pictures too and rewrite the README so it uses the local copies
B. Leave the README as it is and accept broken pictures
C. Download them when it is simple, and report the ones that could not be fetched
D. Not yet defined
X. Other (please specify)

[Answer]:

## Q5. How should the splitting of a bundle into pieces be controlled?

Why we ask: your smallest drive is under 1 GB while some models are over 100 GB, so a bundle has to be cut into pieces that fit a drive.

A. I set a maximum piece size when I create the bundle
B. The tool asks for the size of each drive as I go, fills it, and tells me when to swap drives
C. Both A and B
D. Not yet defined
X. Other (please specify)

[Answer]:

## Q6. What must the tool do inside the air-gapped environment?

Why we ask: you said it should run on both operating systems on both sides (feasibility Q3). This sets how much it has to do on the air-gapped side.

A. Only check that all pieces are present and not damaged
B. Check, and also put the pieces back together into the original files in a folder layout the web app can read
C. Check, put the pieces back together, and also list what models are available there
D. Not yet defined
X. Other (please specify)

[Answer]:

## Q7. How can the tool be installed on the air-gapped computers?

Why we ask: nothing can be downloaded there, and the earlier research found this to be the least certain part of the plan (risk R3 in `raid-log.md`).

A. Python 3.10 or newer is already installed there
B. Python is not installed, but a single ready-to-run program file can be brought in after approval
C. Neither: only a plain archive of files can be brought in
D. Not known yet
X. Other (please specify)

[Answer]:

## Q8. About how fast is the internet connection on the download computer?

Why we ask: there is a limit to how fast any download can be, set by the connection. Without this number, a speed goal cannot be checked (risk R10 in `raid-log.md`).

A. Under 100 Mbit/s
B. 100 Mbit/s to 1 Gbit/s
C. Over 1 Gbit/s
D. I don't know
X. Other (please specify)

[Answer]:

## Q9. What would count as "noticeably faster" for large files?

Why we ask: your success measure for downloads has no number yet. A number lets the tests prove it.

A. At least twice as fast as downloading a file over a single connection
B. At least four times as fast as downloading a file over a single connection
C. As close to the full speed of the connection as the official tool allows
D. Not yet defined
X. Other (please specify)

[Answer]:
