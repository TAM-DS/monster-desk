# Monster Desk | Interview demonstration (5–8 minutes)

## Open in one sentence

> I was a trader. I didn't build agents that trade autonomously; I built a desk that demonstrates why they should not have unrestricted execution authority.

## The business problem

A research signal is not an order. Before a trading idea can become an executable ticket, somebody must validate its terms and limits, and the execution function must not be able to alter what was approved.

The point of Monster Desk is to make that separation tangible in a paper-only, four-seat console.

## Demonstrate the boundary

1. **Research:** Propose a paper ticket for `BUY 100 AAPL`. Point to its immutable terms and digest.
2. **Execution before Risk:** Try to submit it. Show `TicketNotBound`.
3. **Risk:** Human operator clicks **Bind ticket**. Explain the notional and quantity checks and the digest that is bound.
4. **Execution mutation:** Select **Cheat: change symbol to NVDA at send**. Show `ExecutionMayNotMutateTicket`.
5. **Correct submission:** Submit the unchanged ticket. Show the explicit `[SIMULATED]` result, then try again and show `TicketAlreadyFilled`.
6. **Surveillance:** Halt a fresh session before execution, demonstrate `DeskHalted`, and inspect the in-session audit tail.

If time is short, show steps 1–5 and explain the halt test.

## What is implemented here versus in Monster Heavy?

**Monster Desk:** standalone Streamlit console; immutable ticket and SHA-256 digest; human-operated Risk binding; allowed-symbol, notional, quantity and price-drift checks; denial of altered/unbound/mismatched/repeated execution; enforceable session-scoped halt; in-memory events; simulated paper fills.

**Monster Heavy:** separate durable engine with execution-time policy checks, PostgreSQL leases, worker-failure behavior and compensation as a new ticket. Monster Desk does **not** integrate directly with the Heavy runtime or inherit its durability.

Don't describe session-scoped duplicate protection as cross-process idempotency. Don't describe the demo UI's Risk button as authenticated approval.

## Questions worth anticipating

**Why not allow an autonomous agent to submit directly?**

Research and execution have different authorities. A proposal should carry evidence and fixed terms; approval must bind those terms; execution must check that it received the same ticket. A fluent model cannot substitute for that boundary.

**Why a digest?**

The digest gives the proposed ticket a concrete identity. A changed symbol or size produces different terms, and the execution path is restricted to the digest Risk actually bound. The separate mutation check refuses even an attempted change at submit time.

**What happens if the worker dies or two workers race?**

This console does not attempt to solve that problem. Monster Heavy is where durable leases and recovery logic live. Here, the goal is to make each role's authority visible in an interview.

**What happens when Surveillance halts the desk?**

The halt is now enforced by the desk methods for proposals, Risk binding and execution. Existing events remain in the active session. Reset deliberately starts a new in-memory demonstration and discards that local history.

**Is this a live trading system?**

No. It uses fixture grounding and simulated paper fills, with no broker connectivity, live market feed, authenticated role enforcement or persistent audit service.

## Close

> My architectural principle is that a system's ability to propose an action does not give it authority to execute that action. Monster Desk shows the separation of duties; Monster Heavy demonstrates the deeper durability and recovery controls needed when execution processes fail.

Then stop. Let the interviewer ask which boundary they want to inspect.
