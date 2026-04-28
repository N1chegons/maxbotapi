from maxapi.context import State, StatesGroup
from sqlalchemy import text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import datetime
import enum
from src.db import Base


class UserState(enum.Enum):
    NEW = "new" # не проходил /new
    ONBOARDING_DISCLAIMER = "onboarding_disclaimer" # показали дисклеймер, ждём согласия
    ONBOARDING_MENU = "onboarding_menu" # на экране выбора (запрос/как работает/кто Игорь)
    MEMORY_SETUP = "memory_setup" # первый раз выбирает режим памяти
    ACTIVE_SESSION = "active_session" # идёт диалог с ботом
    SESSION_ENDED = "session_ended" # показали summary, ждём решения
    TRIAL_ACTIVE = "trial_active" # триал идёт
    TRIAL_ENDED_NOT_PAID = "trial_ended_not_paid"
    PAID = "paid" # активная подписка
    CHURNED = "churned" # подписка закончилась
    CRISIS_MODE = "crisis_mode" # сработал кризисный триггер

class MemoryMode(enum.Enum):
    none = "none"
    session = "session"
    full = "full"

class SubsStatus(enum.Enum):
    none = "none"
    active = "active"
    expired = "expired"

class SubsTier(enum.Enum):
    basic = "basic"
    deep = "deep"

class Role(enum.Enum):
    user = "user"
    assistant = "assistant"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(index=True)
    platform: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text(
            "TIMEZONE('utc', now())")
    )
    memory_mode: Mapped[MemoryMode] = mapped_column(default=MemoryMode.none)
    state: Mapped[UserState] = mapped_column(default=UserState.NEW)
    trial_started_at: Mapped[datetime.datetime] = mapped_column(nullable=True)
    trial_ends_at: Mapped[datetime.datetime] = mapped_column(nullable=True)
    messages_count_trial: Mapped[int] = mapped_column(default=0)
    subscription_status: Mapped[SubsStatus] = mapped_column(default=SubsStatus.none)
    subscription_tier: Mapped[SubsTier] = mapped_column(nullable=True)
    subscription_ends_at: Mapped[datetime.datetime] = mapped_column(nullable=True)
    last_active_at: Mapped[datetime.datetime] = mapped_column(nullable=True)
    disclaimer_agreed_at:  Mapped[datetime.datetime] = mapped_column(nullable=True)

    sessions = relationship("Session", back_populates="user")
    messages: Mapped[list["Message"]] = relationship(back_populates="user")

class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    started_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text(
            "TIMEZONE('utc', now())")
    )
    ended_at: Mapped[datetime.datetime] = mapped_column(nullable=True)

    user = relationship("User", back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(back_populates="session")

class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[Role]
    content: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text(
            "TIMEZONE('utc', now())")
    )
    is_crisis_flagged: Mapped[bool] = mapped_column(default=False)

    session: Mapped["Session"] = relationship(back_populates="messages")
    user: Mapped["User"] = relationship(back_populates="messages")

class Feedback(Base):
    __tablename__ = "feedbacks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text(
            "TIMEZONE('utc', now())")
    )
    fragment: Mapped[str]
    is_positive: Mapped[bool] = mapped_column(default=True)
    next_topic: Mapped[str | None]
    session_topic: Mapped[str | None]


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text(
            "TIMEZONE('utc', now())")
    )
    contact: Mapped[str] = mapped_column(nullable=True)
    messages: Mapped[str] = mapped_column(nullable=True)

    appointment_date: Mapped[datetime.datetime] = mapped_column(
        nullable=True,
        server_default=text(
            "TIMEZONE('utc', now())")
    )
    viewed: Mapped[bool] = mapped_column(nullable=True, default=False)

class ThemeChoice(StatesGroup):
    first_choice = State()

class ConsultChoice(StatesGroup):
    ant_choice = State()

class WaitingForPhone(StatesGroup):
    waiting = State()