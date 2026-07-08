import os
import logging
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

# Use centralized settings module
from backend.config import DATABASE_URL

logger = logging.getLogger(__name__)

def get_sanitized_db_url(url: str) -> str:
    """
    Returns a sanitized database URL with credentials (username/password) masked for secure logging.
    """
    try:
        parsed = urlparse(url)
        if parsed.password:
            # Mask both username and password
            netloc = f"*****:*****@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
        elif parsed.username:
            netloc = f"*****@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
        else:
            netloc = parsed.netloc
        
        sanitized_parsed = parsed._replace(netloc=netloc)
        return urlunparse(sanitized_parsed)
    except Exception:
        return "postgresql://***:***@***/database"

# Initialize connection pool
pool = None

def get_pool() -> ConnectionPool:
    global pool
    if pool is None:
        sanitized_url = get_sanitized_db_url(DATABASE_URL)
        logger.info(f"Initializing PostgreSQL connection pool with URL: {sanitized_url}")
        # min_size=1, max_size=10 is suitable for our single developer / resume-quality scale
        new_pool = ConnectionPool(conninfo=DATABASE_URL, min_size=1, max_size=10, open=True, kwargs={"autocommit": True})
        
        # Wait until the pool is ready (at least min_size connections established)
        new_pool.wait()
        
        pool = new_pool
        logger.info("PostgreSQL connection pool initialized successfully and verified database connectivity.")
    return pool

@contextmanager
def get_db_connection():
    """
    Context manager to retrieve a connection from the pool.
    Auto-commits or auto-rolls back depending on exceptions.
    """
    connection_pool = get_pool()
    with connection_pool.connection() as conn:
        # Enable dictionary row mapping by default for easier JSON handling
        conn.row_factory = dict_row
        yield conn

def init_db():
    """
    Initializes PostgreSQL tables required for the application.
    Does NOT affect checkpointer tables (LangGraph manages its own checkpointer tables).
    """
    logger.info("Initializing application database tables...")
    create_tables_sql = """
    -- Users Table
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) UNIQUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Sessions Table
    CREATE TABLE IF NOT EXISTS sessions (
        id VARCHAR(255) PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        dataset_id VARCHAR(255) NOT NULL,
        dataset_name VARCHAR(255),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Reports Table
    CREATE TABLE IF NOT EXISTS reports (
        id SERIAL PRIMARY KEY,
        session_id VARCHAR(255) REFERENCES sessions(id) ON DELETE CASCADE,
        question TEXT NOT NULL,
        narrative_summary TEXT,
        chart_plotly_json JSONB,
        pdf_file_path VARCHAR(512),
        execution_time_ms DOUBLE PRECISION,
        success BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    -- Metrics Table
    CREATE TABLE IF NOT EXISTS metrics (
        id SERIAL PRIMARY KEY,
        execution_date DATE UNIQUE NOT NULL DEFAULT CURRENT_DATE,
        total_executions INTEGER DEFAULT 0,
        first_try_success_count INTEGER DEFAULT 0,
        retry_success_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0,
        common_failure_types JSONB DEFAULT '{}'::jsonb
    );

    -- Add default user if not exists for easy portfolio testing
    INSERT INTO users (id, email) 
    VALUES (1, 'portfolio.user@example.com') 
    ON CONFLICT (id) DO NOTHING;
    """
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_tables_sql)
            logger.info("Application database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # Do not raise error to allow the app to run in mock/SQLite or memory if Postgres is not running locally.
        # But for production-grade it should log the issue.
        logger.warning("Continuing execution. Ensure PostgreSQL is running for persistent state.")

def close_pool():
    global pool
    if pool is not None:
        logger.info("Closing PostgreSQL connection pool...")
        pool.close()
        pool = None
