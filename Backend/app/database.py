# =============================================================
# app/database.py — Database Connection & Session Setup
#
# WHAT IS SQLite?
#   SQLite is a lightweight, file-based database.
#   Unlike PostgreSQL or MySQL, it requires NO separate server —
#   the entire database lives in a single .db file on disk.
#   Perfect for development, small projects, and local apps.
#
# WHAT IS SQLAlchemy?
#   SQLAlchemy is a Python ORM (Object-Relational Mapper).
#   ORM = lets you talk to a database using Python classes and objects
#         instead of writing raw SQL queries.
#
#   WITHOUT ORM (raw SQL):
#     cursor.execute("INSERT INTO records (title, sentiment) VALUES (?, ?)",
#                    (title, sentiment))
#
#   WITH ORM (SQLAlchemy):
#     record = AnalysisRecord(title=title, sentiment=sentiment)
#     db.add(record)
#     db.commit()
#
#   Both do the same thing — but ORM is safer, more readable,
#   and lets you use Python objects instead of SQL strings.
#
# HOW FASTAPI CONNECTS TO THE DATABASE:
#   FastAPI uses "dependency injection" (Depends) to give each
#   route its own database session (connection).
#   The session opens when a request comes in, and closes after
#   the request is handled — even if an error occurs.
#
# HOW TABLES ARE CREATED:
#   SQLAlchemy reads your Python model classes (in models.py)
#   and generates the correct CREATE TABLE SQL automatically.
#   We call Base.metadata.create_all(engine) once at startup.
#
# =============================================================

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# =============================================================
# DATABASE FILE PATH
#
# The database lives at Backend/news_analyzer.db
# SQLite creates this file automatically on first run.
# "sqlite:///" is the connection string prefix SQLAlchemy expects.
# =============================================================

# __file__ = this file's path (database.py)
# os.path.dirname(__file__) = the 'app/' directory
# We go one level up to place the .db file in the Backend/ folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, "news_analyzer.db")

# The connection URL SQLAlchemy uses to locate the database
DATABASE_URL = f"sqlite:///{DB_PATH}"


# =============================================================
# ENGINE
#
# The "engine" is the core connection to the database.
# It handles the low-level communication (opening files,
# running SQL, returning results).
#
# connect_args={"check_same_thread": False}
#   SQLite normally only allows one thread to use a connection.
#   FastAPI handles multiple requests concurrently (many threads),
#   so we disable this restriction — SQLAlchemy manages safety for us.
# =============================================================
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)


# =============================================================
# SESSION FACTORY
#
# A "session" is a single conversation with the database.
# Think of it like a checkout at a store — you open a session,
# do your work (add/read/update), then close (commit or rollback).
#
# sessionmaker() creates a factory that produces new sessions.
#   autocommit=False → we manually call db.commit() to save changes
#   autoflush=False  → don't auto-send pending changes before queries
#   bind=engine      → all sessions use our SQLite engine
# =============================================================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# =============================================================
# BASE CLASS
#
# All ORM model classes (in models.py) will inherit from Base.
# SQLAlchemy uses Base to track which Python classes map to
# which database tables, and how the columns are defined.
# =============================================================
Base = declarative_base()


# =============================================================
# DATABASE SESSION DEPENDENCY
#
# This is a "generator function" used with FastAPI's Depends().
# It provides a fresh database session to any route that needs one.
#
# HOW IT WORKS:
#   1. yield db   → gives the session to the route function
#   2. The route does its work (reads/writes to db)
#   3. finally:   → runs after the route finishes (always)
#   4. db.close() → closes the session and frees resources
#
# This pattern ensures the session is ALWAYS closed — even if
# the route raises an exception halfway through.
# =============================================================
def get_db():
    """
    Dependency function: provides a database session per request.

    Usage in a route:
        from fastapi import Depends
        from app.database import get_db
        from sqlalchemy.orm import Session

        @router.get("/example")
        def my_route(db: Session = Depends(get_db)):
            records = db.query(MyModel).all()
    """
    db = SessionLocal()
    try:
        yield db           # Hand the session to the route function
    finally:
        db.close()         # Always clean up, even if an error occurred
