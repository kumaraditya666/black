"""Evaluation-only layered findings schema; never imported by production routes."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Claim(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text: str = Field(min_length=1,max_length=1200)
    evidence_ids: list[str] = Field(min_length=1,max_length=12)

class Mechanism(BaseModel):
    model_config=ConfigDict(extra='forbid')
    explanation: str = Field(min_length=1,max_length=1200)
    supporting_evidence: list[str] = Field(min_length=1,max_length=12)
    missing_evidence: list[str] = Field(max_length=12)

class Attribution(BaseModel):
    model_config=ConfigDict(extra='forbid')
    status: Literal['ESTABLISHED','NOT_ESTABLISHED','CONTRADICTED']
    explanation: str = Field(min_length=1,max_length=1200)
    evidence_ids: list[str] = Field(min_length=1,max_length=12)
    missing_evidence: list[str] = Field(max_length=12)

class LayeredFindings(BaseModel):
    model_config=ConfigDict(extra='forbid')
    outcome: Literal['LIKELY_CAUSE','INSUFFICIENT_EVIDENCE']
    static_code_facts: list[Claim] = Field(max_length=4)
    runtime_observations: list[Claim] = Field(max_length=4)
    behavioral_contract: list[Claim] = Field(max_length=3)
    mechanism_hypotheses: list[Mechanism] = Field(max_length=4)
    causal_attribution: Attribution
    uncertainties: list[Claim] = Field(max_length=4)

def validate_layered(raw: dict, evidence: list[dict]) -> LayeredFindings:
    result=LayeredFindings.model_validate(raw)
    by_id={x['id']:x for x in evidence}
    groups=((result.static_code_facts,{'code_context','stack_frame'}),
            (result.runtime_observations,{'event'}),
            (result.behavioral_contract,{'documentation'}))
    refs=[]
    for claims,allowed in groups:
        for claim in claims:
            for ref in claim.evidence_ids:
                if ref not in by_id or by_id[ref].get('type') not in allowed:
                    raise ValueError('citation evidence type mismatch')
                refs.append(ref)
    for h in result.mechanism_hypotheses:
        for ref in h.supporting_evidence:
            if ref not in by_id or by_id[ref].get('type') not in {'code_context','stack_frame'}:
                raise ValueError('mechanism citation must be pinned source')
            refs.append(ref)
        for ref in h.missing_evidence:
            if ref not in by_id: raise ValueError('unknown missing-evidence ID')
            refs.append(ref)
    for c in result.uncertainties:
        if any(ref not in by_id for ref in c.evidence_ids): raise ValueError('unknown uncertainty citation')
        refs.extend(c.evidence_ids)
    a=result.causal_attribution
    if any(ref not in by_id for ref in a.evidence_ids+a.missing_evidence):
        raise ValueError('unknown attribution citation')
    if a.status=='ESTABLISHED' and not any(by_id[x].get('type')=='runtime_telemetry' for x in a.evidence_ids):
        raise ValueError('causal attribution lacks authenticated runtime telemetry')
    if a.status=='NOT_ESTABLISHED' and not a.missing_evidence:
        raise ValueError('unestablished attribution must name missing evidence')
    if result.outcome=='INSUFFICIENT_EVIDENCE' and result.mechanism_hypotheses:
        # Layered outcome describes incident attribution; local mechanisms remain separately reportable.
        pass
    return result
