from __future__ import annotations

from pydantic import BaseModel, Field

from enum import Enum


class ActionExecutionFailed(BaseModel):
    """Error which indicates that an action execution failed.

    Attributes:
        action_name: Name of the action that failed.
        message: Message which describes the error.
    """

    action_name: str = Field(alias="action_name")
    message: str = Field(alias="message")


class ResourceNotFoundType(str, Enum):
    """Type of resource that was not found."""

    ACTION = "ACTION"
    DOMAIN = "DOMAIN"


class ResourceNotFound(BaseModel):
    """Error which indicates that a resource was not found.

    Attributes:
        action_name: Name of the action that was not found.
        message: Message which describes the error.
    """

    action_name: str = Field(alias="action_name")
    message: str = Field(alias="message")
    resource_type: ResourceNotFoundType = Field(alias="resource_type")
