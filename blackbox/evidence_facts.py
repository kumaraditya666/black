"""Deterministic facts from a recorded snapshot, not proof of runtime causation."""
import ast
import textwrap
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class AtomicClaim(BaseModel):
    model_config = ConfigDict(extra='forbid')
    category: Literal['exception_type', 'exception_message', 'commit', 'frame_order', 'frame_function', 'frame_location',
                      'source_statement', 'division_denominator', 'static_call']
    value: str = Field(max_length=3000)
    evidence_ids: list[str] = Field(min_length=1)
    verification_status: Literal['RECORDED', 'VERIFIED_SOURCE', 'STATIC_ONLY', 'CONTRADICTED', 'UNVERIFIABLE']
    limitations: str


def _division_denominator(source: str) -> str | None:
    try:
        node = ast.parse(textwrap.dedent(source))
        divisions = [n for n in ast.walk(node) if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Div, ast.FloorDiv))]
        return ast.unparse(divisions[0].right) if len(divisions) == 1 else None
    except (SyntaxError, ValueError, RecursionError):
        return None


def extract_facts(snapshot: dict) -> list[dict]:
    facts = []
    def add(category, value, evidence_id, status, limitations):
        facts.append(AtomicClaim(category=category, value=str(value), evidence_ids=[evidence_id],
                                 verification_status=status, limitations=limitations).model_dump())
    for item in snapshot['evidence']:
        ref = item['id']
        if item['type'] == 'event':
            for category, key in [('exception_type', 'exception_type'), ('exception_message', 'message'), ('commit', 'commit')]:
                add(category, item[key], ref, 'RECORDED', 'Client-reported event data; not independently verified execution.')
        elif item['type'] == 'stack_frame':
            add('frame_order', ref.split(':', 1)[1], ref, 'RECORDED', 'Order within the retained client-reported stack; earlier frames may be omitted.')
            add('frame_function', item['function'], ref, 'RECORDED', 'Function name and order are reported by the client.')
            add('frame_location', f"{item['path']}:{item['line']}", ref, 'RECORDED', 'Reported stack location; source resolution is separate.')
            if item['status'] == 'resolved':
                add('source_statement', item['source_line'], ref, 'VERIFIED_SOURCE', 'Line read from the recorded Git revision; does not prove execution.')
                denominator = _division_denominator(item['source_line'])
                if denominator:
                    add('division_denominator', denominator, ref, 'VERIFIED_SOURCE', 'Single-line AST division operand; not runtime value or causality.')
        elif item['type'] == 'static_call':
            add('static_call', f"{item['caller']} -> {item['callee']}", ref, 'STATIC_ONLY', item['notice'])
    return facts


def check_atomic_claim(category: str, value: str, evidence_ids: list[str], facts: list[dict]) -> dict:
    """Compare typed values only against the specifically cited extracted records."""
    candidates = [f for f in facts if f['category'] == category and set(f['evidence_ids']).issubset(evidence_ids)]
    if not candidates:
        status = 'UNVERIFIABLE'
    elif any(f['value'] == value for f in candidates):
        status = candidates[0]['verification_status']
    else:
        status = 'CONTRADICTED'
    return {'category': category, 'value': value, 'evidence_ids': evidence_ids,
            'verification_status': status, 'limitations': 'Exact typed comparison only; not causal entailment.'}
