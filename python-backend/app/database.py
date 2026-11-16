from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import DATABASE_URL

# 🎓 Node.js vs Python Database Connection:
# In Node.js + Prisma:
#   const prisma = new PrismaClient(); // Handles pooling automatically
#
# In Python + SQLAlchemy:
# 1. create_engine: Manages the connection pool to SQLite or PostgreSQL.
# 2. sessionmaker: Creates new Session objects for executing queries.
# 3. Base: The base class that all ORM model classes inherit from.

# Note for SQLite: check_same_thread=False allows FastAPI async workers to share the SQLite connection safely.
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False  # Set to True if you want to see every raw SQL query printed in the console
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    FastAPI Dependency:
    Yields a database session for each incoming HTTP request,
    and automatically closes it when the request finishes.
    Equivalent to an Express middleware that attaches a DB client to req.db!
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
