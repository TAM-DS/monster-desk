# MONSTER DESK | Governed Paper-Trading Console

**The research seat can propose a trade. It cannot send one.**

> I was a trader. I did not build agents that trade. I built the desk that will not let them.

Monster Desk is a standalone, human-operated Streamlit demonstration of the separation-of-duties design behind [Monster Heavy](https://github.com/TAM-DS/monster-heavy). It makes a trading control visible: **Research proposes a ticket, Risk binds its exact terms, Execution may submit only that bound ticket, and Surveillance can halt the desk.**

The outcome is always **paper-only**. There is no broker connection, live order, real market-data feed, or autonomous trading.

[Run the demo](#run-the-demo) · [See the four seats](#four-seats-four-distinct-authorities) · [Review the tests](#validation-and-scope)

## The moment that matters

Research proposes a paper ticket:

```text
BUY 100 AAPL @ reference 180.00
```

Execution tries to submit before Risk has bound the ticket:

```text
DENIED: TicketNotBound
```

A human operator clicks **Bind ticket** in the Risk seat. The application binds the SHA-256 digest of the frozen ticket terms. Execution then attempts to change the symbol at send time:

```text
DENIED: ExecutionMayNotMutateTicket
```

The unchanged, bound ticket can reach a **simulated** fill only when the supplied digest matches and the execution-time checks pass. A second submission of that ticket is denied. A Surveillance halt blocks further desk operations.

**A proposed trade is not an approved ticket. An approved ticket is not permission to change its terms. A simulated fill is not a street fill.**

## Four seats, four distinct authorities

| Seat | What it does | Boundary enforced in this demo |
| --- | --- | --- |
| **Research** | Creates one immutable paper-trade proposal per session. | Cannot directly submit an order or revise an existing ticket. |
| **Risk** | Human-operated binding of the ticket digest after notional and quantity checks. | Cannot silently modify the proposed terms during binding. |
| **Execution** | Submits the matching bound ticket for a simulated fill, subject to price-drift checks. | Cannot execute an unbound, altered, mismatched, previously filled, or halted ticket. |
| **Surveillance** | Records a halt and blocks subsequent proposals, binding, and submissions. | Cannot undo previous events in the active session; a separate reset starts a new, empty demo session. |

The seats are workflow roles in a local demonstration, **not authenticated user accounts or production role-based access control**. Risk binding is a human UI action, not an independently verified approval identity.

## See the desk

These screenshots show the running console. They were captured before the latest halt and duplicate-submission safeguards, which are covered in code and tests.

**01 · Risk binds; Execution simulates the fill**

![Bound ticket and simulated fill](docs/screenshots/01-ticket-bind.png)

**02 · An altered ticket is denied**

![Execution may not mutate ticket](docs/screenshots/02-monster-desk-research.png)

**03 · The audit tail records success and refusal**

![Audit tail with rejected mutated submission](docs/screenshots/03-audit-monster-desk.png)

## The 90-second demonstration

1. In **Research**, propose `BUY 100 AAPL`.
2. In **Execution**, submit before Risk binding. Observe `DENIED: TicketNotBound`.
3. In **Risk**, click **Bind ticket**. The exact proposal digest is now bound.
4. In **Execution**, select **Cheat: change symbol to NVDA at send** and submit. Observe `DENIED: ExecutionMayNotMutateTicket`.
5. Uncheck **Cheat** and submit the correct bound digest. Observe a `[SIMULATED]` fill, explicitly labeled **not a street fill**.
6. Submit again. Observe `DENIED: TicketAlreadyFilled`.
7. In **Surveillance**, click **Halt desk**. Further proposals, binding, and submissions are rejected with `DeskHalted`. Inspect the in-session audit tail.

For a separate halt-before-fill demonstration, select **Reset demo session**, propose and bind a fresh ticket, then halt before submitting. Reset intentionally discards the previous in-memory session and its local event list.

## Architecture: bind the decision, constrain execution

```text
Research seat
  |
  v
Immutable Ticket (symbol, side, size, reference, thesis, grounding)
  |
  v
SHA-256 ticket digest
  |
  v
Risk seat (human clicks Bind)
  |   check notional / quantity
  v
BoundTicket (frozen digest)
  |
  v
Execution seat
  |   require bound ticket
  |   refuse term mutation
  |   match claimed digest
  |   check observed-price drift
  |   refuse duplicate simulated fill
  |   refuse while halted
  v
PaperFill [SIMULATED]
  |
  v
In-memory session event log

Surveillance seat -- halt --> blocks further desk operations
```

The immutable `Ticket` includes the proposal terms and grounding in its digest. Risk binds those terms; Execution cannot replace them with a different symbol, side, or quantity at submit time. The demo also enforces an allowed-symbol list, notional and quantity limits, and a reference-price drift threshold.

The halt and duplicate-fill controls operate **within the current Streamlit session**. They are not distributed locks and do not replace Monster Heavy's durable concurrency and recovery protections.

## Validation and scope

The tests in [`tests/test_desk.py`](tests/test_desk.py) cover:

- Unbound execution is denied.
- Attempted mutation of a bound ticket is denied.
- A mismatched digest is rejected.
- An authorized path produces a **simulated** fill with the original ticket digest.
- An over-limit notional is refused.
- A Surveillance halt prevents execution, research, and Risk binding.
- A second simulated fill is refused without overwriting the first.
- Repeated halt attempts are refused without clearing prior session events.

These are focused behavior tests, not evidence of production trading safety or an independent security assessment.

**In scope:** paper-only proposal, human-operated binding, execution checks, session-scoped halt, single-use simulated fill, and visible local event history.

**Out of scope:** a live order-management system, broker connectivity, market-data validation, authenticated traders, durable audit retention, cross-process idempotency, and production compliance attestations.

## Relationship to Monster Heavy

| Monster Heavy | Monster Desk |
| --- | --- |
| Durable governed paper-trading engine | Standalone, in-memory four-seat teaching and demo console |
| Frozen proposals, approval and execution-time policy checks | Visible Research → Risk → Execution → Surveillance roles |
| PostgreSQL lease and worker-death recovery | Session-scoped duplicate and halt protections |
| Compensation recorded as a new ticket | Refusal and simulated-fill events in a local session log |

**Monster Desk does not call Monster Heavy's runtime.** It illustrates the same control philosophy through a smaller implementation. Durable leases, process-death tests, and compensation behavior belong to Monster Heavy; they are not claims about this console.

## Run the demo

```bash
git clone https://github.com/TAM-DS/monster-desk.git
cd monster-desk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -q
streamlit run app.py
```

Open the local URL printed by Streamlit (typically `http://localhost:8501`).

**Interview takeaway:** the person—or agent—with a trading idea does not automatically have authority to execute it. Monster Desk makes that boundary visible; Monster Heavy addresses its durability under failure.
