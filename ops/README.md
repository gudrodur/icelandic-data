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

## Upgrading openclaw — read this first

`openclaw update` from 2026.6.1 → 2026.7.1 **fails**, and fails messily. Tried
2026-07-17; recovered. Don't repeat it blind.

**Blocker:** 2026.7.1 requires node `>=22.22.3 <23`, `>=24.15.0 <25`, or
`>=25.9.0`. The mini has v18.20.8, v22.22.0, v24.12.0, v24.14.0 — *none* qualify
(v24.14.0 misses by one patch). The build dies in `tsdown`.

**Why the auto-rollback is not enough:** it restores tracked source, but `dist/`
and `node_modules` are git-ignored, so the half-built 2026.7.1 artifacts survive.
You end up with 6.1 source and a 7.1 launcher, and *every* openclaw command —
including `openclaw doctor` — is then refused by 7.1's engine gate. The repair
tool is behind the thing that is broken. The gateway keeps running only because
it is an already-started process; the next restart would fail.

**Recovery** (verified):

```bash
ssh solberg.club
cd ~/openclaw
export PATH=~/.local/share/fnm/node-versions/v24.12.0/installation/bin:$PATH
corepack pnpm install --frozen-lockfile   # was already up to date; deps were fine
node scripts/build-all.mjs                # rebuilds dist/ from 6.1 -> ~135s
launchctl kickstart -k gui/501/ai.openclaw.gateway   # prove it restarts
```

Then re-verify, in order: `openclaw --version`, `openclaw cron list` (5 jobs,
4 explicit telegram routes), and force the DMS alert path with
`MAX_AGE_HOURS=0`. A gateway that has not been restarted is unproven.

**To actually upgrade:** `fnm install 24.15.0` (or 25.9+) first, repoint
`ai.openclaw.gateway.plist` at it, then `openclaw update`. Afterwards update
`NODE_BIN` in `icelandic-data-dms.sh` to match, or the switch goes deaf.
