from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from monster_desk.desk import Desk, DeskRefusal

st.set_page_config(page_title="Monster Desk", layout="wide")
st.title("Monster Desk")
st.caption(
    "Companion console to TAM-DS/monster-heavy. "
    "I was a trader. I did not build agents that trade. I built the desk that will not let them."
)

if "desk" not in st.session_state:
    st.session_state.desk = Desk()

desk: Desk = st.session_state.desk

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
    st.write("Binds the digest. Cannot rewrite terms.")
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
    st.write("Halt is a new event. It does not erase history.")
    if st.button("Halt desk"):
        desk.surveillance_halt("Operator halt — no further submits this session.")
        st.warning("Halt recorded.")
    if st.button("Reset session"):
        st.session_state.desk = Desk()
        st.rerun()

st.divider()
st.subheader("Audit tail")
st.dataframe(list(reversed(desk.events)), use_container_width=True, hide_index=True)
st.caption(
    "Paper only. Durable worker leases, process-death tests, and compensation tickets live in "
    "monster-heavy. This console is the seat layout over that contract."
)
