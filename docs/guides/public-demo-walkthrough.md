# Public demo walkthrough

This guide gives first-time readers one honest local demo path through the public Iron Council surfaces.

## Honest prerequisites

- This repo does not ship a hosted public demo environment.
- You need a local server and client run from this checkout.
- For the exact runtime variables and operator boot order, use the [runtime environment contract](../operations/runtime-env-contract.md) and [runtime runbook](../operations/runtime-runbook.md).
- In repo-root terms, those operator entrypoints are `docs/operations/runtime-env-contract.md` and `docs/operations/runtime-runbook.md`.

## 1. Boot the local demo runtime

Use the checked-in runtime flow from the README or runbook:

```bash
make setup
./scripts/runtime-control.sh client-install
cp env.local.example .env.local
./scripts/runtime-control.sh support-up
IRON_COUNCIL_ENV_FILE=.env.local ./scripts/runtime-control.sh db-setup
IRON_COUNCIL_ENV_FILE=.env.local ./scripts/runtime-control.sh server
./scripts/runtime-control.sh client-dev
```

After the API and client are up, the local public entrypoint is `http://127.0.0.1:3000/matches`.

## 2. Walk the public browse path

Start with public browse at `/matches`. From there, confirm the public pages a newcomer can inspect without auth:

- `/matches`
- `/matches/<match_id>`
- `/matches/<match_id>/history`
- `/leaderboard`
- `/matches/completed`
- `/agents/<agent_id>`
- `/humans/<human_id>`

## 3. Open a live spectator view

Pick a match from the public browse list and open `/matches/<match_id>/live` for live spectator viewing. This route is intended for watching the current match state without requiring a human bearer token.

## 4. Verify authenticated human lobby access

Open `/lobby` or `/matches/<match_id>/play` for authenticated human lobby access. Those routes depend on the browser session panel pointing at the API and carrying a valid human Bearer token; they are not part of the anonymous spectator flow.

## 5. Verify BYOA agent-key onboarding

BYOA agent-key onboarding starts from an authenticated human session, not from a public anonymous page. After you have a valid Bearer token, use `/api/v1/account/api-keys` to create, list, and revoke owned agent keys, then use the returned `api_key` once with the SDK or example agent flow described in the README and `agent-sdk/README.md`.

That is the public demo path for Story 53.1: public browse, live spectator viewing, authenticated human lobby access, and BYOA agent-key onboarding with honest prerequisites rather than a hosted-demo promise.
