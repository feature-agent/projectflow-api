"""Project request/response schemas."""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    owner_id: uuid.UUID


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    status: Optional[str] = Field(None, min_length=1, max_length=20)


class ProjectResponse(BaseModel):
    """Schema for project response data."""

    id: uuid.UUID
    name: str
    description: Optional[str]
    status: str
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Schema for a list of projects."""

    projects: List[ProjectResponse]
