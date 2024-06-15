from __future__ import annotations

from pydantic import BaseModel, Field

from enum import Enum


class ResourceNotFoundType(str, Enum):
    """Type of resource that was not found."""
    ACTION = "ACTION"
    DOMAIN = "DOMAIN"


class ResourceNotFound(BaseModel):
    """Error which indicates that a resource was not found."""
    action_name: str = Field(alias="action_name")
    message: str = Field(alias="message")
    resource_type: ResourceNotFoundType = Field(alias="resource_type")
