# Practices Discovery Questions

These questions settle how you want to work on this project. Your answers become the team's recorded practices and apply to every later step. A draft based on what is in the project is in `team-practices.md`, with the evidence in `evidence.md`.

## Q1. How do you want to manage changes to the code?

Why we ask: the project folder is not under version control yet, so there is no history to learn from. The framework's default is one main line of work with short-lived branches merged back quickly, each piece of work as a single commit.

A. Use the default: one main line, short-lived branches, each piece of work squashed into a single commit
B. One main line, with longer-lived branches for bigger pieces of work
C. Commit straight to the main line, with no branches (I am the only developer)
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q2. Should the project folder be put under version control now?

Why we ask: the workflow records each piece of work as a commit, and automated checks usually run from a code host.

A. Yes, set it up locally (and I will connect a code host later)
B. Yes, and it will live on a code host I already use
C. No, not at this time
D. Not yet defined
X. Other (please specify)

[Answer]: B

## Q3. Build a thin end-to-end slice first? A walking skeleton is a minimal version that runs the whole way through, built first to prove the pieces connect before the real features go in.

Why we ask: the existing prototype already runs end to end in a basic form, so a fresh slice may or may not be needed.

A. Yes, always build a thin slice first for each new piece of work
B. No, never; build features directly
C. Decide each time, depending on the piece of work
D. Not yet defined
X. Other (please specify)

[Answer]:A

## Q4. How do you want to approach testing?

Why we ask: this sets when tests are written relative to the code. The default for a plan like this one is to write the tests after each part is built.

A. Write each part first, then its tests (test-after)
B. Write the tests first, then the code (test-driven)
C. Describe behaviour in plain scenarios first, then build to match (behaviour-driven)
D. A mix of approaches
E. Not yet defined
X. Other (please specify)

[Answer]:B

## Q5. How much automated test coverage must a change have before you accept it?

Why we ask: the plan's default is that each fix has a test for it and that the existing tests keep passing. Some teams set a percentage floor.

A. Each change has a test for it, and the existing tests keep passing (no percentage floor)
B. A coverage floor of 80% of lines
C. A higher floor (please give the number)
D. No requirement
E. Not yet defined
X. Other (please specify)

[Answer]:A

## Q6. Where should automated checks (tests and building the package) run, and how will the tool be handed out?

Why we ask: the plan includes a step that sets up automated checks on both Linux and Windows. The tool is a command-line program, so "release" means producing something installable, not updating a live service.

A. On GitHub, with installable files attached to each release
B. On another service or on my own machine, with installable files handed over directly
C. Only on my own machine for now, with files handed over directly
D. Not yet defined
X. Other (please specify)

[Answer]:B

## Q7. How should code be formatted and checked?

Why we ask: the project already uses the formatter-and-checker tool ruff with a line length of 100.

A. Keep ruff as it is for both checking and formatting
B. Keep ruff for checking and add another formatter (please name it)
C. Use different tools (please name them)
D. Not yet defined
X. Other (please specify)

[Answer]: A

## Q8. Are there hard rules every later step must always follow, or never do?

Why we ask: only rules you state yourself are recorded as hard rules. Examples of the shape: "always verify file checksums after download" or "never download private models". Pick "None" if you have none.

A. None for now
B. Yes, I will write them (please type them using the other-answer line)
C. Not yet defined
X. Other (please specify)

[Answer]:A
