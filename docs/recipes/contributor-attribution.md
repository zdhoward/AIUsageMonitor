# Contributor attribution

AI tools are not contributors. Do not add AI identities as authors, committers,
or Co-Authored-By trailers. Preserve legitimate human credit.

Run `python scripts/attribution_guard.py install` after cloning. This installs
commit-message and push checks, retaining and chaining existing hooks (including
the public push guard). Re-running installation is safe. CI also checks every
reachable commit, including merges and incoming branches.

Audit with `python scripts/attribution_guard.py check HEAD`.

To prepare historical cleanup, run
`python scripts/attribution_guard.py prepare SOURCE NEW_BRANCH`. This creates a
separate branch that removes AI co-author trailers, preserves all file trees,
human credits, identities and dates, and verifies the rewritten commits.
Existing refs and remote history stay untouched. Signed history is refused.
If the privacy guard finds historical machine paths, `--redact-local-paths`
also redacts paths in the setup notes and scheduled-task description. Review
that tip diff before publishing; attribution-only cleanup preserves every tree.

Publishing rewritten history requires the owner's explicit approval. Back up
the original refs first, use an exact force-with-lease, and coordinate existing
clones and historical release tags. GitHub may cache contributor displays.
Never hide genuine contributors or replace their identities with the owner's.
