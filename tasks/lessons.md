# Lessons

- **Apply the owner's scope literally, first time.** "Soonest 7d cooldown" was first delivered as a label on a counter that still included 5h windows, so it needed three more rounds (7d only, per account, Flash only). When a display rule is named, enforce every part of it in the first change and capture the screen against that rule.
- **Cooldowns are per account.** A pool-average percentage hides one exhausted account behind a healthy one. Use `q[]`/`qz[]` (per-account remaining and reset) for any "is something exhausted" test; use the average only for rings.
- **Check which account a credential belongs to before blaming the parser.** T3's stored Antigravity login is a different Google account from the two CPAMC ones and returns only `3p-*` buckets. The Proxy view (CPAMC) holds the real Gemini numbers. Compare against live CPAMC output and the owner's `/usage` before changing code.
- **A service restart empties the proxy screen for ~30-45 s.** Wait, then capture; do not read the "Waiting for proxy data" frame as a failure.
- **Strip invisible characters from doc edits.** A zero-width space landed inside an identifier in `DATA_SOURCES.md`; grep `[^\x00-\x7F]` after doc edits.
