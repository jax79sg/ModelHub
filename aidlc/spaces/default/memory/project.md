# Project-Level Rules

> Project-specific specialisation and corrections. Loaded after `org.md` and
> `team.md` as strict-additive guidance; contradictions with broader policy
> are rejected. Populated by practices-discovery and the self-learning loop.
>
> Use sparingly: most teams don't need a project layer. Reach for it
> only when this specific project needs stable, durable guidance beyond the
> team practice (for example, package-specific release checks or an additional
> regression suite for a legacy component).

## Way of Working

<!-- Project-specific specialisation. Example: -->
<!-- This monorepo requires package-scoped branch names and a package owner -->
<!-- review in addition to the team's normal merge policy. -->

## Walking Skeleton

<!-- Project-specific specialisation. Example: -->
<!-- The walking skeleton must exercise the legacy service adapter as well -->
<!-- as the new service boundary. -->

## Testing Posture

<!-- Project-specific specialisation. -->

## Guard Policy

<!-- Project-specific. Mode: strict, relaxed, or off. Strict here holds for every intent, whatever one person asks in chat; relaxed or off here applies to every intent whose policy came from its scope, unless the person sets another; changing this line changes it. A section under the retired Change Control heading, written by an earlier release, is still read. -->

## Deployment

<!-- Project-specific specialisation. -->

## Code Style

<!-- Project-specific specialisation. -->

## Tech Stack

<!-- Technology choices locked for this project. -->

## Decided

<!-- Decisions made in earlier stages that should not be re-asked. -->
<!-- Format: DECIDED: [decision] (Stage [slug], [date]) -->

## Scope Overrides

<!-- Custom scope rules for this project. -->

## Forbidden

<!-- Populated by practices-discovery affirmation gate. -->
<!-- Format: NEVER [behavior] (affirmed [date]) -->
<!-- Example: NEVER throw exceptions across service layer boundaries (affirmed 2026-05-17) -->

## Mandated

<!-- Populated by practices-discovery affirmation gate. -->
<!-- Format: ALWAYS [behavior] (affirmed [date]) -->
<!-- Example: ALWAYS use Result<T,E> for fallible operations in service layer (affirmed 2026-05-17) -->

None. (affirmed 2026-10-09)

## Corrections

<!-- Project-specific corrections from human feedback. -->
<!-- Format: NEVER/ALWAYS [behavior] (learned [date]) -->
- Write the decision log as a flat table with one row per decision, its ID, and the question it came from, so later stages can cite a decision by its ID. (learned 2026-10-12) <!-- cid:261011-enterprise-modelhub:approval-handoff:291fb26584acb877714214e48efdf0d534782aad3ad64e96edba576553393c80 -->
- When a vendor's documentation does not say where or how something is stored, do not build the path or call from a guess: discover it at run time (for example by listing), and record the question for confirmation on the real system. (learned 2026-10-12) <!-- cid:261011-enterprise-modelhub:contract-design:33c47b69ebcd7c0da2c435e3c082ff89ef7e5f9cf62edce3229a67134cd3d987 -->
- Assign Build and Test verdicts only from existing tests and CI results; a scale, timing or real-system target with no check is Unverified, never guessed to be met. (learned 2026-10-17) <!-- cid:261014-enterprise-build:build-and-test:a570a673a646717ed0ef713b6968daaa97cc52ee731155be75c7111f91451cd1 -->
