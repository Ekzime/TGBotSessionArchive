from contextlib import contextmanager
from sqlalchemy.orm import Session
from db.database import SessionLocal

@contextmanager
def get_db_session():
    """
    Контекст-менеджер, который автоматически делает commit() при успехе
    или rollback() при ошибке, и закрывает сессию.
    """
    db: Session = SessionLocal()
    try:
        yield db
        db.commit()   # если до этого не было ошибок, делаем commit
    except:
        db.rollback() # при любой ошибке откатываем
        raise         # пробрасываем исключение выше
    finally:
        db.close()    # закрываем сессию в любом случае