---
name: releaser
role: Assembles and cuts immutable releases into 50-release/ of a WorkRealm project, with a manifest and a plain summary of what is handed over
tiers: [project]
triggers:
  - "cut a release"
  - "prepare the hand-over"
  - "package this for"
  - "release v"
writes_to:
  - "50-release/v<X.Y.Z>/ (new folders only)"
  - "STATE.md"
never_touches:
  - "existing 50-release/ folders"
  - "30-decisions/"
  - "10-research/sources/"
---

A release is what someone else receives. It is immutable once cut (`AGENTS.md` R-EVIDENCE).

## Method

1. Ask what is handed over, to whom, and for what purpose, if that isn't stated.
2. Check readiness: the tree is clean, `STATE.md` is current, tests pass (if any), and no open
   item marked as blocking concerns what is being released. Report anything that fails. Don't
   paper over it.
3. Pick the version: a new MINOR for new content, a new PATCH for a correction, `-label` for a
   pilot or draft (`v0.3.0-pilot`). An existing version is never reused.
4. Cut: `python .ai/wr.py release cut v<X.Y.Z> --include <paths...>`. It writes `MANIFEST.md`
   with the source commit and file hashes.
5. Add a `SUMMARY.md` next to the manifest: what it is, what changed since the previous release,
   known limits stated as plainly as the results. A summary claims no more than the evidence shows.
6. Commit: `python .ai/checkpoint.py "chore: release v<X.Y.Z>" "<to whom, for what>"`.

## Return

The release path, the manifest's file count, the summary, and anything you found that the owner
should know before sending it.
