from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


ONTARIO_SPORTSBOOKS = [
    "theScore Bet",
    "FanDuel Ontario",
    "DraftKings Ontario",
    "Bet365 Ontario",
    "BetMGM Ontario",
    "Caesars Ontario",
]

MARKETS = ["moneyline", "spread", "totals"]


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    sport: Mapped[str] = mapped_column(String(64), index=True)
    league: Mapped[str] = mapped_column(String(64), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    home_team: Mapped[str] = mapped_column(String(128))
    away_team: Mapped[str] = mapped_column(String(128))
    home_team_normalized: Mapped[str] = mapped_column(String(128), index=True)
    away_team_normalized: Mapped[str] = mapped_column(String(128), index=True)

    odds: Mapped[list["Odds"]] = relationship("Odds", back_populates="event", cascade="all, delete-orphan")


class Odds(Base):
    __tablename__ = "odds"
    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "sportsbook",
            "market",
            "selection_normalized",
            "line",
            name="uq_odds_entry",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(128), ForeignKey("events.event_id"), index=True)
    sportsbook: Mapped[str] = mapped_column(String(64), index=True)
    market: Mapped[str] = mapped_column(String(32), index=True)
    selection: Mapped[str] = mapped_column(String(128))
    selection_normalized: Mapped[str] = mapped_column(String(128), index=True)
    line: Mapped[float | None] = mapped_column(Float, nullable=True)
    american_odds: Mapped[int] = mapped_column(Integer)
    decimal_odds: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)

    event: Mapped["Event"] = relationship("Event", back_populates="odds")
