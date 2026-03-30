# Story 21.1: Add an authenticated match lobby creation endpoint

Status: drafted

## Story

As an authenticated agent competitor,
I want to create a new match lobby through the API,
So that I can spin up a browseable game with valid public settings and immediately occupy the creator slot without relying on seeded fixtures.

## Acceptance Criteria

1. Given an authenticated caller submits a supported lobby configuration, when `POST /api/v1/matches` is called, then the server creates a new lobby with validated public config, canonical initialized state, and creator membership.
2. Given DB-backed mode is active, when the lobby is created, then the server persists the `matches` row and creator `players` row in one coherent transaction and returns compact lobby metadata suitable for browse/detail surfaces.
3. Given the new lobby is public and joinable, when the existing browse or detail routes are called, then the lobby appears immediately with correct slot counts and without leaking private auth material.
4. Given invalid config or unsupported map input, when the create route is called, then the server returns structured validation/domain errors and does not persist a partial lobby.
5. Given the story ships, when focused unit/API/e2e and SDK checks run, then the authenticated creation contract is proven from the public boundary and the repo quality gate passes.

## Tasks / Subtasks

- [ ] Add narrow authenticated create-lobby request/response models and domain validation rules. (AC: 1, 4)
- [ ] Add a DB-backed lobby creation helper that initializes canonical state and persists match + creator membership atomically. (AC: 1, 2, 4)
- [ ] Expose `POST /api/v1/matches` through the authenticated API, keeping the returned payload compact and public-facing. (AC: 1, 2, 3)
- [ ] Add focused DB/API/e2e/SDK coverage for success, validation failures, browse/detail visibility, and creator membership. (AC: 3, 4, 5)
- [ ] Update BMAD/source docs, run review + simplification, and pass `make quality`. (AC: 5)

## Dev Notes

- Keep the contract deliberately small: validated map/config inputs, compact public match metadata in the response, and the creator `player_id` for follow-on agent actions.
- Reuse `server.match_initialization` for canonical starting state instead of inventing a second bootstrap path.
- In this repo phase, prefer authenticated agent-driven lobby creation over speculative human-auth flows; do not introduce Supabase JWT plumbing in this story.
- The created lobby must remain compatible with existing public browse/detail reads and the authenticated join flow.

## Implementation Plan

- Plan file: `docs/plans/2026-03-30-story-21-1-authenticated-match-lobby-creation.md`
- Parallelism assessment: sequential implementation because API models, persistence, route wiring, and verification all share one contract seam; spec and quality reviews run after the worker finishes.
- Verification target: focused RED/GREEN DB/API/e2e/SDK commands, then `make quality`.
