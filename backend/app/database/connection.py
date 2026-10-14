import os
import re
from typing import Tuple, Dict, Any, Optional
from sqlalchemy.engine.url import make_url, URL

def redact_db_url(url_str: str) -> str:
    """
    Safely redact credentials from a database URL string for error messages and logging.
    Guarantees passwords are never printed or logged.
    """
    if not url_str or not isinstance(url_str, str):
        return ""
    try:
        clean = url_str.strip()
        if clean.startswith("postgres://"):
            clean = clean.replace("postgres://", "postgresql://", 1)
        return make_url(clean).render_as_string(hide_password=True)
    except Exception:
        # Fallback regex masking if URL cannot be parsed
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url_str)

def is_local_host(host: Optional[str]) -> bool:
    """
    Check if the given host string points to the local machine.
    Handles localhost, IPv4 loopback (127.0.0.1), IPv6 loopback (::1 or [::1]), and empty/socket hosts.
    """
    if not host:
        return True
    clean_host = host.strip().lower().strip("[]")
    return clean_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0")

def configure_database_connection(
    raw_url: str,
    is_vercel: Optional[bool] = None
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """
    Configure database URL, driver-specific connect_args, and engine pooling parameters.

    1. Supports sqlite://, postgres://, postgresql://, and postgresql+<driver>://.
    2. Normalizes postgres:// and postgresql:// to use postgresql+pg8000 for pure-Python serverless execution.
    3. Preserves username, password, hostname, port, database, percent-encoded credentials, and other query params.
    4. Handles 'sslmode' query parameter explicitly for pg8000 (which does not accept 'sslmode' argument directly).
    5. Strictly rejects insecure 'disable' or 'allow' sslmode for remote database hosts.
    6. Enforces TLS/SSL (ssl_context=True) for all remote PostgreSQL hosts, verifying CA certificates and hostname.
    7. Allows plaintext or explicit SSL on localhost / 127.0.0.1 / ::1 for local development.
    8. Applies serverless-friendly connection pool settings on Vercel (pool_size=1, max_overflow=2, pool_recycle=300).
    9. Preserves existing SQLite configuration (check_same_thread=False).
    """
    if not raw_url or not isinstance(raw_url, str):
        raise ValueError("DATABASE_URL must be a non-empty string")

    clean_raw = raw_url.strip()

    if is_vercel is None:
        from app.core.config import is_running_on_vercel
        is_vercel = is_running_on_vercel()

    # 1. SQLite handling: keep completely unchanged
    if clean_raw.startswith("sqlite"):
        return clean_raw, {"check_same_thread": False}, {"pool_pre_ping": True}

    # 2. Normalize scheme prefix
    if clean_raw.startswith("postgres://"):
        clean_raw = clean_raw.replace("postgres://", "postgresql://", 1)

    try:
        url: URL = make_url(clean_raw)
    except Exception as e:
        redacted = redact_db_url(clean_raw)
        raise ValueError(f"Invalid DATABASE_URL format ({redacted}): {e}") from None

    # 3. Dialect selection: ensure pg8000 is used when standard postgresql or no driver is specified
    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+pg8000")

    connect_args: Dict[str, Any] = {}
    engine_kwargs: Dict[str, Any] = {"pool_pre_ping": True}

    # 4. Connection Pooling Configuration
    if is_vercel:
        # Vercel serverless functions: 1 connection per container, short recycle, fast timeout
        engine_kwargs.update({
            "pool_size": 1,
            "max_overflow": 2,
            "pool_recycle": 300,
            "pool_timeout": 15,
        })
    else:
        # Standard persistent server: standard pool
        engine_kwargs.update({
            "pool_size": 5,
            "max_overflow": 10,
            "pool_recycle": 1800,
            "pool_timeout": 30,
        })

    # 5. SSL / TLS Configuration for pg8000
    if "pg8000" in url.drivername:
        query_dict = dict(url.query)
        sslmode = query_dict.get("sslmode")

        # Strip driver-unsupported query parameters (sslmode, channel_binding) from pg8000.connect()
        strip_params = [k for k in ("sslmode", "channel_binding") if k in query_dict]
        if strip_params:
            url = url.difference_update_query(strip_params)

        host_is_local = is_local_host(url.host)

        if sslmode is not None:
            clean_mode = str(sslmode).strip().lower()

            if not host_is_local:
                # Remote database host: strictly reject unencrypted modes
                if clean_mode in ("disable", "allow"):
                    redacted = url.render_as_string(hide_password=True)
                    raise ValueError(
                        f"Insecure sslmode '{clean_mode}' is rejected for remote database host '{url.host}'. "
                        f"Remote PostgreSQL connections must enforce TLS encryption ({redacted})."
                    )
                elif clean_mode in ("require", "verify-ca", "verify-full", "prefer"):
                    # pg8000 uses ssl.create_default_context() when ssl_context=True,
                    # enforcing TLS 1.2+, CA signature validation, and hostname matching.
                    connect_args["ssl_context"] = True
                else:
                    redacted = url.render_as_string(hide_password=True)
                    raise ValueError(
                        f"Unsupported sslmode '{clean_mode}' in database connection ({redacted}). "
                        "Supported modes for remote hosts: require, verify-ca, verify-full, prefer."
                    )
            else:
                # Local database host (localhost, 127.0.0.1, ::1)
                if clean_mode in ("require", "verify-ca", "verify-full"):
                    connect_args["ssl_context"] = True
                elif clean_mode in ("disable", "allow", "prefer"):
                    connect_args["ssl_context"] = False
                else:
                    redacted = url.render_as_string(hide_password=True)
                    raise ValueError(
                        f"Unsupported sslmode '{clean_mode}' in database connection ({redacted}). "
                        "Supported modes: require, verify-ca, verify-full, prefer, disable, allow."
                    )
        else:
            # When sslmode is omitted:
            if not host_is_local:
                # Never silently downgrade remote database connections to plaintext.
                # All remote PostgreSQL databases default to TLS verification.
                connect_args["ssl_context"] = True
            else:
                # Local development database defaults to unencrypted connection
                connect_args["ssl_context"] = False

    final_url = url.render_as_string(hide_password=False)
    return final_url, connect_args, engine_kwargs
