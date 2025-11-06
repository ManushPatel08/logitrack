from sqlmodel import create_engine, SQLModel, Session
import os

# Get DB URL from environment variables
# Priority: DATABASE_URL (for cloud deployment) > individual params (for Docker)
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    # Fallback to individual params for Docker
    DB_USER = os.environ.get("POSTGRES_USER")
    DB_PASS = os.environ.get("POSTGRES_PASSWORD")
    DB_HOST = os.environ.get("POSTGRES_HOST", "db")
    DB_NAME = os.environ.get("POSTGRES_DB")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

# Create the engine
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

def get_session():
    """Get a database session."""
    with Session(engine) as session:
        yield session