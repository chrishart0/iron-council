# Story 40.2 Rating Settlement and Profile History Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Settle completed matches exactly once into durable rating/history updates so leaderboard and agent profile reads show finalized outcomes instead of provisional placeholders.

**Architecture:** Keep the change local to the existing DB-backed completion/read path. Add one explicit settlement ledger/table plus a tiny settlement module that computes deterministic per-player outcomes from the persisted completed match, applies rating/history updates transactionally, and lets read models derive finalized leaderboard/profile values from durable rows rather than ad hoc completed-match scans.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Alembic-style migration tooling already in repo, Pydantic API models, pytest, real-process smoke/API tests, uv, make.

---

### Task 1: Add a durable settlement ledger schema

**Objective:** Create the smallest persistence surface that records one finalized settlement per player per completed match and makes duplicate application impossible.

**Files:**
- Modify: `server/db/models.py`
- Modify: `server/db/tooling.py` and/or existing migration/schema bootstrap files used by `python -m server.db.tooling setup`
- Test: `tests/test_db_registry.py`

**Step 1: Write failing schema/behavior test**

Add a DB-focused test proving the repo can persist a settlement row with:
- `match_id`
- `player_id`
- `result` (`win`, `loss`, or `draw`)
- `elo_before`
- `elo_after`
- `elo_delta`
- `alliance_tenure_ticks`
- `territory_share`

and that the unique key on `(match_id, player_id)` rejects duplicate settlement rows for the same completed match.

Use a shape like:

```python
assert settlement.result == "win"
assert settlement.elo_before == 1190
assert settlement.elo_after == 1208
assert settlement.elo_delta == 18
```

**Step 2: Run test to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'settlement and unique'
```

Expected: FAIL because no settlement table/model exists yet.

**Step 3: Write minimal implementation**

Add a new SQLAlchemy model, for example:

```python
SETTLEMENT_RESULTS = ("win", "loss", "draw")

class MatchSettlement(Base):
    __tablename__ = "match_settlements"

    id: Mapped[Any] = mapped_column(uuid_type, primary_key=True)
    match_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("matches.id"), nullable=False)
    player_id: Mapped[Any] = mapped_column(uuid_type, sa.ForeignKey("players.id"), nullable=False)
    result: Mapped[str] = mapped_column(enum_values(*SETTLEMENT_RESULTS), nullable=False)
    elo_before: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    elo_after: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    elo_delta: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    alliance_tenure_ticks: Mapped[int] = mapped_column(sa.Integer(), nullable=False)
    territory_share: Mapped[float] = mapped_column(sa.Float(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (sa.UniqueConstraint("match_id", "player_id"),)
```

Update the DB bootstrap/migration path so fresh DBs create the new table.

**Step 4: Run test to verify pass**

Re-run the same focused test command. Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/models.py server/db/tooling.py tests/test_db_registry.py
git commit -m "feat: add durable match settlement ledger"
```

### Task 2: Pin the deterministic settlement formula in tests

**Objective:** Lock the behavior contract before implementing the settlement writer.

**Files:**
- Modify: `tests/test_db_registry.py`
- Possibly inspect: `tests/support.py`

**Step 1: Write failing tests**

Add tests for one completed-match fixture that prove:
- winners gain rating, losers lose rating
- alliance tenure changes winner gain magnitude
- territory contribution changes winner gain magnitude
- no winner alliance produces draws with zero-sum or no-op deltas, whichever contract you choose explicitly and document
- duplicate settlement invocation is idempotent

Use an explicit fixture where the winning alliance has two members with different joined ticks and different city counts so the weighting is observable.

Example assertion shape:

```python
assert settlement_by_name["Arthur"].result == "win"
assert settlement_by_name["Arthur"].elo_delta > settlement_by_name["Morgana"].elo_delta
assert settlement_by_name["Gawain"].result == "loss"
assert settlement_by_name["Gawain"].elo_delta < 0
```

**Step 2: Run test to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'rating_settlement or idempotent_settlement'
```

Expected: FAIL because no settlement writer exists.

**Step 3: Keep the formula explicit in the test docstring/comments**

Document the simplest deterministic formula that fits `core-plan.md` section 8.2. Example:

```python
# base swing = 24
# winner score = 1.0, loser score = 0.0, draw = 0.5
# winner gain multiplier = 0.5 + 0.5 * tenure_share
# winner gain multiplier *= 0.5 + 0.5 * territory_share
```

Do not hide the formula in a magic helper without tests pinning expected outputs.

**Step 4: Re-run once implementation exists**

Use the same command from Step 2 after the settlement writer lands.

**Step 5: Commit**

```bash
git add tests/test_db_registry.py tests/support.py
git commit -m "test: pin deterministic rating settlement behavior"
```

### Task 3: Implement settlement writes on completed matches

**Objective:** Apply settlement rows and durable rating/history updates exactly once for DB-backed completed matches.

**Files:**
- Create: `server/db/settlement.py`
- Modify: `server/db/tick_persistence.py` or the nearest completed-match persistence seam
- Modify: `server/db/models.py`
- Test: `tests/test_db_registry.py`

**Step 1: Write the minimal settlement module**

Create a small explicit module with functions like:

```python
def settle_completed_match(*, session: Session, match_id: str) -> list[MatchSettlement]:
    ...

def compute_player_settlement(... ) -> PlayerSettlementDraft:
    ...
```

Keep it boring: load one completed match, load its players/alliance rows, compute results deterministically, insert one settlement row per player if none exist, and update `players.elo_rating` to `elo_after`.

**Step 2: Hook settlement into the completion seam**

After the terminal match row is persisted successfully, call settlement inside the same database transaction or in a tightly coupled follow-up transaction that preserves idempotency.

Preferred shape:

```python
if match.status == MatchStatus.COMPLETED.value:
    apply_match_settlement(session=session, match=match)
```

Guard with the settlement ledger instead of a mutable boolean flag.

**Step 3: Update profile history derivation**

Where DB-backed agent profiles are hydrated, replace the placeholder history/rating construction with values aggregated from settled rows for that player identity. Keep seeded/in-memory fallback behavior unchanged.

Example target shape:

```python
AgentProfileResponse(
    ...,
    rating=AgentProfileRating(elo=final_elo, provisional=matches_played == 0),
    history=AgentProfileHistory(
        matches_played=matches_played,
        wins=wins,
        losses=losses,
        draws=draws,
    ),
)
```

**Step 4: Run focused tests to verify pass**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'rating_settlement or idempotent_settlement or agent_profile'
```

Expected: PASS.

**Step 5: Commit**

```bash
git add server/db/settlement.py server/db/tick_persistence.py server/db/models.py tests/test_db_registry.py
git commit -m "feat: settle completed matches into rating history"
```

### Task 4: Finalize leaderboard/profile contract tests at the API boundary

**Objective:** Prove public leaderboard and authenticated/public agent-profile routes now expose finalized durable results.

**Files:**
- Modify: `tests/api/test_agent_api.py`
- Modify: `tests/api/test_agent_process_api.py`
- Modify: `tests/e2e/test_api_smoke.py`
- Possibly inspect: `server/db/public_reads.py`, `server/db/public_read_assembly.py`, `server/db/identity_hydration.py`

**Step 1: Write failing API-boundary assertions**

Tighten or add tests asserting that DB-backed responses now show:
- finalized ELO values
- `provisional=False` once settled matches exist
- `matches_played`, `wins`, `losses`, `draws` coming from durable settlement results
- leaderboard ordering using finalized ELO, not stale per-match player rows

Use explicit response assertions such as:

```python
assert response.json()["leaderboard"][0] == {
    "rank": 1,
    "display_name": "Arthur",
    "competitor_kind": "human",
    "elo": 1220,
    "provisional": False,
    "matches_played": 1,
    "wins": 1,
    "losses": 0,
    "draws": 0,
}
```

**Step 2: Run focused tests to verify failure**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'leaderboard or profile'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_process_api.py -k profile
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'leaderboard or profile'
```

Expected: FAIL where the code still returns provisional placeholder values.

**Step 3: Implement the smallest read-model fixes**

Refactor read assembly only as needed so:
- public leaderboard aggregates settled rows by stable competitor identity
- DB-backed agent profiles aggregate settlements by stable competitor identity
- existing route signatures stay unchanged

Do not introduce a generic ranking framework.

**Step 4: Run focused tests to verify pass**

Re-run the same commands from Step 2. Expected: PASS.

**Step 5: Commit**

```bash
git add tests/api/test_agent_api.py tests/api/test_agent_process_api.py tests/e2e/test_api_smoke.py server/db/public_reads.py server/db/public_read_assembly.py server/db/identity_hydration.py
git commit -m "feat: expose finalized rating history in reads"
```

### Task 5: Full verification and simplification pass

**Objective:** Re-run the strongest repo-managed checks, then trim any unnecessary abstraction.

**Files:**
- Review entire Story 40.2 diff
- Update: `_bmad-output/implementation-artifacts/40-2-add-deterministic-post-match-rating-settlement-and-profile-history-updates.md`
- Update: `_bmad-output/implementation-artifacts/sprint-status.yaml`

**Step 1: Run focused story verification**

Run:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'settlement or leaderboard or agent_profile'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'leaderboard or profile'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_process_api.py -k profile
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'leaderboard or profile'
```

**Step 2: Run strongest practical repo-managed gate**

Run:

```bash
source .venv/bin/activate && make quality
```

Expected: PASS.

**Step 3: Perform simplification review**

Inspect:

```bash
git diff --stat HEAD~4..HEAD
```

Then confirm:
- no new framework/service layer was added
- the formula is explicit and local
- the settlement guard is the DB unique key, not duplicated runtime flags
- seeded/in-memory profile behavior stayed intact

**Step 4: Update BMAD closeout artifacts**

Mark Story 40.2 complete, record exact verification commands/results, and set the next story.

**Step 5: Final commit**

```bash
git add -A
git commit -m "feat: finalize post-match rating settlement"
```

## Parallelism / sequencing note

This story should remain sequential. The schema, settlement writer, leaderboard aggregation, and DB-backed profile hydration all touch the same rating/history contract and would create merge/conflict risk if split across parallel workers.

## Validation summary

Primary commands:

```bash
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/test_db_registry.py -k 'settlement or leaderboard or agent_profile'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_api.py -k 'leaderboard or profile'
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/api/test_agent_process_api.py -k profile
uv run pytest --override-ini addopts='-q --strict-config --strict-markers' tests/e2e/test_api_smoke.py -k 'leaderboard or profile'
source .venv/bin/activate && make quality
```

## Risks / pitfalls

- Do not double-apply settlement on retries or on repeated completed-match reads.
- Do not key leaderboard/profile aggregation by display name; use stable human/api-key identity.
- Do not silently overwrite seeded/in-memory placeholder profile behavior for non-DB paths.
- Keep the rating formula explicit and deterministic; avoid a premature ranking engine.
- If the final formula materially sharpens the source-of-truth semantics, update the canonical docs and BMAD story notes in the same change set.
