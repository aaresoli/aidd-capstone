"""
Database models for Campus Resource Hub
This file defines the schema structure
"""

from datetime import datetime
from flask_login import UserMixin

class User(UserMixin):
    """
    User model representing students, staff, and administrators.
    
    Implements Flask-Login's UserMixin interface for session management.
    All users can create and manage resources; staff/admins have additional
    permissions for approving bookings on restricted resources.
    
    Roles:
    - 'student': Can browse and book resources
    - 'staff': Can approve bookings for their own resources
    - 'admin': Full system access including user management
    """
    def __init__(self, user_id=None, name=None, email=None, password_hash=None,
                 role='student', profile_image=None, department=None, created_at=None,
                 is_suspended=0, email_verified=0, verification_token=None,
                 verification_token_expiry=None):
        self.user_id = user_id
        self.name = name
        self.email = email  # Must be unique, used for login
        self.password_hash = password_hash  # Bcrypt-hashed password (never plaintext)
        self.role = role  # 'student', 'staff', 'admin'
        self.profile_image = profile_image  # Path to uploaded profile image
        self.department = department  # Optional department/affiliation
        self.created_at = created_at or datetime.now()
        self.is_suspended = bool(is_suspended)  # Account suspension flag
        self.email_verified = bool(email_verified)  # Email verification status
        self.verification_token = verification_token  # Cryptographically secure token
        self.verification_token_expiry = verification_token_expiry  # Token expiration time
    
    def get_id(self):
        """
        Return the user identifier used by Flask-Login.
        
        Required by UserMixin interface. Flask-Login uses this to store
        user ID in the session cookie.
        
        Returns:
            str: String representation of user_id
        """
        return str(self.user_id)
    
    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'profile_image': self.profile_image,
            'department': self.department,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'is_suspended': self.is_suspended,
            'email_verified': self.email_verified,
            'verification_token': self.verification_token,
            'verification_token_expiry': self.verification_token_expiry
        }


class Resource:
    """
    Resource model for campus resources (rooms, equipment, spaces).
    
    Represents any bookable campus resource with availability rules, booking
    constraints, and lifecycle status. Resources can be restricted (requiring
    approval) or unrestricted (auto-approved).
    
    Status values:
    - 'draft': Not yet published, not visible to students
    - 'published': Available for booking
    - 'archived': No longer accepting new bookings
    """
    def __init__(self, resource_id=None, owner_id=None, title=None, description=None,
                 category=None, location=None, capacity=None, images=None,
                 equipment=None, availability_rules=None, is_restricted=0,
                 status='draft', created_at=None, availability_schedule=None,
                 min_booking_minutes=None, max_booking_minutes=None,
                 booking_increment_minutes=None, buffer_minutes=None,
                 advance_booking_days=None, min_lead_time_hours=None):
        self.resource_id = resource_id
        self.owner_id = owner_id  # User ID of resource owner (can approve bookings)
        self.title = title
        self.description = description
        self.category = category  # 'Study Room', 'Lab Equipment', 'Event Space', etc.
        self.location = location  # Physical location on campus
        self.capacity = capacity  # Maximum occupancy (if applicable)
        self.images = images  # Comma-separated file paths for uploaded images
        self.equipment = equipment  # Optional equipment list/description
        self.availability_rules = availability_rules  # JSON string with custom rules
        self.is_restricted = bool(is_restricted)  # If True, bookings require manual approval
        self.status = status  # 'draft', 'published', 'archived'
        self.created_at = created_at or datetime.now()
        # Weekly availability schedule as JSON: {day: [{"start": "HH:MM", "end": "HH:MM"}]}
        self.availability_schedule = availability_schedule
        # Booking constraints
        self.min_booking_minutes = min_booking_minutes  # Minimum booking duration
        self.max_booking_minutes = max_booking_minutes  # Maximum booking duration
        self.booking_increment_minutes = booking_increment_minutes  # Time slot increments
        self.buffer_minutes = buffer_minutes  # Required gap between bookings
        self.advance_booking_days = advance_booking_days  # How far ahead bookings allowed
        self.min_lead_time_hours = min_lead_time_hours  # Minimum notice required
    
    def to_dict(self):
        """Convert resource to dictionary"""
        return {
            'resource_id': self.resource_id,
            'owner_id': self.owner_id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'location': self.location,
            'capacity': self.capacity,
            'images': self.images,
            'availability_rules': self.availability_rules,
            'equipment': self.equipment,
            'is_restricted': self.is_restricted,
            'status': self.status,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'availability_schedule': self.availability_schedule,
            'min_booking_minutes': self.min_booking_minutes,
            'max_booking_minutes': self.max_booking_minutes,
            'booking_increment_minutes': self.booking_increment_minutes,
            'buffer_minutes': self.buffer_minutes,
            'advance_booking_days': self.advance_booking_days,
            'min_lead_time_hours': self.min_lead_time_hours
        }


class Booking:
    """
    Booking model for resource reservations.
    
    Represents a time slot reservation for a resource. Bookings go through
    a lifecycle: created as 'pending' or 'approved' (depending on resource
    restrictions), then moved to 'approved', 'rejected', 'completed', or 'cancelled'.
    
    Status lifecycle:
    - 'pending': Awaiting owner approval (restricted resources only)
    - 'approved': Confirmed and active
    - 'rejected': Declined by owner
    - 'cancelled': Cancelled by requester or owner
    - 'completed': Finished (allows reviews to be posted)
    
    Datetime fields (start_datetime, end_datetime) are stored in UTC.
    """
    def __init__(self, booking_id=None, resource_id=None, requester_id=None,
                 start_datetime=None, end_datetime=None, status='pending',
                 recurrence_rule=None, created_at=None, updated_at=None,
                 decision_notes=None, decision_by=None, decision_timestamp=None,
                 requester_name=None):
        self.booking_id = booking_id
        self.resource_id = resource_id  # Resource being booked
        self.requester_id = requester_id  # User making the booking
        self.start_datetime = start_datetime  # UTC datetime string
        self.end_datetime = end_datetime  # UTC datetime string
        self.status = status  # 'pending', 'approved', 'rejected', 'cancelled', 'completed'
        self.recurrence_rule = recurrence_rule  # iCal recurrence rule (e.g., "FREQ=WEEKLY;COUNT=3")
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        # Decision metadata (for audit trail on restricted resources)
        self.decision_notes = decision_notes  # Notes explaining approval/rejection
        self.decision_by = decision_by  # User ID of person who approved/rejected
        self.decision_timestamp = decision_timestamp  # When decision was made
        # Computed field (not in database, populated via SQL JOIN)
        self.requester_name = requester_name
    
    def to_dict(self):
        """Convert booking to dictionary"""
        return {
            'booking_id': self.booking_id,
            'resource_id': self.resource_id,
            'requester_id': self.requester_id,
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'status': self.status,
            'recurrence_rule': self.recurrence_rule,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'updated_at': self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            'decision_notes': self.decision_notes,
            'decision_by': self.decision_by,
            'decision_timestamp': self.decision_timestamp
        }


class Message:
    """Message model for user communication"""
    def __init__(self, message_id=None, thread_id=None, sender_id=None,
                 receiver_id=None, content=None, timestamp=None, is_flagged=0,
                 flag_reason=None, flagged_by=None, flagged_at=None, is_hidden=0):
        self.message_id = message_id
        self.thread_id = thread_id
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.is_flagged = bool(is_flagged)
        self.flag_reason = flag_reason
        self.flagged_by = flagged_by
        self.flagged_at = flagged_at
        self.is_hidden = bool(is_hidden)
    
    def to_dict(self):
        """Convert message to dictionary"""
        return {
            'message_id': self.message_id,
            'thread_id': self.thread_id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'is_flagged': self.is_flagged,
            'flag_reason': self.flag_reason,
            'flagged_by': self.flagged_by,
            'flagged_at': self.flagged_at,
            'is_hidden': self.is_hidden
        }


class Review:
    """Review model for resource ratings"""
    def __init__(self, review_id=None, resource_id=None, reviewer_id=None,
                 rating=None, comment=None, timestamp=None, is_flagged=0,
                 flag_reason=None, flagged_by=None, flagged_at=None, is_hidden=0):
        self.review_id = review_id
        self.resource_id = resource_id
        self.reviewer_id = reviewer_id
        self.rating = rating  # 1-5
        self.comment = comment
        self.timestamp = timestamp or datetime.now()
        self.is_flagged = bool(is_flagged)
        self.flag_reason = flag_reason
        self.flagged_by = flagged_by
        self.flagged_at = flagged_at
        self.is_hidden = bool(is_hidden)
    
    def to_dict(self):
        """Convert review to dictionary"""
        return {
            'review_id': self.review_id,
            'resource_id': self.resource_id,
            'reviewer_id': self.reviewer_id,
            'rating': self.rating,
            'comment': self.comment,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            'is_flagged': self.is_flagged,
            'flag_reason': self.flag_reason,
            'flagged_by': self.flagged_by,
            'flagged_at': self.flagged_at,
            'is_hidden': self.is_hidden
        }


class WaitlistEntry:
    """Waitlist model for tracking demand on fully booked resources"""
    def __init__(
        self,
        entry_id=None,
        resource_id=None,
        requester_id=None,
        start_datetime=None,
        end_datetime=None,
        status='active',
        recurrence_rule=None,
        created_at=None,
        processed_at=None,
        booking_id=None
    ):
        self.entry_id = entry_id
        self.resource_id = resource_id
        self.requester_id = requester_id
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.status = status  # 'active', 'promoted', 'cancelled'
        self.recurrence_rule = recurrence_rule
        self.created_at = created_at or datetime.now()
        self.processed_at = processed_at
        self.booking_id = booking_id

    def to_dict(self):
        """Convert waitlist entry to dictionary"""
        return {
            'entry_id': self.entry_id,
            'resource_id': self.resource_id,
            'requester_id': self.requester_id,
            'start_datetime': self.start_datetime,
            'end_datetime': self.end_datetime,
            'status': self.status,
            'recurrence_rule': self.recurrence_rule,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'processed_at': self.processed_at,
            'booking_id': self.booking_id
        }
