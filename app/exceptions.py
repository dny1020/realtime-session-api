"""Custom exceptions for the Contact Center API"""


class ContactCenterException(Exception):
    """Base exception for Contact Center API"""
    pass


class AsteriskConnectionError(ContactCenterException):
    """Raised when Asterisk ARI is unavailable or connection fails"""
    pass


class CallOriginationError(ContactCenterException):
    """Raised when call origination fails"""
    pass


class DatabaseError(ContactCenterException):
    """Raised when database operations fail"""
    pass


class AuthenticationError(ContactCenterException):
    """Raised when authentication fails"""
    pass


class RateLimitExceeded(ContactCenterException):
    """Raised when rate limit is exceeded"""
    pass
