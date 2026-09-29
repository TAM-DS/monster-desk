from decimal import Decimal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from monster_desk.desk import Desk, DeskRefusal


def _propose(desk: Desk, qty="100", px="180") -> None:
    desk.research_propose(
        portfolio="book-alpha",
        symbol="AAPL",
        side="BUY",
        quantity=qty,
        reference_price=px,
        thesis="Liquidity add after dip; paper only.",
        grounding="fixture:nbbo:AAPL",
    )


def test_execution_cannot_run_unbound() -> None:
    desk = Desk()
    _propose(desk)
    with pytest.raises(DeskRefusal, match="TicketNotBound"):
        desk.execution_submit(claimed_digest=desk.ticket.digest(), observed_price="180")


def test_execution_cannot_mutate_bound_ticket() -> None:
    desk = Desk()
    _propose(desk)
    desk.risk_bind("Risk")
    with pytest.raises(DeskRefusal, match="ExecutionMayNotMutateTicket"):
        desk.execution_submit(
            claimed_digest=desk.bound.ticket_digest,
            observed_price="180",
            mutate_symbol="NVDA",
        )


def test_wrong_digest_is_refused() -> None:
    desk = Desk()
    _propose(desk)
    desk.risk_bind("Risk")
    with pytest.raises(DeskRefusal, match="FrozenTicketRequired"):
        desk.execution_submit(claimed_digest="0" * 64, observed_price="180")


def test_happy_path_is_simulated() -> None:
    desk = Desk()
    _propose(desk)
    desk.risk_bind("Risk")
    fill = desk.execution_submit(
        claimed_digest=desk.bound.ticket_digest,
        observed_price="180.10",
    )
    assert fill.simulated is True
    assert fill.ticket_digest == desk.ticket.digest()
    assert desk.ticket.notional == Decimal("18000")


def test_notional_limit() -> None:
    desk = Desk()
    with pytest.raises(DeskRefusal, match="OrderNotionalExceeded"):
        _propose(desk, qty="2000", px="180")
        desk.risk_bind("Risk")


def test_surveillance_halt_blocks_execution_and_preserves_events() -> None:
    desk = Desk()
    _propose(desk)
    desk.risk_bind("Risk")
    prior_events = len(desk.events)
    desk.surveillance_halt("Operator halt")
    assert desk.halted is True
    assert len(desk.events) == prior_events + 1
    with pytest.raises(DeskRefusal, match="DeskHalted"):
        desk.execution_submit(claimed_digest=desk.bound.ticket_digest, observed_price="180")
    assert desk.fill is None
    assert desk.events[-1]["ok"] is False
    assert desk.events[-1]["detail"] == "DENIED: DeskHalted"
    assert desk.events[-2]["action"] == "halt"


def test_halt_blocks_research_and_risk_operations() -> None:
    desk = Desk()
    desk.surveillance_halt("Operator halt")
    with pytest.raises(DeskRefusal, match="DeskHalted"):
        _propose(desk)
    assert desk.ticket is None
    with pytest.raises(DeskRefusal, match="DeskHalted"):
        desk.risk_bind("Risk")


def test_second_simulated_fill_denied_and_first_fill_preserved() -> None:
    desk = Desk()
    _propose(desk)
    desk.risk_bind("Risk")
    first = desk.execution_submit(claimed_digest=desk.bound.ticket_digest, observed_price="180.10")
    with pytest.raises(DeskRefusal, match="TicketAlreadyFilled"):
        desk.execution_submit(claimed_digest=desk.bound.ticket_digest, observed_price="180.11")
    assert desk.fill is first
    assert len([event for event in desk.events if event["action"] == "simulate_fill"]) == 1
    assert desk.events[-1]["ok"] is False


def test_repeated_halt_denied_without_clearing_history() -> None:
    desk = Desk()
    desk.surveillance_halt("Operator halt")
    with pytest.raises(DeskRefusal, match="DeskAlreadyHalted"):
        desk.surveillance_halt("Attempted second halt")
    assert desk.halted is True
    assert desk.events[0]["ok"] is True
    assert desk.events[-1]["ok"] is False
