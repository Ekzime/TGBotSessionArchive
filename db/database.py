import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models.model import Base
from config import settings

SQLALCHEMY_DATABASE_URL = settings.SQLALCHEMY_DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL,echo=False) # если нужны логи с sqlalchemy echo=True

# Фабрика сессий (SessionLocal)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

init_db()
