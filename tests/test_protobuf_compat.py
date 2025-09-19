"""Tests for protobuf compatibility shims."""

import pytest
from unittest.mock import patch

from rasa_sdk.protobuf_compat import (
    get_protobuf_version,
    is_protobuf_v4,
    is_protobuf_v5,
    get_protobuf_version_info,
)


class TestProtobufCompatibility:
    """Test protobuf version compatibility functions."""

    def test_get_protobuf_version(self):
        """Test getting protobuf version."""
        version = get_protobuf_version()
        assert version is not None
        assert hasattr(version, 'major')
        assert hasattr(version, 'minor')
        assert hasattr(version, 'micro')

    def test_is_protobuf_v4(self):
        """Test protobuf v4 detection."""
        with patch('rasa_sdk.protobuf_compat.get_protobuf_version') as mock_version:
            # Test v4 detection
            mock_version.return_value.major = 4
            mock_version.return_value.minor = 25
            mock_version.return_value.micro = 8

            assert is_protobuf_v4() is True
            assert is_protobuf_v5() is False

    def test_is_protobuf_v5(self):
        """Test protobuf v5 detection."""
        with patch('rasa_sdk.protobuf_compat.get_protobuf_version') as mock_version:
            # Test v5 detection
            mock_version.return_value.major = 5
            mock_version.return_value.minor = 29
            mock_version.return_value.micro = 5

            assert is_protobuf_v4() is False
            assert is_protobuf_v5() is True

    def test_get_protobuf_version_info(self):
        """Test getting detailed version info."""
        with patch('rasa_sdk.protobuf_compat.get_protobuf_version') as mock_version:
            mock_version.return_value.major = 4
            mock_version.return_value.minor = 25
            mock_version.return_value.micro = 8
            mock_version.return_value = "4.25.8"

            info = get_protobuf_version_info()

            assert info["version"] == "4.25.8"
            assert info["major"] == 4
            assert info["minor"] == 25
            assert info["micro"] == 8
            assert info["is_v4"] is True
            assert info["is_v5"] is False

    def test_version_info_v5(self):
        """Test version info for protobuf v5."""
        with patch('rasa_sdk.protobuf_compat.get_protobuf_version') as mock_version:
            mock_version.return_value.major = 5
            mock_version.return_value.minor = 29
            mock_version.return_value.micro = 5
            mock_version.return_value = "5.29.5"

            info = get_protobuf_version_info()

            assert info["version"] == "5.29.5"
            assert info["major"] == 5
            assert info["minor"] == 29
            assert info["micro"] == 5
            assert info["is_v4"] is False
            assert info["is_v5"] is True
