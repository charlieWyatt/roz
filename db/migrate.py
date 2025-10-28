#!/usr/bin/env python3
"""
Database migration runner.

Simple migration system that runs SQL files in order.
Works with both Python workers and TypeScript app (Kysely).
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', '')

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'dbname': os.getenv('DB_NAME', 'postgres'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'sslmode': 'require',  # Supabase requires SSL
}

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'


def get_connection():
    """Get database connection."""
    try:
        # Try connection string first (preferred for Supabase)
        if DATABASE_URL:
            conn = psycopg2.connect(DATABASE_URL + '&sslmode=require' if 'sslmode' not in DATABASE_URL else DATABASE_URL)
            return conn
        else:
            conn = psycopg2.connect(**DB_CONFIG)
            return conn
    except psycopg2.OperationalError as e:
        print(f"Error connecting to database: {e}")
        if DATABASE_URL:
            print(f"Using DATABASE_URL connection string")
        else:
            print(
                f"Config: {DB_CONFIG['user']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
        sys.exit(1)


def create_migrations_table(conn):
    """Create table to track applied migrations."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    conn.commit()


def get_applied_migrations(conn) -> List[str]:
    """Get list of already applied migrations."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT migration_name FROM schema_migrations ORDER BY migration_name")
        return [row[0] for row in cur.fetchall()]


def get_pending_migrations(applied: List[str]) -> List[Tuple[str, Path]]:
    """Get list of migrations that haven't been applied yet."""
    all_migrations = sorted(MIGRATIONS_DIR.glob('*.sql'))
    pending = []

    for migration_path in all_migrations:
        migration_name = migration_path.stem
        if migration_name not in applied:
            pending.append((migration_name, migration_path))

    return pending


def apply_migration(conn, migration_name: str, migration_path: Path):
    """Apply a single migration."""
    print(f"Applying migration: {migration_name}")

    with open(migration_path, 'r') as f:
        sql = f.read()

    try:
        with conn.cursor() as cur:
            # Execute the migration SQL
            cur.execute(sql)

            # Record that we applied this migration
            cur.execute(
                "INSERT INTO schema_migrations (migration_name) VALUES (%s)",
                (migration_name,)
            )

        conn.commit()
        print(f"✓ Applied: {migration_name}")
        return True

    except Exception as e:
        conn.rollback()
        print(f"✗ Failed: {migration_name}")
        print(f"Error: {e}")
        return False


def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    # Skip database creation for managed services like Supabase (using connection string)
    if DATABASE_URL:
        print("Using managed database (Supabase) - skipping database creation")
        return True
    
    try:
        # Connect to postgres database to create our database
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            dbname='postgres',
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        with conn.cursor() as cur:
            # Check if database exists
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (DB_CONFIG['dbname'],)
            )

            if not cur.fetchone():
                print(f"Creating database: {DB_CONFIG['dbname']}")
                cur.execute(f"CREATE DATABASE {DB_CONFIG['dbname']}")
                print(f"✓ Database created: {DB_CONFIG['dbname']}")
            else:
                print(f"Database already exists: {DB_CONFIG['dbname']}")

        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"Error creating database: {e}")
        return False


def export_schema(conn, output_path: Path):
    """Export current database schema to a file."""
    print(f"Exporting schema to: {output_path}")

    try:
        with conn.cursor() as cur:
            # Get all tables, indexes, and views
            cur.execute("""
                SELECT 
                    schemaname, 
                    tablename
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)

            tables = cur.fetchall()

            with open(output_path, 'w') as f:
                f.write("-- Current database schema\n")
                f.write(f"-- Generated by migrate.py\n\n")

                for schema, table in tables:
                    # Get table definition (simplified)
                    f.write(f"-- Table: {table}\n")

        print(f"✓ Schema exported to: {output_path}")

    except Exception as e:
        print(f"Error exporting schema: {e}")


def main():
    """Run migrations."""
    print("=" * 60)
    print("DATABASE MIGRATION TOOL")
    print("=" * 60)

    # Create database if needed
    if not create_database_if_not_exists():
        sys.exit(1)

    # Connect to database
    conn = get_connection()
    print(
        f"Connected to: {DB_CONFIG['user']}@{DB_CONFIG['host']}/{DB_CONFIG['dbname']}")

    # Create migrations tracking table
    create_migrations_table(conn)

    # Get applied and pending migrations
    applied = get_applied_migrations(conn)
    pending = get_pending_migrations(applied)

    print(f"\nApplied migrations: {len(applied)}")
    print(f"Pending migrations: {len(pending)}")

    if not pending:
        print("\n✓ Database is up to date!")
        conn.close()
        return

    # Apply pending migrations
    print("\n" + "=" * 60)
    print("APPLYING MIGRATIONS")
    print("=" * 60)

    for migration_name, migration_path in pending:
        if not apply_migration(conn, migration_name, migration_path):
            print("\n✗ Migration failed. Stopping.")
            conn.close()
            sys.exit(1)

    print("\n" + "=" * 60)
    print(f"✓ Successfully applied {len(pending)} migration(s)")
    print("=" * 60)

    # Export current schema
    schema_path = Path(__file__).parent / 'schema.sql'
    export_schema(conn, schema_path)

    conn.close()


if __name__ == '__main__':
    main()
