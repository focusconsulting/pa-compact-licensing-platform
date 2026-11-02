"""Gives the test suite its own database, dropped and created empty at the start of every run.

pytest loads this file before ``tests/conftest.py``, so ``DB_NAME`` names the test
database before anything reads ``licensing_api.config``. The app's startup then
migrates it from empty (constitution Principle XIV), and data in the development
database, such as ``just seed demo``'s, never reaches a test.
"""

import os

import psycopg2
from psycopg2 import sql


def _use_empty_test_database() -> None:
    name = f'{os.environ.get("DB_NAME", "licensing")}_test'
    os.environ['DB_NAME'] = name
    # Imported here, after DB_NAME is set: importing the module reads the settings.
    from licensing_api.config import Settings

    connection = psycopg2.connect(Settings(db_name='postgres').sync_db_url)
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name))
        )
        cursor.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    connection.close()


_use_empty_test_database()
