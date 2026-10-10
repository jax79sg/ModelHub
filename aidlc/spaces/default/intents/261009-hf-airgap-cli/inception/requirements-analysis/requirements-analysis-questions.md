# Requirements Analysis Questions

These questions settle what the first version must do. Earlier answers are not asked again: your intent (`intent-statement`), the feasibility research (`feasibility-assessment.md`, `constraint-register.md`, `raid-log.md`) and the practices in `team-practices.md` already cover the audience, deadline, drive sizes, Python skills, licence handling, and test approach.

## Q1. By default, which files of a model should be downloaded?

Why we ask: many models store the same weights in several formats (for example both a safe numbers-only format and an older format that can contain runnable code), which can double or triple the size. You said a content scan and approval are required (feasibility Q2).

A. Everything in the model's repository, in all formats
B. Everything except duplicate weight formats: prefer the safe numbers-only format (safetensors) when it exists
C. Show me the file list and total size first, and let me choose for each model
D. Not yet defined
X. Other (please specify)

[Answer]:X. I need to know what are the types, and what each does. Then i decide by selecting one or more of them in.

## Q2. How will you tell the tool which models to fetch?

Why we ask: it decides whether the tool must read a list of models or only one name at a time.

A. One model name per command
B. A list of model names in a file, fetched in one run
C. Both A and B
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q3. What should be kept for each model so the web app can show a model page? (select all that apply)

Why we ask: your success measure is that the web app shows "the same key information" as huggingface.co. Everything listed here is available without logging in (feasibility research, E3 to E6). The more you keep, the more the web app can show, and the larger the bundle.

A. The README text and its settings header (licence name, language, tags)
B. Summary details: task type, library, dates, download and like counts, size, parameter counts
C. The file list with sizes and checksums, plus Hugging Face's own safety-scan results
D. The change history and named versions (branches and tags)
E. The community discussions
X. Other (please specify)

[Answer]:A, B, C, D

## Q4. What should happen to pictures and links in a README that point to other websites?

Why we ask: the web app is offline, so those pictures would show as broken. The sample README checked loaded a badge image from another website.

A. Download those pictures too and rewrite the README so it uses the local copies
B. Leave the README as it is and accept broken pictures
C. Download them when it is simple, and report the ones that could not be fetched
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q5. How should the splitting of a bundle into pieces be controlled?

Why we ask: your smallest drive is under 1 GB while some models are over 100 GB, so a bundle has to be cut into pieces that fit a drive.

A. I set a maximum piece size when I create the bundle
B. The tool asks for the size of each drive as I go, fills it, and tells me when to swap drives
C. Both A and B
D. Not yet defined
X. Other (please specify)

[Answer]:A, B

## Q6. What must the tool do inside the air-gapped environment?

Why we ask: you said it should run on both operating systems on both sides (feasibility Q3). This sets how much it has to do on the air-gapped side.

A. Only check that all pieces are present and not damaged
B. Check, and also put the pieces back together into the original files in a folder layout the web app can read
C. Check, put the pieces back together, and also list what models are available there
D. Not yet defined
X. Other (please specify)

[Answer]:C

## Q7. How can the tool be installed on the air-gapped computers?

Why we ask: nothing can be downloaded there, and the earlier research found this to be the least certain part of the plan (risk R3 in `raid-log.md`).

A. Python 3.10 or newer is already installed there
B. Python is not installed, but a single ready-to-run program file can be brought in after approval
C. Neither: only a plain archive of files can be brought in
D. Not known yet
X. Other (please specify)

[Answer]:B

## Q8. About how fast is the internet connection on the download computer?

Why we ask: there is a limit to how fast any download can be, set by the connection. Without this number, a speed goal cannot be checked (risk R10 in `raid-log.md`).

A. Under 100 Mbit/s
B. 100 Mbit/s to 1 Gbit/s
C. Over 1 Gbit/s
D. I don't know
X. Other (please specify)

[Answer]:B

## Q9. What would count as "noticeably faster" for large files?

Why we ask: your success measure for downloads has no number yet. A number lets the tests prove it.

A. At least twice as fast as downloading a file over a single connection
B. At least four times as fast as downloading a file over a single connection
C. As close to the full speed of the connection as the official tool allows
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q10. You asked to see the file types and what each does, then choose. Here they are. If you run the tool without choosing, what should it do?

Why we ask: your answer to Q1 means the tool will list a model's files grouped by type, with a plain explanation, and let you pick one or more types. That is now a requirement. This question only settles what happens when you don't pick.

The types found in typical model repositories (sizes are from the Hugging Face documentation's example for the `gpt2` model):

- `.safetensors`: the model's learned numbers in a plain format that cannot contain runnable code. This is the current standard. About 0.55 GB for `gpt2`.
- `.bin` (for example `pytorch_model.bin`): the older PyTorch format. It uses a method that can hide runnable code, which is why scanners check it. About 0.55 GB.
- `.h5` (for example `tf_model.h5`): the same model for TensorFlow and Keras. About 0.50 GB.
- `.msgpack` (for example `flax_model.msgpack`): the same model for JAX and Flax. About 0.50 GB.
- `.onnx`: a format for running the model in many tools through ONNX Runtime. Several variants, about 0.65 GB each.
- `.tflite`: smaller versions meant for phones and small devices. About 0.13 to 0.50 GB each.
- `.ot`: the model for the Rust library rust-bert. About 0.70 GB.
- `.gguf`: a compact format used by llama.cpp and Ollama. Not in `gpt2`, but common in other models, often in several sizes per model.
- `.json` and `.txt` (for example `config.json`, `tokenizer.json`, `vocab.json`): small settings and word-list files needed to load the model. Kilobytes to a few megabytes.
- `README.md`: the model card, and `.gitattributes`: a technical settings file.

For `gpt2`, the documentation's example shows the whole repository at about 5.6 GB, against about 0.55 GB for the single `.safetensors` file. The other formats are copies of the same model for different tools.

A. Stop and show me the list of types so I choose
B. Fetch the small files plus the `.safetensors` weights (when they exist), and nothing else
C. Fetch everything
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q11. You chose "at least twice as fast as a single connection" (Q9) on a connection of 100 Mbit/s to 1 Gbit/s (Q8). How should the goal be worded?

Why we ask: extra connections only help if a single connection does not already use the whole link. At the slow end of your range a single connection may already be at full speed, so "twice as fast" could be impossible there, while it may be reachable at the fast end. The feasibility research did not measure this.

A. Keep "at least twice as fast as a single connection", and prove it on your actual connection
B. Change it to: the download reaches at least 80% of your measured connection speed
C. Measure first on your connection, then decide the number before building
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q12. If everything you chose does not fit in the one month before the air-gapped environment goes live, which things should slip first? (select all that apply)

Why we ask: you chose a lot (Q4 to Q7) and a one-month deadline (feasibility Q10). Choosing now keeps the essentials safe. Items left unselected stay in the first version.

A. Downloading outside pictures and rewriting the README to use them (Q4)
B. Listing the available models on the air-gapped side (Q6)
C. The interactive "fill a drive and tell me to swap" splitting (Q5), keeping the fixed piece size
D. The standalone program for Windows, doing Linux first (Q7)
E. Nothing should slip; the date can move instead
X. Other (please specify)

[Answer]:E
