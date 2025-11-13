"""
Data Access Layer initialization
"""
import sqlite3
from contextlib import contextmanager
from sqlite3 import OperationalError
from src.config import Config

def get_db_connection():
    """Create a database connection"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    # Enforce referential integrity for every connection
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    """Initialize database with schema"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'staff', 'admin')),
                profile_image TEXT,
                department TEXT,
                is_suspended INTEGER NOT NULL DEFAULT 0 CHECK(is_suspended IN (0, 1)),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN is_suspended INTEGER NOT NULL DEFAULT 0 CHECK(is_suspended IN (0, 1))')
        except OperationalError:
            pass

        # Resources table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT,
                location TEXT,
                capacity INTEGER,
                images TEXT,
                equipment TEXT,
                availability_rules TEXT,
                is_restricted INTEGER NOT NULL DEFAULT 0 CHECK(is_restricted IN (0, 1)),
                status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft', 'published', 'archived')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(user_id)
            )
        ''')

        # Ensure new resource columns exist when upgrading older databases
        try:
            cursor.execute('ALTER TABLE resources ADD COLUMN equipment TEXT')
        except OperationalError:
            pass
        try:
            cursor.execute('ALTER TABLE resources ADD COLUMN is_restricted INTEGER NOT NULL DEFAULT 0 CHECK(is_restricted IN (0, 1))')
        except OperationalError:
            pass
        try:
            cursor.execute('ALTER TABLE resources ADD COLUMN availability_rules TEXT')
        except OperationalError:
            pass

        # Bookings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                requester_id INTEGER NOT NULL,
                start_datetime DATETIME NOT NULL,
                end_datetime DATETIME NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'cancelled', 'completed')),
                recurrence_rule TEXT,
                decision_notes TEXT,
                decision_by INTEGER,
                decision_timestamp DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
                FOREIGN KEY (requester_id) REFERENCES users(user_id),
                FOREIGN KEY (decision_by) REFERENCES users(user_id)
            )
        ''')

        try:
            cursor.execute('ALTER TABLE bookings ADD COLUMN recurrence_rule TEXT')
        except OperationalError:
            pass
        for column in ('decision_notes TEXT', 'decision_by INTEGER', 'decision_timestamp DATETIME'):
            try:
                cursor.execute(f'ALTER TABLE bookings ADD COLUMN {column}')
            except OperationalError:
                pass

        # Waitlist table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS waitlist_entries (
                entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                requester_id INTEGER NOT NULL,
                start_datetime DATETIME NOT NULL,
                end_datetime DATETIME NOT NULL,
                status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'promoted', 'cancelled')),
                recurrence_rule TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME,
                booking_id INTEGER,
                FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
                FOREIGN KEY (requester_id) REFERENCES users(user_id),
                FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_waitlist_resource_status ON waitlist_entries (resource_id, status)')

        # Message threads table (used to guarantee unique thread identifiers)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS message_threads (
                thread_id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_key TEXT NOT NULL UNIQUE,
                owner_id INTEGER NOT NULL,
                participant_id INTEGER NOT NULL,
                resource_id INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(user_id),
                FOREIGN KEY (participant_id) REFERENCES users(user_id),
                FOREIGN KEY (resource_id) REFERENCES resources(resource_id)
            )
        ''')

        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id INTEGER,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                is_flagged INTEGER NOT NULL DEFAULT 0 CHECK(is_flagged IN (0, 1)),
                flag_reason TEXT,
                flagged_by INTEGER,
                flagged_at DATETIME,
                is_hidden INTEGER NOT NULL DEFAULT 0 CHECK(is_hidden IN (0, 1)),
                FOREIGN KEY (thread_id) REFERENCES message_threads(thread_id),
                FOREIGN KEY (sender_id) REFERENCES users(user_id),
                FOREIGN KEY (receiver_id) REFERENCES users(user_id),
                FOREIGN KEY (flagged_by) REFERENCES users(user_id)
            )
        ''')

        for column in (
            'is_flagged INTEGER NOT NULL DEFAULT 0 CHECK(is_flagged IN (0, 1))',
            'flag_reason TEXT',
            'flagged_by INTEGER',
            'flagged_at DATETIME',
            'is_hidden INTEGER NOT NULL DEFAULT 0 CHECK(is_hidden IN (0, 1))'
        ):
            try:
                cursor.execute(f'ALTER TABLE messages ADD COLUMN {column}')
            except OperationalError:
                pass

        # Reviews table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                reviewer_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                comment TEXT,
                is_flagged INTEGER NOT NULL DEFAULT 0 CHECK(is_flagged IN (0, 1)),
                flag_reason TEXT,
                flagged_by INTEGER,
                flagged_at DATETIME,
                is_hidden INTEGER NOT NULL DEFAULT 0 CHECK(is_hidden IN (0, 1)),
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (resource_id) REFERENCES resources(resource_id),
                FOREIGN KEY (reviewer_id) REFERENCES users(user_id),
                FOREIGN KEY (flagged_by) REFERENCES users(user_id)
            )
        ''')

        for column in (
            'is_flagged INTEGER NOT NULL DEFAULT 0 CHECK(is_flagged IN (0, 1))',
            'flag_reason TEXT',
            'flagged_by INTEGER',
            'flagged_at DATETIME',
            'is_hidden INTEGER NOT NULL DEFAULT 0 CHECK(is_hidden IN (0, 1))'
        ):
            try:
                cursor.execute(f'ALTER TABLE reviews ADD COLUMN {column}')
            except OperationalError:
                pass

        # Admin logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_table TEXT,
                details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users(user_id)
            )
        ''')

        # Notifications table for simulated email delivery
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'sent')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_notification_state (
                user_id INTEGER PRIMARY KEY,
                last_seen_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')

        # Calendar integrations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_credentials (
                credential_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                credentials_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(user_id, provider)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                external_event_id TEXT NOT NULL,
                html_link TEXT,
                synced_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                UNIQUE(booking_id, user_id, provider)
            )
        ''')

        conn.commit()
        print("✓ Database initialized successfully")
