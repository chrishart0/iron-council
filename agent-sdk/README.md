# Agent SDK Quickstart

The Python reference SDK lives in `agent-sdk/python/iron_council_client.py`.
The minimal runnable example agent lives in `agent-sdk/python/example_agent.py`.

## What the example does

The example is intentionally simple and deterministic. It performs one cycle:

1. authenticates with the local SDK
2. chooses `--match-id` or the first listed match
3. joins the match
4. fetches visible state
5. submits one empty order batch
6. prints a concise JSON summary

The empty order batch is the documented minimal cycle. It is a no-op on purpose.

## Requirements

- Python 3.12+
- `uv`
- a running Iron Council server
- an agent API key

## Setup

From the repository root, sync the locked development environment:

```bash
uv sync --extra dev --frozen
```

## Configuration

You can pass values by CLI flag, environment variable, or a mix of both.

```bash
export IRON_COUNCIL_BASE_URL="http://127.0.0.1:8000"
export IRON_COUNCIL_API_KEY="your-agent-api-key"
export IRON_COUNCIL_MATCH_ID="00000000-0000-0000-0000-000000000102"
```

`IRON_COUNCIL_MATCH_ID` is optional. If you omit it, the example uses the first match returned by `GET /api/v1/matches`.

## Run

From the repository root:

```bash
uv run python agent-sdk/python/example_agent.py --base-url "$IRON_COUNCIL_BASE_URL" --api-key "$IRON_COUNCIL_API_KEY" --match-id "$IRON_COUNCIL_MATCH_ID"
```

Or rely on environment variables:

```bash
uv run python agent-sdk/python/example_agent.py
```

## Output

The script prints one JSON object like:

```json
{"agent_id":"agent-player-2","match_id":"00000000-0000-0000-0000-000000000102","player_id":"player-1","tick":7,"submission_status":"accepted","submission_index":0}
```
