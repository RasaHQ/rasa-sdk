"""
Protobuf version compatibility shims.

This module provides compatibility functions to handle differences between
protobuf 4.x and 5.x versions.
"""

import google.protobuf
from packaging import version


def get_protobuf_version():
    """Get the current protobuf version."""
    return version.parse(google.protobuf.__version__)


def is_protobuf_v5():
    """Check if we're running protobuf 5.x or later."""
    return get_protobuf_version() >= version.parse("5.0.0")


def is_protobuf_v4():
    """Check if we're running protobuf 4.x."""
    return version.parse("4.0.0") <= get_protobuf_version() < version.parse("5.0.0")


def get_protobuf_version_info():
    """Get detailed protobuf version information for debugging."""
    pb_version = get_protobuf_version()
    return {
        "version": str(pb_version),
        "is_v4": is_protobuf_v4(),
        "is_v5": is_protobuf_v5(),
        "major": pb_version.major,
        "minor": pb_version.minor,
        "micro": pb_version.micro,
    }
