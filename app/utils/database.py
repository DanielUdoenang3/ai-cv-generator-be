from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base, configure_mappers
from sqlalchemy import create_engine
from app.utils.settings import settings


def get_db_engine(test_mode: bool = False): 
    DATABASE_URL = settings.DB_URL

    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using them
        pool_recycle=3600,   # Recycle connections after 1 hour
        pool_size=10,        # Number of connections to maintain
        max_overflow=20,     # Max additional connections when pool is full
        echo=False           # Set to True for SQL query logging
    )


engine = get_db_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db_session = scoped_session(SessionLocal)

Base = declarative_base()

# Configure mappers after all models are imported
configure_mappers()


def create_database():
    return Base.metadata.create_all(bind=engine)


def get_db():
    db = db_session()
    try:
        yield db
    finally:
        db.close()