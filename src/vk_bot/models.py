import datetime
import enum
from sqlalchemy import text, BigInteger, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from vkbottle import BaseStateGroup

from src.db import Base


class ContentType(enum.Enum):
    TEST = "test"
    RIDDLE = "riddle"
    FACT = "fact"


class Question(Base):
    __tablename__ = "vk_questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[ContentType] = mapped_column(index=True, default=ContentType.FACT)
    title: Mapped[str] = mapped_column()
    video_url: Mapped[str] = mapped_column(nullable=True)

    options: Mapped[list] = mapped_column(JSON, nullable=True)

    correct_answer: Mapped[str] = mapped_column(nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )


class VKUser(Base):
    __tablename__ = "vk_users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vk_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    first_name: Mapped[str] = mapped_column(nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )

    last_fact_date: Mapped[datetime.datetime] = mapped_column(nullable=True)

    is_subscribed: Mapped[bool] = mapped_column(default=True)


class VKQuizResult(Base):
    __tablename__ = "vk_quiz_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    vk_id: Mapped[int] = mapped_column(BigInteger, index=True)

    question_id: Mapped[int] = mapped_column(ForeignKey("vk_questions.id", ondelete="SET NULL"), nullable=True)
    question_type: Mapped[ContentType] = mapped_column(default=ContentType.FACT)

    user_answer: Mapped[str] = mapped_column(nullable=True)
    is_correct: Mapped[bool] = mapped_column()

    answered_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text("TIMEZONE('utc', now())")
    )


class AdminStates(BaseStateGroup):
    WAITING_FOR_FACT_TEXT = "waiting_for_fact_text"
    WAITING_FOR_FACT_VIDEO = "waiting_for_fact_video"