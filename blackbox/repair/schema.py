"""Structured patch proposals and repair outcome vocabulary."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Bounds are part of the JSON schema sent to the model, so constrained decoding cannot emit an
# unbounded patch. Validation applies the same limits.
PATCH_CHANGE_LIMIT = 3
PATCH_TEXT_LIMIT = 2000

RepairStatus = Literal[
    'ELIGIBILITY_BLOCKED', 'UNVERIFIED', 'ENVIRONMENT_FAILED', 'SECURITY_BLOCKED', 'GENERATION_FAILED',
    'PATCH_REJECTED', 'PATCH_FAILED', 'VERIFIED_IN_TEST_ENVIRONMENT',
]


class PatchChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    path: str = Field(min_length=1, max_length=256)
    find: str = Field(min_length=1, max_length=PATCH_TEXT_LIMIT)
    replace: str = Field(max_length=PATCH_TEXT_LIMIT)
    explanation: str = Field(min_length=1, max_length=500)


class PatchProposal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    summary: str = Field(min_length=1, max_length=1000)
    changes: list[PatchChange] = Field(min_length=1, max_length=PATCH_CHANGE_LIMIT)
    risks: list[str] = Field(default_factory=list, max_length=3)
