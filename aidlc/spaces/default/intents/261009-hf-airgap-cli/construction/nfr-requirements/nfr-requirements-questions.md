# NFR Requirements Questions

NFR means non-functional requirement: how well the tool must work, as opposed to what it does. `requirements.md` already fixes some (NFR1 to NFR8: 80% of connection speed, byte-level damage detection, restart, no network on the air-gapped side, token secrecy, both operating systems, tests first). These questions ask for the numbers and choices that are still open. The inputs are `requirements.md` and `contract-summary.md`; the step that designs the logic in detail (`functional-spec`, `rules`) was skipped by the approved plan, so I use the requirements and the contracts instead.

## Q1. How much memory may the tool use?

Why we ask: files can be hundreds of gigabytes, so the tool must read and check them in small pieces rather than loading them whole. The limit sets how big those pieces can be.

A. Up to 512 MB
B. Up to 2 GB
C. Up to 8 GB
D. No limit that matters on my computers
E. Not yet defined
X. Other (please specify)

[Answer]:X. 8GB

## Q2. How long is acceptable to put a 100 GB model back together and check it inside the air-gapped environment?

Why we ask: this step reads and checks every byte, so its time is set mostly by the speed of the disks there, which I do not know.

A. Under 30 minutes
B. Under 2 hours
C. Under 8 hours
D. As long as it takes, as long as it can be stopped and restarted
E. Not yet defined
X. Other (please specify)

[Answer]:D. And the process can be visually seen so ppl don't thinnk it hanged

## Q3. What is the largest picture the tool should download from a README?

Why we ask: requirement FR4.4 says pictures over a size limit are skipped. A limit protects against a README that points at a huge or hostile file.

A. 5 MB
B. 25 MB
C. 100 MB
D. Not yet defined
X. Other (please specify)

[Answer]:X. 7MB

## Q4. Do you need to detect deliberate tampering with a bundle, or only accidental damage?

Why we ask: checksums stored in the bundle catch accidents (a bad drive, a failed copy). Someone who changes both a file and its checksum would not be caught. Catching that needs a signature with a secret key, which adds key handling.

A. Accidental damage only: checksums are enough
B. Also detect tampering: sign each bundle's manifest with a key I keep
C. Not yet defined
X. Other (please specify)

[Answer]:B

## Q5. Which operating system versions must the program file run on? (select all that apply)

Why we ask: a ready-to-run program built on a newer Linux can fail to start on an older one, so the oldest Linux sets how it must be built.

A. Windows 11
B. Windows 10
C. Windows Server (2016 to 2022)
D. A recent Linux (for example Ubuntu 22.04 or RHEL 9, and newer)
E. An older Linux than that (for example Ubuntu 20.04 or RHEL 8)
X. Other (please specify)

[Answer]:A,B,C,D,E

## Q6. Which processor types must it run on? (select all that apply)

Why we ask: this was assumed to be 64-bit Intel/AMD in `requirements.md` (assumption A1). A separate program file is needed for each type.

A. 64-bit Intel/AMD on Windows
B. 64-bit Intel/AMD on Linux
C. ARM on Windows
D. ARM on Linux
E. Not yet defined
X. Other (please specify)

[Answer]:A,B

## Q7. How should the single program file be built?

Why we ask: your answer to Q7 of the requirements asked for one ready-to-run file for Windows and one for Linux. The tool's download library includes native parts that some packaging tools handle badly, which can only be settled by trying.

A. Use the most common packaging tool (PyInstaller) in its single-file mode
B. Use a compiler-based tool (Nuitka) for a single file
C. Try both in a short test build on both systems, report what worked, and let that choose
D. Not yet defined
X. Other (please specify)

[Answer]:C

## Q8. How many models, and how many versions of each, will the air-gapped store hold?

Why we ask: it sets how fast the `list` command and the web app's folder reading must stay.

A. Up to about 10 models
B. Up to about 100 models
C. Up to about 1,000 models
D. Not yet defined
X. Other (please specify)

[Answer]:C

## Q9. You said up to about 1,000 models (Q8). About how many versions (commits) of each model will you keep side by side?

Why we ask: the contract keeps each version in its own folder (contract Q4), so the number of folders, and the time to list them, is models times versions.

A. One version each
B. Up to about 3 versions each
C. Up to about 10 versions each
D. Not yet defined
X. Other (please specify)

[Answer]: C

## Q10. You want tampering detected (Q4). How will the public half of the signing key reach the air-gapped environment?

Why we ask: if the key travels inside the same bundle that it checks, someone who can change the bundle can also change the key, and the signature protects nothing. The key has to arrive by a separate, trusted route, checked once by a person.

A. Carried across once, separately from the bundles (for example with the approved program file), and checked by a person on arrival
B. Carried inside each bundle (protects only against accidents, not against someone altering the bundle)
C. Not yet defined
X. Other (please specify)

[Answer]: A. Can we use the same tool to check on arrival.
