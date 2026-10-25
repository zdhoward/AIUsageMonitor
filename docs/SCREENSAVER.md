# Idle screensaver

Console and Details default to 30 seconds without usage changes, then show the
configured saver target (MINT by default). Usage changes wake the original view
for another 30 seconds. Face and Images remain awake. There is no saver page in
the navigation cycle. A tap or `!NEXT` during saving wakes the original view;
the next tap advances. See [UI.md](UI.md) for policy switches and comparison rules.

If any reported quota window is `due` and its known used percentage is below
100%, Console and Details stay awake (or leave an active saver) so the available
quota stays visible. Unknown usage/reset times and 100%-used windows do not
block saving. This also applies when usage-change waking is disabled.

## Device evidence (2026-10-23)

Production build flashed to COM6 with hash verification. With the service
temporarily paused by the existing screenshot helper, a live payload followed
by a 31-second wait produced [idle MINT](img/T-010-idle.png). Feeding fresh live
usage then produced [awake Console](img/T-010-wake.png), without `!NEXT` or touch;
the Codex session usage had changed. Both actual framebuffer images were
visually inspected. Service resumed ACKs afterward. These captures demonstrate
the default idle/wake path, not sustained animation or physical touch quality.

## Deferred sprint-end acceptance

Run these on the production build, with service port ownership coordinated
through the existing pause/resume API and screenshot helper. Keep physical
panel acceptance separate from framebuffer evidence.

- Feed an unchanged payload repeatedly for over 30 seconds: saver must activate.
- With a known due window at 0–99% used, remain on Console/Details beyond the
  timeout; also start from an active saver and confirm it wakes. Check deadline
  crossing without a new payload, and confirm unknown/100%-used windows do not
  block saving. Repeat with usage-change waking disabled.
- Change only seq, clock, age, reset countdown, activity elapsed time or MINT
  fields: saver remains active. Change quota percent, cost or token count:
  original dashboard wakes; another change restarts its full idle interval.
- Tap while asleep: same dashboard, then Details, Face, Images, Console; there
  must be four navigation stops and no preview title on the saver.
- Leave Face and Images selected for over 30 seconds: neither changes view.
- Build with Details wake disabled: changes cannot wake sleeping Details;
  manual input can. With Details saving disabled, it never enters the saver.
- Override each timeout separately and confirm independent behavior. Confirm
  elapsed subtraction around millis rollover, including a change near rollover.
- Build with saving disabled and Companion omitted; it must not require a
  Companion target. Active saving with an omitted target must fail compilation.
- Check portrait, framebuffer allocation fallback, physical taps and sustained
  animation/heap. These are pending until explicitly executed at sprint end.
