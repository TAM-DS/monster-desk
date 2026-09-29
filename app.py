from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from monster_desk.desk import Desk, DeskRefusal

st.set_page_config(page_title="Monster Desk | Governed Paper Trading", layout="wide")
st.title("MONSTER DESK")
st.caption("Governed paper-trading console · Four seats · No broker connection · No autonomous execution")
st.markdown("**Research proposes. Risk binds. Execution submits only the bound ticket. Surveillance can halt the desk.**")

if "desk" not in st.session_state:
    st.session_state.desk = Desk()

desk: Desk = st.session_state.desk

if desk.halted:
    st.error("DESK HALTED — proposals, risk binding, and submissions are blocked for this session.")
elif desk.fill is not None:
    st.success("PAPER FILL RECORDED — this ticket cannot be submitted again.")
elif desk.bound is not None:
    st.info("RISK BOUND — only this ticket digest can reach simulated execution.")
else:
    st.info("AWAITING RISK BINDING — execution is not authorized.")

r, k, x, a = st.columns(4)

with r:
    st.subheader("1 · Research")
    st.write("May propose. Cannot send an order.")
    symbol = st.selectbox("Symbol", ["AAPL", "MSFT", "NVDA"])
    side = st.selectbox("Side", ["BUY", "SELL"])
    qty = st.text_input("Quantity", "100")
    px = st.text_input("Reference price", "180.00")
    thesis = st.text_area("Thesis", "Paper add after dip. Not a live view.")
    if st.button("Propose ticket"):
        try:
            t = desk.research_propose(
                portfolio="book-alpha",
                symbol=symbol,
                side=side,
                quantity=qty,
                reference_price=px,
                thesis=thesis,
                grounding="fixture:nbbo",
            )
            st.success(f"Proposed digest `{t.digest()[:16]}\u2026`")
        except DeskRefusal as exc:
            st.error(f"DENIED: {exc}")
    if desk.ticket:
        st.code(
            f"{desk.ticket.side} {desk.ticket.quantity} {desk.ticket.symbol}\n"
            f"ref {desk.ticket.reference_price}  notional {desk.ticket.notional}\n"
            f"{desk.ticket.digest()}"
        )

with k:
    st.subheader("2 · Risk")
    st.write("Human-operated demo approval: binds the proposed digest without rewriting its terms.")
    if st.button("Bind ticket"):
        try:
            b = desk.risk_bind("Risk")
            st.success(f"Bound `{b.ticket_digest[:16]}\u2026`")
        except DeskRefusal as exc:
            st.error(f"DENIED: {exc}")
    if desk.bound:
        st.info("Ticket is frozen. Execution may only submit this digest.")

with x:
    st.subheader("3 · Execution")
    st.write("May submit the frozen ticket. May not change it.")
    claimed = st.text_input(
        "Claimed digest",
        value=desk.bound.ticket_digest if desk.bound else "",
        key=f"claimed-{desk.bound.ticket_digest if desk.bound else 'unbound'}",
    )
    obs = st.text_input("Observed price", "180.10")
    cheat = st.checkbox("Cheat: change symbol to NVDA at send")
    if st.button("Submit (simulate fill)"):
        try:
            fill = desk.execution_submit(
                claimed_digest=claimed,
                observed_price=obs,
                mutate_symbol="NVDA" if cheat else None,
            )
            st.success(f"[SIMULATED] fill @ {fill.observed_price} — not a street fill")
        except DeskRefusal as exc:
            st.error(f"DENIED: {exc}")

with a:
    st.subheader("4 · Surveillance")
    st.write("Halt blocks new proposals, binding, and submissions. Existing session events remain visible.")
    if st.button("Halt desk"):
        try:
            desk.surveillance_halt("Operator halt — no further actions this session.")
            st.warning("Desk halted. All new desk actions are blocked.")
        except DeskRefusal as exc:
            st.error(f"DENIED: {exc}")
    if st.button("Reset demo session"):
        st.session_state.desk = Desk()
        st.rerun()
    st.caption("Reset creates a new in-memory demo session; the previous session audit is not preserved.")

st.divider()
st.subheader("Audit tail")
st.dataframe(list(reversed(desk.events)), use_container_width=True, hide_index=True)
st.caption(
    "Paper only. Durable worker leases, process-death tests, and compensation tickets live in "
    "monster-heavy. This standalone, in-memory console demonstrates its separation-of-duties design; "
    "it is not connected to the durable engine. Session reset clears the local audit."
)
