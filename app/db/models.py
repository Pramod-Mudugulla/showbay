from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    func,
)

from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)

    owner: Mapped[str] = mapped_column(String(255), nullable=False) 
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    forks: Mapped[int] = mapped_column(Integer, nullable=False)
    open_issues: Mapped[int] = mapped_column(Integer, nullable=False)

    primary_language: Mapped[str | None] = mapped_column(String(255), nullable=True)
    html_url: Mapped[str] = mapped_column(String(255), nullable=False)

    repo_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )