"""
Input validators for API endpoints

Prevents injection attacks and validates data formats.
"""
import re
from typing import Optional


class PhoneNumberValidator:
    """Validate and sanitize phone numbers"""
    
    @staticmethod
    def validate(phone: str) -> str:
        """
        Validate E.164 format: +[country][number]
        
        Args:
            phone: Phone number string
            
        Returns:
            Cleaned phone number in E.164 format
            
        Raises:
            ValueError: If phone number format is invalid
        """
        # Remove all non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Must start with + and have 7-15 digits
        if not re.match(r'^\+\d{7,15}$', cleaned):
            raise ValueError(
                f"Invalid phone number format. Expected E.164: +[country][number]. Got: {phone}"
            )
        
        return cleaned


class AsteriskContextValidator:
    """Prevent injection in Asterisk contexts"""
    
    ALLOWED_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    @staticmethod
    def validate(value: str) -> str:
        """
        Validate Asterisk context name
        
        Only allow alphanumeric, underscore, and hyphen to prevent injection attacks.
        
        Args:
            value: Context name
            
        Returns:
            Validated context name
            
        Raises:
            ValueError: If context contains invalid characters
        """
        if not value:
            raise ValueError("Context cannot be empty")
        
        if not AsteriskContextValidator.ALLOWED_PATTERN.match(value):
            raise ValueError(
                f"Invalid context '{value}'. Only alphanumeric, underscore, and hyphen allowed."
            )
        
        if len(value) > 64:
            raise ValueError("Context too long (max 64 chars)")
        
        return value


class AsteriskExtensionValidator:
    """Validate Asterisk extension"""
    
    ALLOWED_PATTERN = re.compile(r'^[a-zA-Z0-9]+$')
    
    @staticmethod
    def validate(value: str) -> str:
        """
        Validate Asterisk extension
        
        Args:
            value: Extension (e.g., 's', '1000')
            
        Returns:
            Validated extension
            
        Raises:
            ValueError: If extension is invalid
        """
        if not value:
            raise ValueError("Extension cannot be empty")
        
        if not AsteriskExtensionValidator.ALLOWED_PATTERN.match(value):
            raise ValueError(
                f"Invalid extension '{value}'. Only alphanumeric characters allowed."
            )
        
        if len(value) > 32:
            raise ValueError("Extension too long (max 32 chars)")
        
        return value


class CallerIDValidator:
    """Sanitize caller ID to prevent Asterisk injection"""
    
    @staticmethod
    def sanitize(value: str) -> str:
        """
        Sanitize caller ID string
        
        Remove special characters that could break Asterisk dialplan.
        
        Args:
            value: Caller ID string
            
        Returns:
            Sanitized caller ID
        """
        if not value:
            return "Outbound Call"
        
        # Remove special characters that could break Asterisk
        # Allow: alphanumeric, spaces, <, >, (, ), -
        sanitized = re.sub(r'[^\w\s<>()-]', '', value)
        
        # Limit length
        return sanitized[:128]
