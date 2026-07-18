import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Database.models import Base

DB_PATH = os.getenv("DB_PATH", "rail_network.db")
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()
