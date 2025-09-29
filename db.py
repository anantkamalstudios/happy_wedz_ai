import psycopg2
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from config import Config

db_pool = SimpleConnectionPool(
    minconn=1,
    maxconn=20,
    host=Config.DB_HOST,
    port=Config.DB_PORT,
    database=Config.DB_NAME,
    user=Config.DB_USER,
    password=Config.DB_PASSWORD
)

@contextmanager
def get_db():
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        db_pool.putconn(conn)
