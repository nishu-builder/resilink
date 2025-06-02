import os
from functools import cache, wraps
from typing import AsyncGenerator, Callable, Coroutine, Any
# Import ContextVar
from contextvars import ContextVar

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session # Keep Session if sync stuff is used
from sqlalchemy import create_engine # Keep sync engine if used

from app.settings import get_settings

# --- Context Variable for Async Session --- 
# Initialize with None or a sentinel object
_current_session_cv: ContextVar[AsyncSession | None] = ContextVar("current_session", default=None)

# --- Synchronous Engine (Optional - If still needed) ---
@cache
def get_engine():
    return create_engine(get_settings().database_url, echo=get_settings().LOG_LEVEL == 'DEBUG')

@cache
def get_session_factory():
    engine = get_engine()
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Sync session getter (if needed)
# def get_session() -> Session: 
#     factory = get_session_factory()
#     with factory() as session:
#         yield session

# --- Asynchronous Engine & Session --- 
@cache
def get_async_engine():
    return create_async_engine(get_settings().ASYNC_DATABASE_URL, echo=get_settings().LOG_LEVEL == 'DEBUG')


@cache
def get_async_session_factory():
    async_engine = get_async_engine()
    return async_sessionmaker(
        bind=async_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

# FastAPI Dependency for Async Session (Can still be useful)
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get an async session (useful for routes not using the decorator)."""
    session_factory = get_async_session_factory()
    # Check if a session is already set in the context
    existing_session = _current_session_cv.get()
    if existing_session is not None:
        yield existing_session # Re-use existing session from context
        return # Don't manage commit/rollback here if re-using
        
    async with session_factory() as session:
        token = _current_session_cv.set(session) # Set for this context
        try:
            yield session
            # Commit usually handled by decorator or endpoint
        except Exception:
            await session.rollback()
            raise
        finally:
            _current_session_cv.reset(token) # Reset context var


# Accessor function for the current session
def get_current_session() -> AsyncSession:
    """Gets the current async session from the context variable."""
    session = _current_session_cv.get()
    if session is None:
        raise LookupError("No async session found in context. Use 'with_async_session' decorator or ensure 'get_async_session' dependency context is active.")
    return session


# Modified Decorator for Async Session Management using ContextVar
def with_async_session(func: Callable[..., Coroutine[Any, Any, Any]]) -> Callable[..., Coroutine[Any, Any, Any]]:
    """Decorator to provide an async session via context variable and handle commit/rollback."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Check if session already exists in context from an outer decorator/dependency
        existing_session = _current_session_cv.get()
        if existing_session is not None:
            # If session exists, just run the function; commit/rollback handled by outer context
            return await func(*args, **kwargs)

        # If no session, create one and manage it
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            token = _current_session_cv.set(session) # Set context var
            try:
                # Call the function - it will use get_current_session()
                result = await func(*args, **kwargs)
                await session.commit() # Commit on success
                return result
            except Exception:
                await session.rollback() # Rollback on error
                raise
            finally:
                _current_session_cv.reset(token) # Reset context var regardless of outcome
    return wrapper
