import logging
from typing import Dict, List, Any, Optional
from backend.services.session_manager import session_manager
from backend.database.connection import get_db_connection
from psycopg import sql

logger = logging.getLogger(__name__)

def is_csv_session(session_id: str) -> bool:
    """
    Checks if the session is CSV-backed (i.e., exists in the SessionManager
    and has registered in-memory tables).
    """
    if session_id in session_manager.sessions:
        session = session_manager.get_session(session_id)
        if len(session.registered_tables) > 0:
            return True
    return False

def get_schema(session_id: str, dataset_id: str) -> Dict[str, Any]:
    """
    Returns the schema of the dataset (columns, data types, and total row count).
    """
    # Fetch sample rows to extract sample values for each column
    sample_values_map = {}
    try:
        samples = get_sample_rows(session_id, dataset_id, n=3)
        for row in samples:
            for col_name, val in row.items():
                if col_name not in sample_values_map:
                    sample_values_map[col_name] = []
                if val is not None and val not in sample_values_map[col_name]:
                    sample_values_map[col_name].append(val)
    except Exception as e:
        logger.warning(f"Could not retrieve sample values for columns: {e}")

    if is_csv_session(session_id):
        # Query DuckDB
        try:
            logger.info(f"Retrieving schema for CSV dataset {dataset_id} in session {session_id} from DuckDB")
            conn = session_manager.get_session_connection(session_id)
            # Retrieve row count
            res_count = conn.execute(f"SELECT COUNT(*) FROM {dataset_id};").fetchone()
            row_count = res_count[0] if res_count else 0
            
            # Retrieve columns and types
            res_info = conn.execute(f"PRAGMA table_info({dataset_id});").fetchall()
            # PRAGMA table_info returns: (cid, name, type, notnull, dflt_value, pk)
            columns = [{"name": r[1], "dtype": r[2], "sample_values": sample_values_map.get(r[1], [])} for r in res_info]
            
            return {
                "dataset_id": dataset_id,
                "source": "csv",
                "columns": columns,
                "row_count": row_count
            }
        except Exception as e:
            logger.error(f"Error reading schema from DuckDB: {e}")
            raise RuntimeError(f"Failed to read CSV dataset schema: {e}")
    else:
        # Query Postgres
        try:
            logger.info(f"Retrieving schema for Postgres table {dataset_id} in session {session_id}")
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Retrieve row count (use parameterized table name dynamically using SQL formatting)
                    count_query = sql.SQL("SELECT COUNT(*) FROM {table};").format(table=sql.Identifier(dataset_id))
                    cur.execute(count_query)
                    row = cur.fetchone()
                    row_count = row["count"] if row else 0

                    # Retrieve column definitions
                    schema_query = """
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_name = %s;
                    """
                    cur.execute(schema_query, (dataset_id,))
                    cols_rows = cur.fetchall()
                    columns = [{"name": r["column_name"], "dtype": r["data_type"], "sample_values": sample_values_map.get(r["column_name"], [])} for r in cols_rows]
                    
                    return {
                        "dataset_id": dataset_id,
                        "source": "postgres",
                        "columns": columns,
                        "row_count": row_count
                    }
        except Exception as e:
            logger.error(f"Error reading schema from Postgres: {e}")
            raise RuntimeError(f"Failed to read Postgres dataset schema: {e}")

def get_sample_rows(session_id: str, dataset_id: str, n: int = 5) -> List[Dict[str, Any]]:
    """
    Returns a sample of first N rows from the dataset.
    """
    if is_csv_session(session_id):
        try:
            logger.info(f"Fetching {n} sample rows for CSV {dataset_id} in session {session_id} from DuckDB")
            conn = session_manager.get_session_connection(session_id)
            cursor = conn.execute(f"SELECT * FROM {dataset_id} LIMIT ?;", [n])
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, r)) for r in rows]
        except Exception as e:
            logger.error(f"Error fetching samples from DuckDB: {e}")
            raise
    else:
        try:
            logger.info(f"Fetching {n} sample rows for Postgres table {dataset_id} in session {session_id}")
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    sample_query = sql.SQL("SELECT * FROM {table} LIMIT %s;").format(table=sql.Identifier(dataset_id))
                    cur.execute(sample_query, (n,))
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Error fetching samples from Postgres: {e}")
            raise

def get_column_stats(session_id: str, dataset_id: str, column: str) -> Dict[str, Any]:
    """
    Calculates detailed statistics for a single column (nulls, unique count, min, max, mean, top values).
    """
    if is_csv_session(session_id):
        try:
            logger.info(f"Computing column stats for {column} in CSV {dataset_id}")
            conn = session_manager.get_session_connection(session_id)
            
            # Nulls and uniques
            nulls_query = f"SELECT COUNT(*) FROM {dataset_id} WHERE \"{column}\" IS NULL;"
            uniques_query = f"SELECT COUNT(DISTINCT \"{column}\") FROM {dataset_id};"
            null_count = conn.execute(nulls_query).fetchone()[0]
            unique_count = conn.execute(uniques_query).fetchone()[0]
            
            # Numeric stats if applicable
            min_val, max_val, mean_val = None, None, None
            try:
                numeric_query = f"SELECT MIN(\"{column}\"), MAX(\"{column}\"), AVG(CAST(\"{column}\" AS DOUBLE)) FROM {dataset_id};"
                stats = conn.execute(numeric_query).fetchone()
                if stats:
                    min_val, max_val, mean_val = stats[0], stats[1], stats[2]
            except Exception:
                # Column is non-numeric, fallback to basic min/max text strings
                try:
                    text_query = f"SELECT MIN(\"{column}\"), MAX(\"{column}\") FROM {dataset_id};"
                    stats = conn.execute(text_query).fetchone()
                    if stats:
                        min_val, max_val = stats[0], stats[1]
                except Exception:
                    pass

            # Top values
            top_query = f"""
                SELECT "{column}" as val, COUNT(*) as cnt 
                FROM {dataset_id} 
                WHERE "{column}" IS NOT NULL 
                GROUP BY "{column}" 
                ORDER BY cnt DESC 
                LIMIT 5;
            """
            top_res = conn.execute(top_query).fetchall()
            top_values = [{"value": r[0], "count": r[1]} for r in top_res]
            
            return {
                "column": column,
                "null_count": null_count,
                "unique_count": unique_count,
                "min": min_val,
                "max": max_val,
                "mean": mean_val,
                "top_values": top_values
            }
        except Exception as e:
            logger.error(f"Error generating column stats from DuckDB: {e}")
            raise
    else:
        try:
            logger.info(f"Computing column stats for {column} in Postgres table {dataset_id}")
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Nulls & Uniques
                    cur.execute(
                        sql.SQL("SELECT COUNT(*) FROM {table} WHERE {col} IS NULL;").format(
                            table=sql.Identifier(dataset_id),
                            col=sql.Identifier(column)
                        )
                    )
                    null_count = cur.fetchone()["count"]
                    
                    cur.execute(
                        sql.SQL("SELECT COUNT(DISTINCT {col}) FROM {table};").format(
                            table=sql.Identifier(dataset_id),
                            col=sql.Identifier(column)
                        )
                    )
                    unique_count = cur.fetchone()["count"]

                    # Basic Numeric Stats (handles cast exceptions gracefully)
                    min_val, max_val, mean_val = None, None, None
                    try:
                        cur.execute(
                            sql.SQL("SELECT MIN({col}), MAX({col}), AVG(CAST({col} AS DOUBLE PRECISION)) FROM {table};").format(
                                table=sql.Identifier(dataset_id),
                                col=sql.Identifier(column)
                            )
                        )
                        stats = cur.fetchone()
                        if stats:
                            min_val = stats.get("min")
                            max_val = stats.get("max")
                            mean_val = stats.get("avg")
                    except Exception:
                        conn.rollback() # Rollback error state on cursor
                        try:
                            # Text-based min/max
                            cur.execute(
                                sql.SQL("SELECT MIN({col}), MAX({col}) FROM {table};").format(
                                    table=sql.Identifier(dataset_id),
                                    col=sql.Identifier(column)
                                )
                            )
                            stats = cur.fetchone()
                            if stats:
                                min_val = stats.get("min")
                                max_val = stats.get("max")
                        except Exception:
                            conn.rollback()

                    # Top Values
                    top_query = sql.SQL("""
                        SELECT {col} AS val, COUNT(*) AS cnt 
                        FROM {table} 
                        WHERE {col} IS NOT NULL 
                        GROUP BY {col} 
                        ORDER BY cnt DESC 
                        LIMIT 5;
                    """).format(
                        table=sql.Identifier(dataset_id),
                        col=sql.Identifier(column)
                    )
                    cur.execute(top_query)
                    top_res = cur.fetchall()
                    top_values = [{"value": r["val"], "count": r["cnt"]} for r in top_res]

                    return {
                        "column": column,
                        "null_count": null_count,
                        "unique_count": unique_count,
                        "min": min_val,
                        "max": max_val,
                        "mean": mean_val,
                        "top_values": top_values
                    }
        except Exception as e:
            logger.error(f"Error generating column stats from Postgres: {e}")
            raise

def run_query(session_id: str, dataset_id: str, query: str) -> Dict[str, Any]:
    """
    Executes a SQL query. If it is a CSV dataset, runs against session's DuckDB connection.
    Otherwise, runs against PostgreSQL.
    """
    if is_csv_session(session_id):
        try:
            logger.info(f"Running SQL query on CSV {dataset_id} in session {session_id} in DuckDB")
            # Enforce that query has read-only structure (no mutations) - simple heuristic
            query_lower = query.lower().strip()
            if any(kw in query_lower for kw in ["insert ", "update ", "delete ", "drop ", "alter ", "create "]):
                raise PermissionError("Write/DDL statements are restricted in query execution.")

            conn = session_manager.get_session_connection(session_id)
            cursor = conn.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            
            # Format rows as list of dicts
            results = [dict(zip(columns, r)) for r in rows]
            return {
                "success": True,
                "columns": columns,
                "row_count": len(results),
                "rows": results
            }
        except Exception as e:
            logger.error(f"DuckDB SQL run_query error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    else:
        try:
            logger.info(f"Running SQL query on Postgres table {dataset_id} in session {session_id}")
            # Enforce read-only structure
            query_lower = query.lower().strip()
            if any(kw in query_lower for kw in ["insert ", "update ", "delete ", "drop ", "alter ", "create "]):
                raise PermissionError("Write/DDL statements are restricted in query execution.")

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = [desc[0] for desc in cur.description] if cur.description else []
                    rows = cur.fetchall()
                    return {
                        "success": True,
                        "columns": columns,
                        "row_count": len(rows),
                        "rows": rows
                    }
        except Exception as e:
            logger.error(f"Postgres SQL run_query error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# --- Standard Model Context Protocol (MCP) server wrapper interface ---
# This allows the module to be run as an independent MCP Server or imported directly.
# (If we run this file directly, it launches a standard MCP Server via Stdio)
if __name__ == "__main__":
    import asyncio
    from mcp.server.fastmcp import FastMCP
    
    # Initialize FastMCP Server named "DataAccessMCP"
    mcp_server = FastMCP("DataAccessMCP")
    
    @mcp_server.tool()
    def get_dataset_schema(session_id: str, dataset_id: str) -> dict:
        """Retrieve schema details including column names, types and row counts."""
        return get_schema(session_id, dataset_id)

    @mcp_server.tool()
    def get_dataset_sample(session_id: str, dataset_id: str, n: int = 5) -> list:
        """Retrieve first N rows of sample data."""
        return get_sample_rows(session_id, dataset_id, n)

    @mcp_server.tool()
    def get_dataset_column_stats(session_id: str, dataset_id: str, column: str) -> dict:
        """Retrieve null counts, unique counts, mathematical boundaries and top frequent values of a column."""
        return get_column_stats(session_id, dataset_id, column)

    @mcp_server.tool()
    def run_dataset_query(session_id: str, dataset_id: str, query: str) -> dict:
        """Run custom SELECT SQL query against the session dataset and retrieve formatted row results."""
        return run_query(session_id, dataset_id, query)

    # Run the server on Stdio
    mcp_server.run()
