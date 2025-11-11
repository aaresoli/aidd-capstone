"""
Notification utilities
Provides a simple way to simulate outbound emails by logging them to the database.
"""
from src.data_access import get_db


class NotificationService:
    """Utility for recording notifications (simulated email delivery)."""

    @staticmethod
    def send_notification(user_id, subject, body, channel='email'):
        """Persist a notification and mark it as sent."""
        if not user_id:
            return

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO notifications (user_id, channel, subject, body, status)
                VALUES (?, ?, ?, ?, 'sent')
                ''',
                (user_id, channel, subject, body)
            )

        # Also log to stdout to aid developers during local testing
        print(f"[Notification::{channel}] → User {user_id} | {subject}\n{body}\n")
