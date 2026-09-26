import os
from pathlib import Path
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, String, JSON, select
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True)
    kind = Column(String, index=True, nullable=False)
    value = Column(JSON, nullable=False)


url = os.getenv("DATABASE_URL", "sqlite:///./data/bench.db")
if url.startswith("sqlite"):
    Path("data").mkdir(exist_ok=True)
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg://", 1)
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(
    url,
    connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    pool_pre_ping=True,
)
Base.metadata.create_all(engine)


@contextmanager
def db():
    with Session(engine) as session:
        with session.begin():
            yield session


def get(s, key, kind=None, lock=False):
    row = (
        s.scalar(select(Document).where(Document.id == key).with_for_update())
        if lock
        else s.get(Document, key)
    )
    return row.value if row and (kind is None or row.kind == kind) else None


def put(s, key, kind, value):
    row = s.get(Document, key)
    if row:
        row.value = value
    else:
        s.add(Document(id=key, kind=kind, value=value))
    return value


def listing(s, kind):
    return [r.value for r in s.scalars(select(Document).where(Document.kind == kind))]
