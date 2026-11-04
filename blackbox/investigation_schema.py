from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Claim(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=2000)
    evidence_ids: list[str] = Field(max_length=20)


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra='forbid')
    explanation: str = Field(min_length=1, max_length=2000)
    supporting_evidence: list[str] = Field(max_length=20)
    contradicting_evidence: list[str] = Field(max_length=20)


class Findings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    outcome: Literal['ROOT_CAUSE_SUPPORTED', 'LIKELY_CAUSE', 'INSUFFICIENT_EVIDENCE', 'INVESTIGATION_FAILED']
    observed_failure: Claim
    observed_facts: list[Claim] = Field(default_factory=list, max_length=20)
    hypotheses: list[Hypothesis] = Field(default_factory=list, max_length=10)
    alternatives: list[Hypothesis] = Field(default_factory=list, max_length=10)
    missing_evidence: list[str] = Field(default_factory=list, max_length=20)
    verification_steps: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode='after')
    def validate_claims(self):
        if not self.observed_failure.evidence_ids or any(not x.evidence_ids for x in self.observed_facts):
            raise ValueError('every observed fact must cite evidence')
        if self.outcome in ('ROOT_CAUSE_SUPPORTED', 'LIKELY_CAUSE') and not self.hypotheses:
            raise ValueError('a diagnosis needs a hypothesis')
        if self.outcome in ('INSUFFICIENT_EVIDENCE', 'INVESTIGATION_FAILED') and self.hypotheses:
            raise ValueError('abstention and failure cannot assert a primary cause')
        if self.outcome in ('INSUFFICIENT_EVIDENCE', 'INVESTIGATION_FAILED') and not self.missing_evidence:
            raise ValueError('abstention and failure require an explanation of missing evidence')
        if not self.verification_steps:
            raise ValueError('verification steps are required')
        if any(not x.supporting_evidence for x in self.hypotheses):
            raise ValueError('each primary hypothesis must cite supporting evidence')
        return self


class InvestigationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    consent_external: bool = False
    reviewed_evidence_hash: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    force: bool = False
