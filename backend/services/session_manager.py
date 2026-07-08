import os
import time
import logging
import duckdb
from typing import Dict, List, Optional
from threading import Lock

logger = logging.getLogger(__name__)

class Session:
    """
    Represents an individual user session owning a dedicated in-memory DuckDB connection.
    """
    def __init__(self, session_id: str):
        self.session_id: str = session_id
        # Open a dedicated in-memory DuckDB connection
        self.connection: duckdb.DuckDBPyConnection = duckdb.connect(":memory:")
        self.last_accessed: float = time.time()
        self.lock: Lock = Lock()
        self.registered_tables: List[str] = []
        logger.info(f"Created DuckDB in-memory session: {session_id}")

    def touch(self):
        """Update the last accessed timestamp to prevent session eviction."""
        self.last_accessed = time.time()

    def close(self):
        """Safely close the DuckDB connection."""
        with self.lock:
            try:
                self.connection.close()
                logger.info(f"Closed DuckDB session connection: {self.session_id}")
            except Exception as e:
                logger.error(f"Error closing session {self.session_id} connection: {e}")


class SessionManager:
    """
    Manages the lifecycle of user sessions and their in-memory DuckDB connections.
    """
    def __init__(self, ttl_seconds: int = 1800):
        self.sessions: Dict[str, Session] = {}
        self.ttl_seconds: int = ttl_seconds
        self.lock: Lock = Lock()
        logger.info("DuckDB session manager initialized successfully.")

    def get_session(self, session_id: str) -> Session:
        """
        Retrieves or creates a session. Thread-safe.
        """
        with self.lock:
            if session_id not in self.sessions:
                self.sessions[session_id] = Session(session_id)
            session = self.sessions[session_id]
            session.touch()
            return session

    def register_csv(self, session_id: str, file_path: str, table_name: str) -> str:
        """
        Loads a CSV file into the session's in-memory DuckDB database.
        Returns the registered table name.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        session = self.get_session(session_id)
        with session.lock:
            try:
                # Use parameterized query to load the CSV safely
                session.connection.execute(
                    f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_csv_auto(?);",
                    [file_path]
                )
                if table_name not in session.registered_tables:
                    session.registered_tables.append(table_name)
                logger.info(f"Successfully registered CSV {file_path} as table {table_name} in session {session_id}")
                return table_name
            except Exception as e:
                logger.error(f"Failed to register CSV in session {session_id}: {e}")
                raise

    def execute_query(self, session_id: str, query: str, params: Optional[list] = None) -> List[Dict]:
        """
        Executes a SQL query against the session's DuckDB connection and returns dict results.
        """
        session = self.get_session(session_id)
        with session.lock:
            session.touch()
            try:
                cursor = session.connection.execute(query, params or [])
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                logger.error(f"Query execution error in session {session_id}: {e} (Query: {query})")
                raise

    def get_session_connection(self, session_id: str) -> duckdb.DuckDBPyConnection:
        """
        Returns the raw connection. Must be used with care under the session lock.
        """
        session = self.get_session(session_id)
        return session.connection

    def evict_session(self, session_id: str):
        """Manually evicts a session."""
        with self.lock:
            session = self.sessions.pop(session_id, None)
            if session:
                session.close()
                logger.info(f"Evicted session: {session_id}")

    def clean_expired_sessions(self):
        """
        Checks for and cleans up expired sessions. Should be run periodically.
        """
        current_time = time.time()
        expired_ids = []
        with self.lock:
            for session_id, session in self.sessions.items():
                if current_time - session.last_accessed > self.ttl_seconds:
                    expired_ids.append(session_id)

        for session_id in expired_ids:
            self.evict_session(session_id)

# Global Session Manager instance
session_manager = SessionManager()
