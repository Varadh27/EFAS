from contextlib import contextmanager
from typing import Generator, List, Dict, Any
import psycopg
from psycopg.rows import dict_row
from src.config import settings
from src.agents.nodes import validate_readonly_sql


@contextmanager
def get_db_connection() -> Generator[psycopg.Connection, None, None]:
    """Context manager providing a database connection with
    read-only default.
    """
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        conn.read_only = True
        yield conn
    finally:
        conn.close()


def execute_readonly_query(sql_query: str) -> List[Dict[str, Any]]:
    """Validates SQL and executes strictly in a read-only transaction scope."""
    safe_sql = validate_readonly_sql(sql_query)
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(safe_sql)
            results = cur.fetchall()
            return [dict(row) for row in results]
