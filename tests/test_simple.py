"""Simple tests - Basic functionality"""
import pytest


def test_import_main():
    """Test that main module can be imported"""
    from app import main
    assert main is not None


def test_import_settings():
    """Test that settings can be loaded"""
    from config.settings import get_settings
    settings = get_settings()
    assert settings is not None
    assert settings.secret_key == "test-secret-key-for-testing-only"


def test_import_asterisk_service():
    """Test that asterisk service can be imported"""
    from app.services.asterisk import AsteriskService
    service = AsteriskService()
    assert service is not None


def test_import_models():
    """Test that models can be imported"""
    from app.models.call import Call, CallStatus
    assert Call is not None
    assert CallStatus is not None


def test_call_status_enum():
    """Test call status enum values"""
    from app.models import CallStatus
    assert CallStatus.PENDING.value == "pending"
    assert CallStatus.DIALING.value == "dialing"
    assert CallStatus.RINGING.value == "ringing"
    assert CallStatus.ANSWERED.value == "answered"
    assert CallStatus.COMPLETED.value == "completed"
    assert CallStatus.FAILED.value == "failed"
