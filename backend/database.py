"""
Database configuration and session management
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import yaml
import os

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'settings.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Create database directory if not exists
db_path = config['database']['path']
db_dir = os.path.dirname(db_path)
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

# SQLite database URL
SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Dependency for FastAPI to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine, checkfirst=True)
