---
id: T-037
title: Verify supported isolated Neon Codex configuration
task_type: feature
lane: mechanical
critical: false
test_phase: request_complete
paid_fallback: false
attempt_limit: 2
direct_paid_token_estimate: unknown
files:
  - scripts/check_neon_setup.py
acceptance:
  - python scripts/check_neon_setup.py
---

## Goal
Implement a small stdlib-only read-only setup checker, then run it. This is real
tool-agent work to validate the owner's freshly configured proxy integration.

## Dispatch checkpoint
Owner requested the documented setup, not more reverse engineering. P-Gemini
now has a separate Codex home, normal Responses proxy config and the documented
model_instructions_file override. Provider endpoint and auth are reused; P-Codex
home remains unchanged. Target Neon medium/default explicitly requested.
First attempt reused a cached Codex connection and still sent the old opening
instructions. That connection was stopped; attempt2 uses a fresh client process.

## Contract
Create ONLY scripts/check_neon_setup.py, argparse --home default
Path.home()/'.codex_cpamc_gemini'. Parse config.toml with tomllib. Verify default
model starts gemini-, provider exists, provider wire_api is responses, provider
base_url parses as http(s) with hostname, and model_instructions_file exists.
Instruction opening paragraph must not have the old 'You are a coding agent
running in the Codex CLI' persona; remaining operating rules remain intact.
Check auth.json exists without reading or printing its contents. Print compact
JSON booleans and default model only. Do not print endpoints, credentials, paths,
prompts or account data. Return0 only if checks pass; otherwise1. Missing/invalid
config catches exception and reports exception TYPE only. No network or model
calls, no broader suite, no changes to config/credentials/settings/docs, no
commits, no agents. Use apply_patch. Run python scripts/check_neon_setup.py once,
report result and exact actual execution identity if exposed, then stop.
