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
`-Remove`. The limited-user task runs headlessly at logon and restarts up to
three times after a failure. It will not take over an occupied port. Its safe
diagnostic path is `http://127.0.0.1:8317/_bridge/health`. No broader network
binding was installed. Deployment health checks do not exercise a real Google,
Claude or Codex sign-in; the owner still completes any account login.

Source evidence:

- [CPAMC callback-forwarder implementation](https://github.com/router-for-me/CLIProxyAPI/blob/v8.1.1/internal/api/handlers/management/auth_files_oauth_callback.go)
- [Management callback URL submission](https://github.com/router-for-me/CLIProxyAPI/blob/v8.1.1/internal/api/handlers/management/oauth_callback.go)
- [Antigravity OAuth redirect](https://github.com/router-for-me/CLIProxyAPI/blob/v8.1.1/sdk/auth/antigravity.go)

## Neon availability

On 2026-11-22 the exact medium model name returned successful small chat replies,
while T3/Codex tool-agent requests returned Google `RESOURCE_EXHAUSTED` / HTTP429
before any patch. Full quota and a small successful reply do not prove the larger
Responses/tool workload is currently accepted. An implementation task failed on
8.1.0 and one bounded post-update task failed on 8.1.1 as well. No code-quality
pass was inferred from these availability failures.

The existing verified updater installed official CPAMC8.1.1, kept the management
page at1.28.3 and verified authenticated health. A temporary Windows replacement
access error on the first attempt recovered without a version change; a changed
diagnostic retry then completed. The updater reports current. No provider login,
tokens, model billing or broad quota-routing settings were changed.
