from sqlmodel import create_engine, SQLModel, Session
import os

# Prefer a full DATABASE_URL (useful for Neon) but fall back to POSTGRES_* vars for local docker-compose
env_db_url = os.environ.get("DATABASE_URL")
skip_ssl = os.environ.get("SKIP_DB_SSL", "false").lower() in ("1", "true", "yes")

if env_db_url:
    DATABASE_URL = env_db_url
    connect_args = {}
    # If the caller did not opt out, ensure SSL is required for secure hosted DBs like Neon
    if not skip_ssl:
        connect_args = {"sslmode": "require"}
else:
    # Build a local URL from individual POSTGRES_* environment variables
    DB_USER = os.environ.get("POSTGRES_USER", "postgres")
    DB_PASS = os.environ.get("POSTGRES_PASSWORD", "")
    DB_HOST = os.environ.get("POSTGRES_HOST", "db")
    DB_PORT = os.environ.get("POSTGRES_PORT", "5432")
    DB_NAME = os.environ.get("POSTGRES_DB", "postgres")
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    connect_args = {}

# Create the engine. echo=True helps during debugging; lower this in production if noisy.
engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)

def get_session():
    """Yield a database session."""
    with Session(engine) as session:
        yield session