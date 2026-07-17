# ops/

Deployed to the mac-mini (`solberg.club`), not run from this repo. Kept here so
the dead-man's-switch is reviewable, diffable, and not one disk failure from
being lost.

| File | Deployed to |
|------|-------------|
| `icelandic-data-dms.sh` | `~/clawd/bin/icelandic-data-dms.sh` |
| `com.jokull.icelandic-data-dms.plist` | `~/Library/LaunchAgents/` |

The switch answers "is anyone still watching?" — it polls the age of the last
commit on the `health-history` branch and alerts via Telegram when observations
stop. It says nothing about whether the data sources are healthy; the workflow
already answers that, with detail.

See the "blind spot" section in `AGENTS.md` for the reasoning and the invariants
worth preserving.

## Redeploy

```bash
scp ops/icelandic-data-dms.sh solberg.club:~/clawd/bin/
scp ops/com.jokull.icelandic-data-dms.plist solberg.club:~/Library/LaunchAgents/
ssh solberg.club 'chmod +x ~/clawd/bin/icelandic-data-dms.sh && \
  launchctl unload ~/Library/LaunchAgents/com.jokull.icelandic-data-dms.plist 2>/dev/null; \
  launchctl load ~/Library/LaunchAgents/com.jokull.icelandic-data-dms.plist'
```

## Exercise it

An untested dead-man's-switch is decoration. Both thresholds are env-overridable:

```bash
ssh solberg.club 'MAX_AGE_HOURS=0 ~/clawd/bin/icelandic-data-dms.sh'   # forces a real Telegram alert
ssh solberg.club 'rm -f ~/clawd/state/icelandic-data-dms.last-alert'   # reset the cooldown
ssh solberg.club 'tail ~/clawd/logs/icelandic-data-dms.log'
```

`NODE_BIN` and `OPENCLAW_JS` are pinned to match `ai.openclaw.gateway.plist`.
If openclaw is upgraded and node moves, update both — the script fails loudly
and refuses to stamp its cooldown rather than going quietly deaf.
