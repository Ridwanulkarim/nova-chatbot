import unittest
from sqlalchemy.engine.url import make_url
from app.database.connection import configure_database_connection, redact_db_url

class TestPostgresConnectionConfig(unittest.TestCase):
    """
    Focused unit tests for PostgreSQL URL normalization, SSL/TLS parameter translation,
    serverless connection pooling, password redaction, and SQLite backward compatibility.
    These tests are purely isolated in-memory tests and do not connect to any database.
    """

    def test_1_postgres_scheme_normalization(self):
        """Case 1: 'postgres://' is normalized to 'postgresql+pg8000://'."""
        raw_url = "postgres://testuser:mypassword@ep-test.neon.tech:5432/neondb"
        norm_url, cargs, ekwargs = configure_database_connection(raw_url, is_vercel=True)
        url_obj = make_url(norm_url)
        self.assertEqual(url_obj.drivername, "postgresql+pg8000")
        self.assertEqual(url_obj.username, "testuser")
        self.assertEqual(url_obj.password, "mypassword")
        self.assertEqual(url_obj.host, "ep-test.neon.tech")
        self.assertEqual(url_obj.port, 5432)
        self.assertEqual(url_obj.database, "neondb")

    def test_2_postgresql_scheme_normalization(self):
        """Case 2: 'postgresql://' is normalized to 'postgresql+pg8000://'."""
        raw_url = "postgresql://dbuser:securepwd@db.supabase.co:5432/postgres"
        norm_url, cargs, ekwargs = configure_database_connection(raw_url, is_vercel=True)
        url_obj = make_url(norm_url)
        self.assertEqual(url_obj.drivername, "postgresql+pg8000")
        self.assertEqual(url_obj.username, "dbuser")
        self.assertEqual(url_obj.password, "securepwd")

    def test_3_existing_pg8000_driver_handling(self):
        """Case 3: 'postgresql+pg8000://' driver specification is preserved."""
        raw_url = "postgresql+pg8000://appuser:apppwd@localhost:5432/appdb"
        norm_url, cargs, ekwargs = configure_database_connection(raw_url, is_vercel=False)
        url_obj = make_url(norm_url)
        self.assertEqual(url_obj.drivername, "postgresql+pg8000")
        self.assertEqual(url_obj.username, "appuser")

    def test_4_sslmode_require_handling(self):
        """Case 4: 'sslmode=require' enables ssl_context and is stripped from pg8000 URL query."""
        raw_url = "postgres://user:pass@ep-cool.neon.tech/neondb?sslmode=require"
        norm_url, cargs, ekwargs = configure_database_connection(raw_url, is_vercel=True)
        url_obj = make_url(norm_url)
        # sslmode must be stripped from query parameters
        self.assertNotIn("sslmode", url_obj.query)
        # connect_args must contain ssl_context=True
        self.assertTrue(cargs.get("ssl_context"))

    def test_5_unsupported_sslmode_rejection(self):
        """Case 5: Unsupported sslmode values are rejected with ValueError without leaking passwords."""
        raw_url = "postgres://admin:SuperSecret999@host.com/db?sslmode=unsupported_bogus"
        with self.assertRaises(ValueError) as ctx:
            configure_database_connection(raw_url, is_vercel=True)
        err_msg = str(ctx.exception)
        self.assertIn("Unsupported sslmode", err_msg)
        self.assertNotIn("SuperSecret999", err_msg)
        self.assertIn("***", err_msg)

    def test_6_preservation_of_unrelated_query_parameters(self):
        """Case 6: Unrelated query parameters (e.g., target_session_attrs) are strictly preserved."""
        raw_url = (
            "postgres://user:pass@ep-cool.neon.tech/neondb"
            "?sslmode=require&target_session_attrs=read-write&application_name=pluto_bot"
        )
        norm_url, cargs, ekwargs = configure_database_connection(raw_url, is_vercel=True)
        url_obj = make_url(norm_url)
        self.assertNotIn("sslmode", url_obj.query)
        self.assertEqual(url_obj.query.get("target_session_attrs"), "read-write")
        self.assertEqual(url_obj.query.get("application_name"), "pluto_bot")
        self.assertTrue(cargs.get("ssl_context"))

    def test_7_percent_encoded_credentials_preservation(self):
        """Case 7: Percent-encoded username and password are preserved without corruption or double-encoding."""
        # 'p@ss#word!' percent-encoded is 'p%40ss%23word%21'
        raw_url = "postgres://my%20user:p%40ss%23word%21@db.neon.tech:5432/mydb?sslmode=require"
        norm_url, cargs, ekwargs = configure_database_connection(raw_url, is_vercel=True)
        url_obj = make_url(norm_url)
        self.assertEqual(url_obj.username, "my user")
        self.assertEqual(url_obj.password, "p@ss#word!")
        # Rendered output string should retain standard URL encoding
        rendered = url_obj.render_as_string(hide_password=False)
        self.assertIn("p%40ss%23word%21", rendered)

    def test_8_sqlite_url_behavior_unchanged(self):
        """Case 8: SQLite URLs (local and /tmp) remain completely unchanged with check_same_thread=False."""
        for sqlite_url in ["sqlite:///./pluto_ai.db", "sqlite:////tmp/pluto_ai.db"]:
            norm_url, cargs, ekwargs = configure_database_connection(sqlite_url, is_vercel=True)
            self.assertEqual(norm_url, sqlite_url)
            self.assertEqual(cargs, {"check_same_thread": False})
            self.assertEqual(ekwargs, {"pool_pre_ping": True})
            # SQLite must not have serverless connection pool limits applied
            self.assertNotIn("pool_size", ekwargs)
            self.assertNotIn("max_overflow", ekwargs)

    def test_9_postgresql_serverless_pool_settings(self):
        """Case 9: Vercel serverless pooling uses pool_size=1, max_overflow=2, pool_recycle=300."""
        pg_url = "postgres://user:pass@ep-cool.neon.tech/neondb?sslmode=require"
        # 1. On Vercel
        _, _, vercel_pool = configure_database_connection(pg_url, is_vercel=True)
        self.assertEqual(vercel_pool["pool_size"], 1)
        self.assertEqual(vercel_pool["max_overflow"], 2)
        self.assertEqual(vercel_pool["pool_recycle"], 300)
        self.assertEqual(vercel_pool["pool_timeout"], 15)
        self.assertTrue(vercel_pool["pool_pre_ping"])

        # 2. Standard persistent server
        _, _, persistent_pool = configure_database_connection(pg_url, is_vercel=False)
        self.assertEqual(persistent_pool["pool_size"], 5)
        self.assertEqual(persistent_pool["max_overflow"], 10)
        self.assertEqual(persistent_pool["pool_recycle"], 1800)
        self.assertEqual(persistent_pool["pool_timeout"], 30)

    def test_10_redaction_of_passwords_in_errors_and_logs(self):
        """Case 10: redact_db_url masks passwords completely and never reveals secrets."""
        url_with_secret = "postgres://admin:SuperSecretPass2026!@ep-cool.neon.tech:5432/main?sslmode=require"
        redacted = redact_db_url(url_with_secret)
        self.assertNotIn("SuperSecretPass2026!", redacted)
        self.assertIn("admin:***@ep-cool.neon.tech:5432/main", redacted)

    def test_11_remote_plaintext_rejection_disable(self):
        """Case 11: Remote database host with sslmode=disable is strictly rejected."""
        raw_url = "postgres://clouduser:CloudSecretPass@ep-test.neon.tech:5432/neondb?sslmode=disable"
        with self.assertRaises(ValueError) as ctx:
            configure_database_connection(raw_url, is_vercel=True)
        err = str(ctx.exception)
        self.assertIn("Insecure sslmode 'disable' is rejected for remote database host", err)
        self.assertNotIn("CloudSecretPass", err)
        self.assertIn("***", err)

    def test_12_remote_plaintext_rejection_allow(self):
        """Case 12: Remote database host with sslmode=allow is strictly rejected."""
        raw_url = "postgresql://supauser:SupaSecret99@db.supabase.co:5432/postgres?sslmode=allow"
        with self.assertRaises(ValueError) as ctx:
            configure_database_connection(raw_url, is_vercel=True)
        err = str(ctx.exception)
        self.assertIn("Insecure sslmode 'allow' is rejected for remote database host", err)
        self.assertNotIn("SupaSecret99", err)

    def test_13_remote_default_tls_when_sslmode_omitted(self):
        """Case 13: Remote database without sslmode parameter defaults to TLS (ssl_context=True)."""
        raw_url = "postgresql://user:pass@ep-remote.neon.tech:5432/production_db"
        _, cargs, _ = configure_database_connection(raw_url, is_vercel=True)
        self.assertTrue(cargs.get("ssl_context"))

    def test_14_remote_prefer_enforces_tls(self):
        """Case 14: Remote database with sslmode=prefer enforces TLS (never downgrades to plaintext)."""
        raw_url = "postgres://user:pass@ep-remote.neon.tech:5432/production_db?sslmode=prefer"
        norm_url, cargs, _ = configure_database_connection(raw_url, is_vercel=True)
        self.assertNotIn("sslmode", make_url(norm_url).query)
        self.assertTrue(cargs.get("ssl_context"))

    def test_15_localhost_plaintext_modes(self):
        """Case 15: Localhost with sslmode=disable or allow sets ssl_context=False."""
        for mode in ("disable", "allow"):
            raw_url = f"postgres://localuser:localpass@localhost:5432/devdb?sslmode={mode}"
            norm_url, cargs, _ = configure_database_connection(raw_url, is_vercel=False)
            self.assertNotIn("sslmode", make_url(norm_url).query)
            self.assertFalse(cargs.get("ssl_context"))

    def test_16_localhost_default_omitted_sslmode(self):
        """Case 16: Localhost without sslmode defaults to unencrypted local connection."""
        raw_url = "postgres://localuser:localpass@127.0.0.1:5432/devdb"
        _, cargs, _ = configure_database_connection(raw_url, is_vercel=False)
        self.assertFalse(cargs.get("ssl_context"))

    def test_17_localhost_explicit_ssl_require(self):
        """Case 17: Localhost with explicit sslmode=require sets ssl_context=True."""
        raw_url = "postgres://localuser:localpass@localhost:5432/devdb?sslmode=require"
        _, cargs, _ = configure_database_connection(raw_url, is_vercel=False)
        self.assertTrue(cargs.get("ssl_context"))

    def test_18_loopback_ipv6_handling(self):
        """Case 18: IPv6 loopback [::1] is treated as local host."""
        raw_url = "postgres://localuser:localpass@[::1]:5432/devdb?sslmode=disable"
        _, cargs, _ = configure_database_connection(raw_url, is_vercel=False)
        self.assertFalse(cargs.get("ssl_context"))

if __name__ == "__main__":
    unittest.main()
