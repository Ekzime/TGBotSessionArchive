from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.models.model import Base

SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root@localhost:3307/botsessionarchive"
engine = create_engine(SQLALCHEMY_DATABASE_URL,echo=True)

# Фабрика сессий (SessionLocal)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

# init_db()


