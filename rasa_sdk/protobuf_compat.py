"""
Protobuf version compatibility shims.

This module provides compatibility functions to handle differences between
protobuf 4.x and 5.x versions, including dependency version management.
"""

import google.protobuf
from packaging import version
import warnings


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


def check_mutually_exclusive_groups():
    """
    Check if both pb4 and pb5 groups are installed simultaneously.

    This function raises an error if both protobuf groups are detected,
    as they are mutually exclusive.
    """
    try:
        import grpcio
        grpcio_version = version.parse(grpcio.__version__)
        pb_version = get_protobuf_version()

        # Check for conflicting installations
        if is_protobuf_v4() and grpcio_version >= version.parse("1.66.0"):
            raise RuntimeError(
                "Conflicting protobuf groups detected! "
                "You have protobuf 4.x installed with grpcio >=1.66.0 (from pb5 group). "
                "Please install only one protobuf group: either 'poetry install --with pb4' "
                "or 'poetry install --with pb5', but not both."
            )
        elif is_protobuf_v5() and grpcio_version < version.parse("1.66.0"):
            raise RuntimeError(
                "Conflicting protobuf groups detected! "
                "You have protobuf 5.x installed with grpcio <1.66.0 (from pb4 group). "
                "Please install only one protobuf group: either 'poetry install --with pb4' "
                "or 'poetry install --with pb5', but not both."
            )
    except ImportError:
        # grpcio not installed, no conflict possible
        pass


def check_dependency_compatibility():
    """
    Check if the installed dependencies are compatible with the current protobuf version.

    This function warns users if they have incompatible dependency versions.
    """
    # First check for mutually exclusive groups
    check_mutually_exclusive_groups()

    pb_version = get_protobuf_version()

    if is_protobuf_v4():
        # For protobuf 4.x, we expect older versions of grpcio and opentelemetry
        try:
            import grpcio
            grpcio_version = version.parse(grpcio.__version__)
            if grpcio_version >= version.parse("1.66.0"):
                warnings.warn(
                    f"Protobuf {pb_version} detected with grpcio {grpcio_version}. "
                    "For protobuf 4.x, consider using grpcio~=1.60.0 for better compatibility.",
                    UserWarning
                )
        except ImportError:
            pass

    elif is_protobuf_v5():
        # For protobuf 5.x, we expect newer versions
        try:
            import grpcio
            grpcio_version = version.parse(grpcio.__version__)
            if grpcio_version < version.parse("1.66.0"):
                warnings.warn(
                    f"Protobuf {pb_version} detected with grpcio {grpcio_version}. "
                    "For protobuf 5.x, consider using grpcio~=1.66.2 for better compatibility.",
                    UserWarning
                )
        except ImportError:
            pass


def get_recommended_dependencies():
    """
    Get recommended dependency versions for the current protobuf version.
    
    Returns:
        dict: Dictionary with recommended package versions
    """
    if is_protobuf_v4():
        return {
            "grpcio": "~1.60.0",
            "grpcio-tools": "~1.60.0",
            "opentelemetry-sdk": "~1.27.0",
            "opentelemetry-exporter-otlp": "~1.27.0",
            "opentelemetry-api": "~1.27.0",
        }
    else:  # protobuf 5.x
        return {
            "grpcio": "~1.66.2",
            "grpcio-tools": "~1.66.2",
            "opentelemetry-sdk": "~1.37.0",
            "opentelemetry-exporter-otlp": "~1.37.0",
            "opentelemetry-api": "~1.37.0",
        }
