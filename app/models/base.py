from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

# Create the database engine using the connection string from .env
engine = create_engine(get_settings().database_url)

# Session factory - used to create database sessions
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.
    
    All your models will inherit from this. It tells SQLAlchemy
    how to map Python classes to database tables.
    """
    pass


def get_db():
    """Dependency: yields a DB session, auto-closes after use.
    
    Use this in FastAPI endpoints to get a database session:
    
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
