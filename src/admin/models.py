from sqlalchemy import text
from sqlalchemy.orm import Mapped, mapped_column
import datetime

from src.db import Base

class CommandLog(Base):
    __tablename__ = "command_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(index=True)
    command: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text(
            "TIMEZONE('utc', now())")
    )