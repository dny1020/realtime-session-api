"""
Tests for input validators
"""
import pytest
from app.validators import (
    PhoneNumberValidator,
    AsteriskContextValidator,
    AsteriskExtensionValidator,
    CallerIDValidator
)


class TestPhoneNumberValidator:
    """Test phone number validation"""
    
    def test_valid_e164(self):
        """Valid E.164 format should pass"""
        assert PhoneNumberValidator.validate("+14155552671") == "+14155552671"
        assert PhoneNumberValidator.validate("+441234567890") == "+441234567890"
        assert PhoneNumberValidator.validate("+12025551234") == "+12025551234"
    
    def test_removes_formatting(self):
        """Should remove formatting characters"""
        assert PhoneNumberValidator.validate("+1 (415) 555-2671") == "+14155552671"
        assert PhoneNumberValidator.validate("+1-415-555-2671") == "+14155552671"
        assert PhoneNumberValidator.validate("+1.415.555.2671") == "+14155552671"
    
    def test_rejects_too_short(self):
        """Should reject numbers that are too short"""
        with pytest.raises(ValueError, match="Invalid phone number format"):
            PhoneNumberValidator.validate("+123")
        
        with pytest.raises(ValueError, match="Invalid phone number format"):
            PhoneNumberValidator.validate("+1234")
    
    def test_rejects_too_long(self):
        """Should reject numbers that are too long"""
        with pytest.raises(ValueError, match="Invalid phone number format"):
            PhoneNumberValidator.validate("+1234567890123456")  # 16 digits
    
    def test_rejects_missing_plus(self):
        """Should reject numbers without leading +"""
        with pytest.raises(ValueError, match="Invalid phone number format"):
            PhoneNumberValidator.validate("14155552671")
    
    def test_rejects_invalid_characters(self):
        """Should reject numbers with invalid characters after cleaning"""
        with pytest.raises(ValueError, match="Invalid phone number format"):
            PhoneNumberValidator.validate("notaphone")
        
        # This passes because letters are stripped: "+1415abc5552671" -> "+14155552671"
        # Which is valid. Test that truly invalid input fails:
        with pytest.raises(ValueError, match="Invalid phone number format"):
            PhoneNumberValidator.validate("abc")  # No digits at all


class TestAsteriskContextValidator:
    """Test Asterisk context validation"""
    
    def test_valid_contexts(self):
        """Valid context names should pass"""
        assert AsteriskContextValidator.validate("outbound-ivr") == "outbound-ivr"
        assert AsteriskContextValidator.validate("incoming_calls") == "incoming_calls"
        assert AsteriskContextValidator.validate("default") == "default"
        assert AsteriskContextValidator.validate("test123") == "test123"
    
    def test_rejects_empty(self):
        """Should reject empty context"""
        with pytest.raises(ValueError, match="Context cannot be empty"):
            AsteriskContextValidator.validate("")
    
    def test_rejects_injection_attempts(self):
        """Should reject potential injection attacks"""
        with pytest.raises(ValueError, match="Only alphanumeric"):
            AsteriskContextValidator.validate("context; DROP TABLE;")
        
        with pytest.raises(ValueError, match="Only alphanumeric"):
            AsteriskContextValidator.validate("context/../etc/passwd")
        
        with pytest.raises(ValueError, match="Only alphanumeric"):
            AsteriskContextValidator.validate("context${EXTEN}")
        
        with pytest.raises(ValueError, match="Only alphanumeric"):
            AsteriskContextValidator.validate("context|/bin/sh")
    
    def test_rejects_special_characters(self):
        """Should reject special characters"""
        with pytest.raises(ValueError, match="Only alphanumeric"):
            AsteriskContextValidator.validate("context with spaces")
        
        with pytest.raises(ValueError, match="Only alphanumeric"):
            AsteriskContextValidator.validate("context@domain")
        
        with pytest.raises(ValueError, match="Only alphanumeric"):
            AsteriskContextValidator.validate("context:123")
    
    def test_rejects_too_long(self):
        """Should reject contexts longer than 64 chars"""
        long_context = "a" * 65
        with pytest.raises(ValueError, match="Context too long"):
            AsteriskContextValidator.validate(long_context)


class TestAsteriskExtensionValidator:
    """Test Asterisk extension validation"""
    
    def test_valid_extensions(self):
        """Valid extensions should pass"""
        assert AsteriskExtensionValidator.validate("s") == "s"
        assert AsteriskExtensionValidator.validate("1000") == "1000"
        assert AsteriskExtensionValidator.validate("extension1") == "extension1"
    
    def test_rejects_empty(self):
        """Should reject empty extension"""
        with pytest.raises(ValueError, match="Extension cannot be empty"):
            AsteriskExtensionValidator.validate("")
    
    def test_rejects_special_characters(self):
        """Should reject special characters"""
        with pytest.raises(ValueError, match="Only alphanumeric"):
            AsteriskExtensionValidator.validate("ext-123")
        
        with pytest.raises(ValueError, match="Only alphanumeric"):
            AsteriskExtensionValidator.validate("ext_123")
    
    def test_rejects_too_long(self):
        """Should reject extensions longer than 32 chars"""
        long_ext = "a" * 33
        with pytest.raises(ValueError, match="Extension too long"):
            AsteriskExtensionValidator.validate(long_ext)


class TestCallerIDValidator:
    """Test caller ID sanitization"""
    
    def test_sanitizes_valid_inputs(self):
        """Should allow valid caller ID formats"""
        assert CallerIDValidator.sanitize("John Doe") == "John Doe"
        assert CallerIDValidator.sanitize("Sales <555-1234>") == "Sales <555-1234>"
        assert CallerIDValidator.sanitize("Support (Main Line)") == "Support (Main Line)"
    
    def test_removes_dangerous_characters(self):
        """Should remove potentially dangerous characters"""
        assert CallerIDValidator.sanitize("Test;DROP TABLE") == "TestDROP TABLE"
        assert CallerIDValidator.sanitize("Name|command") == "Namecommand"
        assert CallerIDValidator.sanitize("Test&test") == "Testtest"
    
    def test_handles_empty_input(self):
        """Should return default for empty input"""
        assert CallerIDValidator.sanitize("") == "Outbound Call"
        assert CallerIDValidator.sanitize(None) == "Outbound Call"
    
    def test_truncates_long_input(self):
        """Should truncate to 128 characters"""
        long_caller_id = "A" * 200
        result = CallerIDValidator.sanitize(long_caller_id)
        assert len(result) == 128
