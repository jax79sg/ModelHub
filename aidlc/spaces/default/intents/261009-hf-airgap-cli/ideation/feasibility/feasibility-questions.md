# Feasibility Questions

Context: these questions follow the intent statement (`intent-statement`, in `ideation/intent-capture/`). The research on what Hugging Face makes available is done by me and written up after your answers. These questions cover only what I cannot look up: your environment, your process, and your limits.

## Q1. How do files get from the internet-connected side into the air-gapped environment today?

Why we ask: the transfer medium sets limits on file size, file names, and whether big model files must be split into pieces.

A. Removable drive or disk with no practical file-size limit
B. Removable media with a file-size limit (for example a drive formatted so that files over 4 GB are not allowed)
C. A one-way network gateway or file-transfer service with its own size or type limits
D. Not yet defined
X. Other (please specify)

[Answer]: A. But the drive varies in sizes.

## Q2. Is anything checked or scanned before files are allowed into the air-gapped environment?

Why we ask: a scan step (for example a malware scan) can reject or slow down certain file types, and some model file formats can contain executable code.

A. Yes, a malware or content scan is required
B. Yes, an approval or review of what is brought in is required
C. Both A and B
D. No checks today
E. Not yet defined
X. Other (please specify)

[Answer]: C

## Q3. Which computers will run the tool? (select all that apply)

Why we ask: your request says it must work on both Linux and Windows. This asks on which side of the gap each one sits, because the air-gapped side cannot install extras from the internet.

A. Linux computer(s) with internet access (the download side)
B. Windows computer(s) with internet access (the download side)
C. Linux computer(s) inside the air-gapped environment (for unpacking or checking bundles)
D. Windows computer(s) inside the air-gapped environment (for unpacking or checking bundles)
E. Not yet defined
X. Other (please specify)

[Answer]:A, B, C, D

## Q4. Can the internet-connected computer reach huggingface.co directly?

Why we ask: downloads come from huggingface.co and from separate content-delivery hostnames. A proxy or an allow-list of web addresses can block those.

A. Yes, direct access to the open internet
B. Yes, through a proxy that needs configuring
C. Only to an allow-list of addresses, which I can ask to extend
D. Only to an allow-list of addresses, and it cannot be extended
E. Not yet defined
X. Other (please specify)

[Answer]:A

## Q5. How big and how many are the models you expect to bring across?

Why we ask: size decides how much faster downloads matter, how much disk space is needed, and whether bundles must be split.

A. A few models, each under about 10 GB
B. Several models, some up to about 100 GB
C. Many models, including some over 100 GB
D. Not yet defined
X. Other (please specify)

[Answer]:C

## Q6. Are there rules about which models may be brought into the air-gapped environment? (select all that apply)

Why we ask: public models carry different licences, and some require accepting terms. Your first version already leaves out private or gated models.

A. No rules beyond what Hugging Face already allows
B. Only models with certain licences may be brought in
C. Each model's licence text must be kept and shown with the model
D. Not yet defined
X. Other (please specify)

[Answer]: A, C

## Q7. Which programming languages are you comfortable building and maintaining this tool in? (select all that apply)

Why we ask: your request asks me to consider the best language. Your skills are a real constraint on that choice, alongside how well each language is supported by Hugging Face's own libraries.

A. Python
B. JavaScript or TypeScript
C. Rust
D. Go
E. No strong preference
X. Other (please specify)

[Answer]: A

## Q8. What are the time, budget, and organisational limits on this work?

Why we ask: a hard deadline or an approval step changes how much research and polish fits.

A. No deadline and no budget limit; it is a project I run at my own pace
B. A deadline tied to the air-gapped environment going live
C. Tools brought into the air-gapped environment need an approval step that takes time
D. Both B and C
E. Not yet defined
X. Other (please specify)

[Answer]: B

## Q9. You said the transfer drives vary in size (Q1) and some models are over 100 GB (Q5). How small can the smallest drive you would use be?

Why we ask: if a model is bigger than the drive, the bundle has to be split across several drives, which changes what the tool must do.

A. Under 100 GB
B. Between 100 GB and 1 TB
C. Over 1 TB
D. It varies too much to say
X. Other (please specify)

[Answer]: X. Smallest is less than 1GB.

## Q10. You said there is a deadline tied to the air-gapped environment going live (Q8). Roughly how far away is it?

Why we ask: it decides how much research and polish fits before the first usable version is needed.

A. Within about 1 month
B. About 1 to 3 months
C. More than 3 months
D. Not yet known
X. Other (please specify)

[Answer]:A
