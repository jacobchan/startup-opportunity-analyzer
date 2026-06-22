# r2-deliberation-loop Specification

## Purpose

Define the behavior of the Round 2 (R2) deliberation sub-rounds in the
deliberation engine. R2 turns the existing "issue" sub-round into a
complete debate loop by adding a mandatory "response" sub-round in which
every challenged agent must issue a verdict (accepted, rejected, or
modified) for each challenge it received, and have that verdict flow
into the final strategy report so downstream readers can see which
conclusions survived cross-challenge scrutiny.
## Requirements
### Requirement: Round 2 consists of an issue sub-round and a response sub-round

The deliberation engine MUST execute Round 2 in two distinct sub-rounds. R2-A is the existing "issue" sub-round (each participating agent may call the `challenge` tool up to 3 times to issue challenges). R2-B is a new "response" sub-round in which every agent that received at least one challenge during R2-A MUST be given a kickoff that exposes only the `respond` and `list_open_challenges` tool actions, and the agent MUST use the `respond` action to fill in a verdict for every challenge targeted at it.

#### Scenario: Agent received one challenge and responds
- **WHEN** agent `market_analyst` has exactly one unresolved challenge after R2-A
- **THEN** the engine MUST run a kickoff for `market_analyst` with only response-capable tools
- **AND** the engine MUST persist the `response` and `verdict` fields of that challenge in the `Challenge` table

#### Scenario: Agent received no challenges and skips R2-B
- **WHEN** agent `competitor_researcher` has zero unresolved challenges after R2-A
- **THEN** the engine MUST NOT run a kickoff for `competitor_researcher` in R2-B

### Requirement: Verdict values follow a fixed enumerated set

Each resolved challenge MUST have a `verdict` field set to one of `accepted`, `rejected`, `modified`, or `no_response`. A verdict of `accepted` means the target agent agrees the challenged claim is wrong and retracts it. A verdict of `rejected` means the target agent disagrees and stands by the claim. A verdict of `modified` means the target agent accepts the challenge but states a corrected version of the claim. A verdict of `no_response` MUST be assigned by the engine when R2-B completes without the target agent having called `respond` for that challenge.

#### Scenario: Engine marks unanswered challenges as no_response
- **WHEN** R2-B kickoff for `finance_analyst` finishes and at least one challenge targeting `finance_analyst` still has `response IS NULL`
- **THEN** the engine MUST set `verdict='no_response'` and `resolved_at=<now>` for each such challenge

#### Scenario: Verdict enum values are stable
- **WHEN** a response is recorded
- **THEN** the `verdict` column MUST be one of the four literals `accepted`, `rejected`, `modified`, `no_response`

### Requirement: R3 strategy report cites at least one accepted or modified challenge

The strategy advisor's prompt for R3 MUST include a "challenge disposition" block that groups every R2 challenge by its `verdict`. The `key_risks` field in the strategy report JSON MUST explicitly reference at least one challenge whose verdict is `accepted` or `modified`, citing its `challenge_id`.

#### Scenario: Strategy report contains a challenge_disposition block
- **WHEN** the R3 kickoff runs
- **THEN** the prompt extras MUST contain a JSON object with keys `accepted`, `rejected`, `modified`, `no_response`, each holding a list of `{challenge_id, claim, response}` entries

#### Scenario: Strategy report cites a modified challenge
- **WHEN** the final strategy report JSON is parsed
- **THEN** at least one string in `key_risks` MUST match the pattern `\[ch-[a-z0-9-]+\]` where the referenced id corresponds to a challenge with verdict in `accepted` or `modified`

### Requirement: R2-B state is checkpointed per challenge response

The engine MUST persist a checkpoint after every challenge is resolved in R2-B. The persisted `EngineState` MUST include the field `r2_resolved_challenge_ids: list[str]`. A resume from a `failed` or `paused` state in R2-B MUST continue from the first challenge that is still `response IS NULL` in the database, treating the database as the source of truth and re-deriving the in-memory resolved set on load.

#### Scenario: Resume continues from the first unresolved challenge
- **WHEN** the engine resumes a run whose persisted state is `round2` and the database has two unresolved challenges targeting `market_analyst`
- **THEN** the engine MUST run R2-B for `market_analyst` only once
- **AND** the engine MUST mark both unresolved challenges with verdicts from that single kickoff

#### Scenario: Idempotent resume does not re-respond
- **WHEN** the engine resumes a run and all challenges in the database already have `response IS NOT NULL`
- **THEN** the engine MUST skip R2-B entirely and proceed to R3

### Requirement: The challenge tool supports a response action without consuming the issue quota

The `ChallengeTool` MUST expose three actions: `challenge(target, claim, reason)`, `respond(challenge_id, response, verdict)`, and `list_open_challenges(target)`. Only the `challenge` action is constrained by the per-agent `max_challenges` limit. Calling `respond` or `list_open_challenges` MUST NOT increment or decrement the issue counter.

#### Scenario: Responding does not consume issue quota
- **WHEN** a `ChallengeTool` instance has `_count == max_challenges` and the agent calls `respond`
- **THEN** the tool MUST accept the response and persist it
- **AND** the tool MUST NOT raise a max-challenges error

#### Scenario: R2-B kickoff disables issue action
- **WHEN** R2-B constructs a `ChallengeTool` for a target agent
- **THEN** the tool MUST be configured with `max_challenges=0` so that any attempt by the LLM to call `challenge` raises an explicit error

