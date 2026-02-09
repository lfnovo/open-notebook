import contextvars

# Set by ProxyAuthMiddleware per-request; read by db_connection() to select user's database.
# Empty string means single-user mode (no per-user DB routing).
current_user: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_user", default=""
)
