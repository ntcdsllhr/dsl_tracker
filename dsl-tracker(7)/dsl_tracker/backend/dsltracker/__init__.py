"""
Make PyMySQL masquerade as MySQLdb so Django's built-in
`django.db.backends.mysql` engine works with a pure-Python driver —
no system MySQL client libraries or compilation needed, which matters
on PythonAnywhere's free tier (MySQL-only) and keeps `pip install` fast
and dependency-free everywhere else too.

Only takes effect if PyMySQL is installed (see requirements.txt) and a
mysql:// DATABASE_URL is configured; harmless no-op otherwise (e.g. local
dev on SQLite, or Postgres in production).
"""
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
