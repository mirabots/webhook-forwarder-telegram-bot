from sqlalchemy import MetaData
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.types import BIGINT, Text

SCHEMA = "wftb"
Base = declarative_base(metadata=MetaData(schema=SCHEMA))


class Chats(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=False)
    owner_id: Mapped[int] = mapped_column(BIGINT, nullable=False)


class Targets(Base):
    __tablename__ = "targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    webhook: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(nullable=False)
    chat_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    key: Mapped[str]
    prefix: Mapped[str]
