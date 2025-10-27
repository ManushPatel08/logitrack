from sqlmodel import create_engine, SQLModel, Session
import os

# Get DB URL from environment variables (set in docker-compose)
DB_USER = os.environ.get("POSTGRES_USER")
DB_PASS = os.environ.get("POSTGRES_PASSWORD")
DB_HOST = os.environ.get("POSTGRES_HOST")
DB_NAME = os.environ.get("POSTGRES_DB")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{5432}/{DB_NAME}"

# Create the engine
engine = create_engine(DATABASE_URL, echo=True)

def get_session():
    """Get a database session."""
    with Session(engine) as session:
        yield session