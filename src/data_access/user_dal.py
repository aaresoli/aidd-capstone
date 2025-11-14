"""
User Data Access Layer
Handles all database operations for users
"""
import bcrypt
from src.data_access import get_db
from src.models.models import User

class UserDAL:
    """Data access layer for user operations"""
    
    @staticmethod
    def create_user(name, email, password, role='student', department=None, email_verified=True):
        """Create a new user with hashed password"""
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users (name, email, password_hash, role, department, email_verified)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, password_hash, role, department, int(bool(email_verified))))
            user_id = cursor.lastrowid
            
        return UserDAL.get_user_by_id(user_id)
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            
        if row:
            return User(**dict(row))
        return None
    
    @staticmethod
    def get_user_by_email(email):
        """Get user by email"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()
            
        if row:
            return User(**dict(row))
        return None
    
    @staticmethod
    def verify_password(email, password):
        """Verify user password and return user if valid"""
        user = UserDAL.get_user_by_email(email)
        if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return user
        return None
    
    @staticmethod
    def update_user(user_id, **kwargs):
        """Update user fields"""
        allowed_fields = ['name', 'email', 'department', 'profile_image', 'role', 'is_suspended']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [user_id]
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f'UPDATE users SET {set_clause} WHERE user_id = ?', values)
            
        return cursor.rowcount > 0
    
    @staticmethod
    def get_all_users():
        """Get all users"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            rows = cursor.fetchall()
            
        return [User(**dict(row)) for row in rows]
    
    @staticmethod
    def delete_user(user_id):
        """Delete a user"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            
        return cursor.rowcount > 0

    @staticmethod
    def set_suspension(user_id, is_suspended):
        """Suspend or reinstate a user."""
        value = 1 if is_suspended else 0
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_suspended = ? WHERE user_id = ?', (value, user_id))
        return cursor.rowcount > 0

    @staticmethod
    def mark_email_verified(user_id):
        """Mark a user account as email verified."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE users
                SET email_verified = 1,
                    verification_token = NULL,
                    verification_token_expiry = NULL
                WHERE user_id = ?
                ''',
                (user_id,)
            )
        return cursor.rowcount > 0

    @staticmethod
    def count_users(role=None):
        """Return total number of users with optional role filtering."""
        query = 'SELECT COUNT(*) as total FROM users'
        params = []

        if role is None:
            pass
        elif isinstance(role, (list, tuple, set)):
            placeholders = ','.join('?' for _ in role)
            query += f' WHERE role IN ({placeholders})'
            params.extend(list(role))
        else:
            query += ' WHERE role = ?'
            params.append(role)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()

        return row['total'] if row else 0

    @staticmethod
    def monthly_registration_trend(months=6):
        """Return monthly registration counts for the requested window."""
        window = max(1, int(months or 1))
        offset = f'-{window - 1} months' if window > 1 else '0 months'
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT strftime('%Y-%m', created_at) AS month,
                       COUNT(*) AS total
                FROM users
                WHERE created_at >= date('now', 'start of month', ?)
                GROUP BY month
                ORDER BY month ASC
                ''',
                (offset,)
            )
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def set_verification_token(user_id, token, expiry):
        """Set email verification token for a user"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET verification_token = ?, verification_token_expiry = ? WHERE user_id = ?',
                (token, expiry, user_id)
            )
        return cursor.rowcount > 0

    @staticmethod
    def verify_email_by_token(token):
        """
        Verify user email by token

        Returns:
            User object if token is valid, None otherwise
        """
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT * FROM users
                WHERE verification_token = ?
                AND verification_token_expiry > datetime('now')
                AND email_verified = 0
                ''',
                (token,)
            )
            row = cursor.fetchone()

            if row:
                # Mark email as verified and clear the token
                user_id = row['user_id']
                cursor.execute(
                    '''
                    UPDATE users
                    SET email_verified = 1,
                        verification_token = NULL,
                        verification_token_expiry = NULL
                    WHERE user_id = ?
                    ''',
                    (user_id,)
                )
                conn.commit()
                return User(**dict(row))

        return None

    @staticmethod
    def get_user_by_verification_token(token):
        """Get user by verification token (without verifying)"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM users WHERE verification_token = ?',
                (token,)
            )
            row = cursor.fetchone()

        if row:
            return User(**dict(row))
        return None

    @staticmethod
    def resend_verification_token(user_id, token, expiry):
        """Update verification token for resending"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE users
                SET verification_token = ?,
                    verification_token_expiry = ?
                WHERE user_id = ? AND email_verified = 0
                ''',
                (token, expiry, user_id)
            )
        return cursor.rowcount > 0
