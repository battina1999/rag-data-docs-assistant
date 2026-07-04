"""Pydantic request/response models for the API (also power the OpenAPI docs)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1,
                          examples=["What is the grain of the fact_flights table?"])


class Citation(BaseModel):
    tag: str
    source: str
    title: str
    score: float
    snippet: str


class AskResponse(BaseModel):
    question: str
    answer: str
    grounded: bool = Field(..., description="True when the answer is supported by retrieved docs")
    provider: str
    citations: List[Citation]


class Health(BaseModel):
    status: str
    providers: dict
    index_ready: bool
    catalog_tables: int
