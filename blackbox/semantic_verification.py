"""Mechanical provenance checks and honest separation of causal interpretation.

A client report and a test result are distinct records. A matching source line or citation does
not prove that code executed, or that an arbitrary natural-language hypothesis is true.
"""
import re
from pathlib import Path
from .redaction import redact
from .repository_intelligence import _git, _safe_path


def _check_source(repo, item, expected_commit):
    path=item.get('path'); commit=item.get('commit'); start=item.get('line'); end=item.get('end_line',start)
    if commit!=expected_commit or not re.fullmatch(r'[0-9a-f]{40}',str(commit)) or not _safe_path(path):
        return 'UNVERIFIABLE'
    if not isinstance(start,int) or not isinstance(end,int) or start<1 or end<start or end-start>1000:
        return 'UNVERIFIABLE'
    try:
        tree=_git(repo,'ls-tree','-z',commit,'--',':(literal)'+path)
        parts=tree.stdout.rstrip(b'\0').split(b'\t',1)
        if tree.returncode or len(parts)!=2 or parts[1].decode('utf8')!=path or not parts[0].startswith((b'100644 blob ',b'100755 blob ')):
            return 'UNVERIFIABLE'
        size=_git(repo,'cat-file','-s',commit+':'+path)
        if size.returncode or not size.stdout.strip().isdigit() or int(size.stdout)>65536:
            return 'UNVERIFIABLE'
        blob=_git(repo,'show',commit+':'+path)
        if blob.returncode or b'\0' in blob.stdout: return 'UNVERIFIABLE'
        lines=blob.stdout.decode('utf8').splitlines()
        if end>len(lines): return 'CONTRADICTED'
        actual=redact('\n'.join(lines[start-1:end]))
        expected=item.get('source') if item.get('type')=='code_context' else item.get('source_line')
        return 'VERIFIED_SOURCE' if expected==actual else 'CONTRADICTED'
    except Exception:
        return 'UNVERIFIABLE'


def assess_snapshot(repo: Path, snapshot: dict, hypotheses=()) -> dict:
    """Check record/source identity; leave model-authored causal claims unverified."""
    evidence=snapshot.get('evidence',[]); event=next((e for e in evidence if e.get('type')=='event'),None)
    if not event:
        return {'observed_failure':None,'immediate_mechanism':{'status':'UNVERIFIABLE'},
                'upstream_root_cause':{'status':'INSUFFICIENT_EVIDENCE'},'claims':[]}
    by_id={item.get('id'):item for item in evidence}; commit=event.get('commit'); claims=[]
    def add(category, ids, status, locations=(), assumption=None, mechanically_verifiable=True, value=None):
        claims.append({'category':category,'value':redact(str(value))[:2000] if value is not None else None,'supporting_evidence_ids':list(ids),
                       'source_locations':list(locations),'mechanically_verifiable':mechanically_verifiable,
                       'verification_outcome':status,'unsupported_assumptions':[assumption] if assumption else []})
    add('EXCEPTION_TYPE',[event['id']],'RECORDED',assumption='Client report does not establish execution.',value=event.get('exception_type'))
    try:
        rev=_git(repo,'cat-file','-t',commit) if re.fullmatch(r'[0-9a-f]{40}',str(commit)) else None
        rev_status='VERIFIED_SOURCE' if rev and rev.returncode==0 and rev.stdout.strip()==b'commit' else 'UNVERIFIABLE'
    except Exception: rev_status='UNVERIFIABLE'
    add('SOURCE_REVISION',[event['id']],rev_status,assumption='Revision existence does not establish runtime execution.',value=commit)
    for item in evidence:
        if item.get('type') not in ('stack_frame','code_context'): continue
        loc={'path':item.get('path'),'line':item.get('line'),'commit':item.get('commit')}
        if item['type']=='stack_frame':
            add('RECORDED_STACK_FRAME',[item['id']],'RECORDED',[loc],
                'Frame was supplied by the event; execution is not independently established.',value=item.get('function'))
        status=_check_source(repo,item,commit)
        add('SOURCE_EXCERPT' if item['type']=='code_context' else 'SOURCE_LINE',
            [item['id']],status,[loc], 'Source and static relationships do not establish runtime execution.',value=item.get('source') if item['type']=='code_context' else item.get('source_line'))
    for hypothesis in hypotheses:
        ids=hypothesis.get('supporting_evidence',[])
        locations=[{'path':by_id[i].get('path'),'line':by_id[i].get('line'),
                    'commit':by_id[i].get('commit')} for i in ids if i in by_id and by_id[i].get('path')]
        add('CAUSAL_HYPOTHESIS',ids,'UNVERIFIABLE',locations,
            'Citation existence does not verify natural-language mechanism or upstream cause.',False, value=hypothesis.get('explanation'))
    return {'observed_failure':{'status':'RECORDED','evidence_ids':[event['id']],
                                'exception_type':event.get('exception_type'),
                                'notice':'Client-reported; runtime execution is not verified.'},
            'immediate_mechanism':{'status':'HYPOTHESIS_REQUIRES_REVIEW' if hypotheses else 'INSUFFICIENT_EVIDENCE',
                                   'notice':'Model hypotheses are not reliably classified as immediate mechanisms; no free-text mechanism is mechanically established.'},
            'upstream_root_cause':{'status':'INSUFFICIENT_EVIDENCE',
                                   'notice':'A model hypothesis and citations do not independently verify upstream causation.'},
            'claims':claims}


def review_hypotheses(findings: dict, assessment: dict) -> dict:
    """One bounded check of provenance and missing evidence; never certify causal prose."""
    checked={c['supporting_evidence_ids'][0]:c for c in assessment.get('claims',[])
             if c.get('category') in ('SOURCE_LINE','SOURCE_EXCERPT') and c.get('supporting_evidence_ids')}
    reviews=[]
    for h in findings.get('hypotheses',[])[:3]:
        refs=h.get('supporting_evidence',[])
        checks=[{'evidence_id':ref,'source_status':checked[ref]['verification_outcome']}
                for ref in refs if ref in checked]
        reviews.append({'claim':h.get('explanation',''), 'claim_type':'UNCLASSIFIED_CAUSAL_HYPOTHESIS',
                        'supporting_evidence_ids':refs, 'source_checks':checks,
                        'decision':'QUALIFIED_REQUIRES_REVIEW',
                        'limitation':'Source identity and citation presence do not prove causality.'})
    return {'steps':['inspect_recorded_evidence','check_pinned_source_identity'],
            'hypotheses':reviews,'omitted_hypotheses':max(0,len(findings.get('hypotheses',[]))-3),
            'missing_evidence':findings.get('missing_evidence',[])[:3],
            'proposed_verification_experiments':findings.get('verification_steps',[])[:3],
            'notice':'Suggestions are untrusted text; no commands are executed.'}


def reconcile_facts(facts: list[dict], assessment: dict) -> list[dict]:
    """Never leave legacy VERIFIED_SOURCE claims verified when rechecking failed."""
    checks={c['supporting_evidence_ids'][0]:c['verification_outcome']
            for c in assessment.get('claims',[]) if c['category']=='SOURCE_LINE' and c['supporting_evidence_ids']}
    result=[]
    for original in facts:
        fact=dict(original)
        if fact.get('verification_status')=='VERIFIED_SOURCE':
            outcomes=[checks.get(i,'UNVERIFIABLE') for i in fact.get('evidence_ids',[])]
            if not outcomes or any(x!='VERIFIED_SOURCE' for x in outcomes):
                fact['verification_status']='CONTRADICTED' if 'CONTRADICTED' in outcomes else 'UNVERIFIABLE'
                fact['limitations']='Pinned source could not be independently matched to this snapshot.'
        result.append(fact)
    return result


def assess_execution(record: dict, fixture: dict) -> dict:
    """Describe recorded, gated test outcomes; a failed reproduction is not historical disproof."""
    validation=record.get('validation') or {}; checks=(validation.get('eligibility') or {}).get('checks',[])
    passed={x.get('code') for x in checks if x.get('ok')}
    trusted={'source_pinned','repository_trusted','recorded_revision'} <= passed
    result={'status':'UNVERIFIABLE','notice':'Persisted test results are not independent attestation or proof about a past incident.', 'checks':{}}
    if not trusted: return result
    for key in ('reproduction_before','reproduction_after','regression'):
        execution=record.get(key)
        if not execution: continue
        usable=(execution.get('returncode') in (0, 1) and type(execution.get('returncode')) is int
                and execution.get('isolation')=='docker' and not execution.get('timed_out')
                and not execution.get('environment_error') and not execution.get('security_blocked'))
        result['checks'][key]={'evidence_id':'repair:'+str(record.get('id','unknown'))+':'+key,
                               'test_node':fixture.get('regression',{}).get('test') if key=='regression' else fixture.get('reproduction',{}).get('test'),
                               'commit':record.get('commit'),'mechanically_verifiable':True,'verification_outcome':
                               ('TEST_PASSED' if execution.get('returncode')==0 else 'TEST_FAILED') if usable else 'UNVERIFIABLE',
                               'returncode':execution.get('returncode')}
    before=record.get('reproduction_before') or {}; checked=result['checks'].get('reproduction_before',{})
    if checked.get('verification_outcome')=='TEST_PASSED':
        result['status']='NOT_REPRODUCED_IN_TEST'
        if fixture.get('reproduction',{}).get('reproducible') is False:
            result['status']='CONTRADICTED_IN_REGISTERED_FIXTURE_SCENARIO'
            result['notice']='The pinned registered fixture scenario passed; this does not disprove any historical incident.'
    elif checked.get('verification_outcome')=='TEST_FAILED':
        marker=fixture.get('reproduction',{}).get('failure_marker','')
        if marker and marker in before.get('output',''): result['status']='FAILURE_REPRODUCED_IN_TEST'
    return result
