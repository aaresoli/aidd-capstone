"""
Utility helpers for role and ownership checks.
Keeps RBAC logic centralized so controllers stay lean.
"""
from flask_login import current_user


def user_has_role(*roles):
    """Return True if the current user has one of the supplied roles."""
    return bool(current_user.is_authenticated and current_user.role in roles)


def is_admin():
    """Convenience helper for admin checks."""
    return user_has_role('admin')


def is_staff():
    """Convenience helper for staff checks (includes admins)."""
    return user_has_role('staff', 'admin')


def owns_resource(resource):
    """Return True if the current user owns the provided resource."""
    if not resource or not current_user.is_authenticated:
        return False
    return resource.owner_id == current_user.user_id


def can_manage_resource(resource):
    """
    Check if current user can manage (edit/delete) a resource.
    
    Resource owners can always manage their own resources. Admins have
    universal management privileges. This is used for edit/delete operations
    and booking approval workflows.
    
    Args:
        resource: Resource model instance to check
        
    Returns:
        bool: True if user can manage the resource, False otherwise
    """
    return is_admin() or owns_resource(resource)


def can_view_booking(booking, resource):
    """
    Check if current user can view booking details.
    
    Users can view their own bookings (as requester). Resource owners and
    admins can view any booking for their resources. This provides privacy
    while allowing necessary oversight.
    
    Args:
        booking: Booking model instance to check
        resource: Resource model instance associated with the booking
        
    Returns:
        bool: True if user can view the booking, False otherwise
    """
    if not current_user.is_authenticated:
        return False
    # Requesters can always view their own bookings
    if booking and booking.requester_id == current_user.user_id:
        return True
    # Resource owners and admins can view bookings for their resources
    return can_manage_resource(resource)


def can_act_on_booking(resource):
    """
    Check if current user can approve/reject bookings for a resource.
    
    Used for booking review workflows. Only resource owners and admins
    can make approval decisions. This determines if approve/reject buttons
    should be shown in the UI.
    
    Args:
        resource: Resource model instance to check
        
    Returns:
        bool: True if user can approve/reject bookings, False otherwise
    """
    return can_manage_resource(resource)
