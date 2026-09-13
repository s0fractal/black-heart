# CM-4 — local experience skill

**ACTIVE / implementation in progress.** CM-3 is accepted. This slice chooses
[a skill](../../../.agents/skills/black-heart-experience/SKILL.md) over the existing
CM-2 CLI: the accepted receiver used shell/file tools successfully, and no new
server or transport is required for local save, search and inspection.

The skill maps natural requests to existing operations, keeps source/basis
visible and distinguishes byte verification, replay and advice acceptance.
It requires partial search errors to remain visible and preserves duplicate
records rather than deleting them to make retries succeed. New experience uses
the existing profile; no stake field or automatic advice adoption is added.

The repository skill is the reviewable source. An operator can load that file
explicitly. Any local installation is a separate convenience; this PR does not
establish automatic discovery across agents or change global agent settings.

The first trial uses the owner's request “пробуй, чого чекати )” as authorization.
The compiler chooses an EMPIRICAL corpus scenario: import the three recorded
examples, search/read them, verify the saved CM-3 exchange offline, and save a
new bounded experience. This is an actual tool path in the current Codex session,
not a fresh user's independently observed choice or a blind skill evaluation.
The original CM-3 response and frozen inputs remain unchanged. No provider
session, OAuth proxy, external API purchase, or evidence replay is needed.
