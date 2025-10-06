"""Simple test configuration"""
import pytest
import os

# Set test environment variables
os.environ["DISABLE_DB"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["ARI_HTTP_URL"] = "http://test-asterisk:8088/ari"
os.environ["ARI_USERNAME"] = "test"
os.environ["ARI_PASSWORD"] = "test"
