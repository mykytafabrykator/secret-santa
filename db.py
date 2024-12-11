import asyncpg
import os

pool = None

async def init_db():
    global pool
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise ValueError("POSTGRES_DSN not set in environment variables")

    pool = await asyncpg.create_pool(dsn=dsn)

    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            wishlist TEXT DEFAULT NULL,
            started_pm INT DEFAULT 0
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            chat_id BIGINT,
            user_id BIGINT,
            assigned_to BIGINT DEFAULT NULL,
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_sessions (
            chat_id BIGINT PRIMARY KEY,
            session_active INT DEFAULT 0
        );
        """)

async def get_pool():
    return pool

async def set_session_active(chat_id: int, active: bool):
    p = await get_pool()
    val = 1 if active else 0
    async with p.acquire() as conn:
        await conn.execute("""
        INSERT INTO chat_sessions (chat_id, session_active) 
        VALUES ($1, $2)
        ON CONFLICT (chat_id) 
        DO UPDATE SET session_active = EXCLUDED.session_active
        """, chat_id, val)

async def is_session_active(chat_id: int) -> bool:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT session_active FROM chat_sessions WHERE chat_id = $1", chat_id)
        return (row and row["session_active"] == 1)

async def clear_participants(chat_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM participants WHERE chat_id = $1", chat_id)
