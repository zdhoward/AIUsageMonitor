# CPAMC OAuth callbacks and Neon checks

## Callback address

The API listener address and an OAuth redirect are separate settings. CPAMC
8.1.1's management handler builds its internal callback-forwarding URL with
`127.0.0.1`; changing the server host does not change that target. Antigravity's
provider redirect also uses a loopback URL. Replacing the provider's redirect
host may fail its registered OAuth redirect checks.

When the browser is on a different device, use the management page's callback
URL input: after provider approval, copy the full final redirected URL into that
input and submit it to the same pending login session. The installed management
page supports this flow and sends `redirect_url` to its authenticated callback
endpoint. The URL contains one-use authorization material: never put it in chat,
screenshots, logs or a tracked file. This documentation does not initiate a login
or consume/reset quota.

When the browser is on the server PC but CPAMC listens only on a Tailscale
interface, the final loopback forwarding target can also be unreachable. The
same callback-input flow avoids changing the provider redirect. Automatic remote
forwarding requires an upstream callback-base setting or a carefully scoped
forwarder; the current release has no documented callback-base setting.

For a browser on this PC, the installed **CPAMC Callback Bridge** task listens
only on loopback port8317. It forwards only the final `/anthropic/callback` and
`/codex/callback` GET paths to the existing `CPAMC_URL`; it does not forward the
management API, model API, cookies or authorization headers. It does not change
provider redirect URIs, initiate logins, log callback queries or store codes.
The target follows the existing private service setting. A browser on another
device must still use callback-URL submission or that device's own tunnel.

Install/start with `scripts/cpamc-callback-bridge.ps1 -Install`; remove with
`-Remove`. The limited-user task runs headlessly at logon with a 5-minute watchdog trigger
(`IgnoreNew`), restarts up to three times after a failure, and binds exclusively
on Windows (`allow_reuse_address = False`) so it will not take over an occupied
port. Its safe
diagnostic path is `http://127.0.0.1:8317/_bridge/health`. No broader network
binding was installed. Deployment health checks do not exercise a real Google,
Claude or Codex sign-in; the owner still completes any account login.

Source evidence:

- [CPAMC callback-forwarder implementation](https://github.com/router-for-me/CLIProxyAPI/blob/v8.1.1/internal/api/handlers/management/auth_files_oauth_callback.go)
- [Management callback URL submission](https://github.com/router-for-me/CLIProxyAPI/blob/v8.1.1/internal/api/handlers/management/oauth_callback.go)
- [Antigravity OAuth redirect](https://github.com/router-for-me/CLIProxyAPI/blob/v8.1.1/sdk/auth/antigravity.go)

## Supported Neon client setup

P-Gemini uses the normal Codex custom-provider Responses connection to CPAMC.
It has its own Codex home instead of sharing P-Codex's default model and client
state. The proxy endpoint and existing authentication are retained. Its default
model is `gemini-4-neon-xhigh(medium)` with medium reasoning.

The client uses Codex's documented `model_instructions_file` setting. Its opening
persona is a neutral software engineering assistant; the existing operating,
safety and tool instructions are preserved. Other proxy providers keep their
original home and instructions. Shared skills stay linked to their source.

Sources: [Codex configuration reference](https://developers.openai.com/codex/config-reference/)
(`model_instructions_file`) and [custom-provider configuration](https://developers.openai.com/codex/config-advanced/).
This is a supported client setting, without a new model proxy or request-rewrite
server. The local configuration checker is `python scripts/check_neon_setup.py`.
It checks local structure only; it does not verify credentials, network
availability, or the semantic completeness of operating rules.

Verified on 2026-11-22 after restarting the cached P-Gemini Codex connection:
Neon medium completed a real multi-step task, read the ticket, wrote the checker
through apply_patch and executed it with exit0. Parent review confirmed the
artifact and command activity; missing-home validation correctly returns exit1.
The other proxy provider's default configuration remains unchanged. This is one
successful organic output, not evidence of long-term reliability or promotion.

Diagnosis before applying the supported setup: the captured agent opening
persona, even in a tiny request, reproduced Google's generic RESOURCE_EXHAUSTED
429. The same full conversation/tools/streaming request succeeded after replacing
only its opening identity text while preserving the safety sentence and all
remaining instructions. Synthetic requests larger than the failed agent request,
tools, streaming and both API endpoints worked. This is evidence of an opening-
instruction compatibility problem; Google's internal reason is not exposed.
It does not establish that every429 means this problem or explain Google's intent.

Earlier quota/update guesses were not the cause of this reproduction. Avoid
repeating inference sweeps; validate the configured client with a real bounded
tool-agent task. Keep implementation quality review separate from route health.

The existing verified updater installed official CPAMC8.1.1, kept the management
page at1.28.3 and verified authenticated health. A temporary Windows replacement
access error on the first attempt recovered without a version change; a changed
diagnostic retry then completed. The updater reports current. No provider login,
tokens, model billing or broad quota-routing settings were changed.
