from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
import json


class DeskRefusal(ValueError):
    """Stable reason code. Not a model apology."""


ALLOWED_SYMBOLS = ("AAPL", "MSFT", "NVDA")
MAX_NOTIONAL = Decimal("250000")
MAX_QTY = Decimal("2000")
MAX_DRIFT = Decimal("0.02")


def _now() -> datetime:
    return datetime.now(UTC)


def _digest(obj: dict) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(blob.encode()).hexdigest()


@dataclass(frozen=True)
class Ticket:
    portfolio: str
    symbol: str
    side: str
    quantity: Decimal
    reference_price: Decimal
    thesis: str
    grounding: str

    def __post_init__(self) -> None:
        if self.side not in ("BUY", "SELL"):
            raise DeskRefusal("InvalidSide")
        if self.symbol not in ALLOWED_SYMBOLS:
            raise DeskRefusal("DisallowedSymbol")
        if self.quantity <= 0 or self.reference_price <= 0:
            raise DeskRefusal("ExpectedPositiveDecimal")

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.reference_price

    def payload(self) -> dict:
        return {
            "portfolio": self.portfolio,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": str(self.quantity),
            "reference_price": str(self.reference_price),
            "thesis": self.thesis,
            "grounding": self.grounding,
        }

    def digest(self) -> str:
        return _digest(self.payload())


@dataclass
class BoundTicket:
    ticket: Ticket
    ticket_digest: str
    risk_actor: str
    bound_at: datetime
    limit_notional: Decimal = MAX_NOTIONAL

    def __post_init__(self) -> None:
        if self.ticket.digest() != self.ticket_digest:
            raise DeskRefusal("TicketDigestMismatch")
        if self.ticket.notional > self.limit_notional:
            raise DeskRefusal("OrderNotionalExceeded")
        if self.ticket.quantity > MAX_QTY:
            raise DeskRefusal("PositionLimitExceeded")


@dataclass
class PaperFill:
    bound_digest: str
    ticket_digest: str
    observed_price: Decimal
    simulated: bool = True


@dataclass
class Desk:
    """In-process desk. Durable leases live in monster-heavy."""

    events: list[dict] = field(default_factory=list)
    ticket: Ticket | None = None
    bound: BoundTicket | None = None
    fill: PaperFill | None = None

    def _log(self, seat: str, action: str, detail: str, ok: bool) -> None:
        self.events.append(
            {
                "ts": _now().isoformat(),
                "seat": seat,
                "action": action,
                "detail": detail,
                "ok": ok,
            }
        )

    def research_propose(
        self,
        *,
        portfolio: str,
        symbol: str,
        side: str,
        quantity: str,
        reference_price: str,
        thesis: str,
        grounding: str,
    ) -> Ticket:
        if self.ticket is not None:
            raise DeskRefusal("TicketAlreadyProposed")
        ticket = Ticket(
            portfolio=portfolio,
            symbol=symbol.upper(),
            side=side.upper(),
            quantity=Decimal(quantity),
            reference_price=Decimal(reference_price),
            thesis=thesis.strip() or "no thesis",
            grounding=grounding.strip() or "fixture-grounding",
        )
        self.ticket = ticket
        self._log("research", "propose", f"{ticket.side} {ticket.quantity} {ticket.symbol} digest={ticket.digest()[:12]}", True)
        return ticket

    def risk_bind(self, actor: str = "Risk") -> BoundTicket:
        if self.ticket is None:
            raise DeskRefusal("NoTicket")
        if self.bound is not None:
            raise DeskRefusal("AlreadyBound")
        bound = BoundTicket(
            ticket=self.ticket,
            ticket_digest=self.ticket.digest(),
            risk_actor=actor,
            bound_at=_now(),
        )
        self.bound = bound
        self._log("risk", "bind", f"bound {bound.ticket_digest[:12]} by {actor}", True)
        return bound

    def execution_submit(
        self,
        *,
        claimed_digest: str,
        observed_price: str,
        mutate_symbol: str | None = None,
        mutate_qty: str | None = None,
    ) -> PaperFill:
        if self.bound is None:
            self._log("execution", "submit", "DENIED: TicketNotBound", False)
            raise DeskRefusal("TicketNotBound")
        if mutate_symbol or mutate_qty:
            self._log("execution", "submit", "DENIED: ExecutionMayNotMutateTicket", False)
            raise DeskRefusal("ExecutionMayNotMutateTicket")
        if claimed_digest != self.bound.ticket_digest:
            self._log("execution", "submit", "DENIED: FrozenTicketRequired", False)
            raise DeskRefusal("FrozenTicketRequired")
        price = Decimal(observed_price)
        ref = self.bound.ticket.reference_price
        if ref == 0 or abs(price - ref) / ref > MAX_DRIFT:
            self._log("execution", "submit", "DENIED: PriceDriftExceeded", False)
            raise DeskRefusal("PriceDriftExceeded")
        fill = PaperFill(
            bound_digest=self.bound.ticket_digest,
            ticket_digest=self.bound.ticket.digest(),
            observed_price=price,
            simulated=True,
        )
        self.fill = fill
        self._log(
            "execution",
            "simulate_fill",
            f"[SIMULATED] fill {self.bound.ticket.side} {self.bound.ticket.quantity} {self.bound.ticket.symbol} @ {price} — not a street fill",
            True,
        )
        return fill

    def surveillance_halt(self, reason: str) -> None:
        self._log("surveillance", "halt", reason, True)
