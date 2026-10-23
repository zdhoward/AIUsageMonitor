# Device protocol and local API

The PC service collects usage data. The ESP32 renders the compact payload and acknowledges it; it does not query AI providers. Sources are [snapshot.py](../service/aimon/snapshot.py), [server.py](../service/aimon/server.py), [model.cpp](../firmware/AIUsageMonitor/model.cpp) and the [sketch](../firmware/AIUsageMonitor/AIUsageMonitor.ino).

## Serial framing

- 115200 baud, 8 data bits, no parity, 1 stop bit.
- Host sends one UTF-8 JSON object per newline; carriage returns are ignored.
- Firmware accepts payload version `v: 1`. Its receive line buffer is 4096 bytes, including the terminating null; oversized lines are discarded at the next newline.
- Valid payload: device replies `@ACK <seq>`. Parse/version failure: `@ERR parse failed (...)`; the last valid model is retained.
- Boot emits `@HELLO aimon-fw ...`, compiled display-pin diagnostics in `@SETUP ...`, and touch initialization status. The service logs status/ack messages.

Minimal illustrative payload, with synthetic measurements:

```json
{
  "v": 1,
  "seq": 42,
  "hm": "12:34",
  "ok": 1,
  "act": {"s": "idle"},
  "acc": [
    {
      "p": "CL1",
      "c": "d97757",
      "pl": "Pro",
      "age": 10,
      "st": 0,
      "rc": 0,
      "w": [
        {"l": "5h", "u": 25, "r": 3600},
        {"l": "7d", "u": 60, "r": 172800}
      ]
    }
  ]
}
```

`u` is percent **used** on the wire; console rings show `100 - u` remaining. `r` is seconds to reset, not an epoch timestamp. `r: 0` is due; `r: -1` is unavailable. `u: -1` means unknown, while `u: 0` is a real zero-used measurement.

## Payload fields

### MINT extension (T-009B contract)

Optional `mint` is `{ "sid":"18e0123456789abc", "n":1, "e":"content", "ttl":15000 }`.
`sid` is exactly 16 lowercase hex digits (host startup time in nanoseconds),
`n` is a positive uint32 loop revision, `e` is exactly content/happy/curious/
bored/sleepy/surprised/stressed, and `ttl` is an integer 1..15000 milliseconds
remaining at send time.
Firmware accepts only increasing `(sid,n)` identities, retaining the identity
after expiry; duplicates never extend a lease. A newer sid allows service restart.
Host clock rollback requires device reboot or waiting for the clock to recover.
No identity survives device reboot; this is ordered local transport, not an
authenticated anti-replay protocol. Missing/invalid/replayed mint clears to
content immediately; malformed whole JSON leaves the current lease to expire.
Expiry uses device uptime even during disconnect or unrelated quota updates.
Old firmware ignores mint; old service leaves new firmware neutral. Reconnect
serializes current state and remaining lease, never queued reactions. The
service bounds the complete UTF-8 JSON line to 4095 bytes excluding newline.

`POST /v1/mint/react?action=pet|play|nap` (empty body) queues one finite reaction.
Unknown/duplicate query fields or bodies return 400; same active/pending action
coalesces, another action while busy returns 429. No reaction extends an active
deadline. This route works with serial disabled and does not refresh sources.

| Field | Meaning |
| --- | --- |
| `v`, `seq`, `hm` | Protocol version, acknowledgement sequence, host local `HH:MM` |
| `ok`, `err` | Source collection status and optional short error summary |
| `act` | Activity: `s` run/idle/na, `p` provider label, `m` shortened model, `n` running count, `t` elapsed seconds |
| `acc` | Accounts: `p` name, `c` RGB hex, `pl` plan, `age` source age seconds, `st` stale flag, `x` unavailable reason, `rc` banked reset credits, `w` windows |
| `acc[].w[]` | `l` window label, `u` percent used, `r` seconds to reset |
| `hi` | Most depleted fresh measured window: `u`, `p`, `w` |
| `use` | Subscription API-price estimates: `c1` today cents, `c7` rolling seven-day cents; `i1`, `cr1`, `o1` token counts; `unp` unpriced flag; `h` 24 hourly cost buckets in cents |
| `byp` | Per-account estimated today cost: `p`, `c1` |
| `free` | Free-model history: `n` message/call records today, `t` tokens, optional most frequent `m` model |
| `nim` | Observed NIM free-history record count `n`; not a provider quota |
| `or` | Optional OpenRouter reported free used/limit `fu`/`fl`, daily spend `d` cents, budget `b` cents, age, or unavailable/error `x` |
| `mint` | Optional face expression lease, session/revision identity and remaining TTL; contract above |

The service emits at most three windows per account. Firmware stores at most four accounts and three windows each; the console intentionally shows three fixed slots and the 5h/7d labels. String fields have bounded buffers and may be truncated. See source for exact limits before extending the protocol.

## Cached values and time

The model merges by account name and window label. Missing/unknown measurements keep the last valid measurement, with source age and reset countdown advanced. Explicit numeric zero replaces a previous measurement, including zero banked reset credits. Missing accounts remain cached and stale. No cache survives power loss.

The firmware ages time using its uptime since payload receipt. The service computes countdowns from source reset timestamps. It wakes at future deadlines to reread local sources and otherwise polls normally. Neither side assumes that a deadline means quota refilled.

## Diagnostic commands

Commands are newline-terminated and begin with `!`:

| Command | Effect |
| --- | --- |
| `!HELLO` | Repeat firmware version, dimensions, framebuffer and pin diagnostics |
| `!NEXT` | Advance to the other view; reply `@VIEW next` |
| `!ROT n` | Set temporary rotation `n & 3`; reboot restores config |
| `!SHOT` | Render and dump the current framebuffer |

`!SHOT` replies `@SHOT <width> <height> 8\n`, followed by exactly `width * height` **binary RGB332 bytes**, then `\n@SHOTEND\n`. The three high bits are red, next three green, final two blue. Do not read image bytes with a text line parser. If no framebuffer is available, it replies `@ERR no framebuffer`. [screenshot.py](../scripts/screenshot.py) handles the binary framing and PNG encoding, while coordinating serial access with the service.

## HTTP API

Default base URL: `http://127.0.0.1:8797`. JSON responses use `Cache-Control: no-store`.

| Method / path | Response / purpose |
| --- | --- |
| `GET /v1/device` | Compact device payload, same format as serial |
| `GET /v1/status` | Debugging state: account/window details, source timestamps/errors, activity and record counts |
| `GET /healthz` | Liveness, refresh timestamp, source errors, serial port/pause state, last push/ack and firmware hello |
| `POST /v1/serial/pause?seconds=N` | Release serial port; default 120 seconds, clamped to 1–900 |
| `POST /v1/serial/resume` | Resume serial operation |
| `POST /v1/mint/react?action=pet` | Loopback-only finite reaction; action pet/play/nap, empty body |

Unknown routes return 404, except POST requests with serial disabled return 409 after MINT route handling. MINT works in HTTP-only mode. There is no HTTP route to force a provider refresh. Health `ok: true` is service liveness; inspect `source_errors` and timestamps for data health.

Example:

```powershell
Invoke-RestMethod http://127.0.0.1:8797/healthz
```

The API has **no authentication**. Keep it bound to localhost unless deliberately experimenting on a trusted LAN. Debugging responses and logs contain display names, model names, timestamps and paths/instance metadata; treat them as usage telemetry even though credentials and prompt bodies are excluded. Wi-Fi mode polls `/v1/device` and has not been hardware-tested.
