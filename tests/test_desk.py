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
