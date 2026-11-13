import copy, os, subprocess
from pathlib import Path
import pytest
from blackbox.semantic_verification import assess_snapshot, assess_execution

@pytest.fixture
def sample(tmp_path):
    repo=tmp_path/'repo';repo.mkdir(); subprocess.run(['git','init','-q',str(repo)],check=True)
    (repo/'app.py').write_text('def f(x):\n    return int(x)\n',encoding='utf8')
    subprocess.run(['git','-C',str(repo),'add','app.py'],check=True)
    env=os.environ.copy();env.update(GIT_AUTHOR_NAME='test',GIT_AUTHOR_EMAIL='test@local',GIT_COMMITTER_NAME='test',GIT_COMMITTER_EMAIL='test@local')
    subprocess.run(['git','-C',str(repo),'commit','-qm','fixture'],check=True,env=env)
    rev=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    snapshot={'evidence':[{'id':'event:1','type':'event','commit':rev,'exception_type':'ValueError','message':'bad'},
      {'id':'frame:0','type':'stack_frame','commit':rev,'path':'app.py','line':2,'function':'f','source_line':'    return int(x)','status':'resolved'}]}
    return repo,snapshot


def test_recorded_event_is_not_runtime_proof(sample):
    repo,snapshot=sample
    result=assess_snapshot(repo,snapshot,[{'explanation':'upstream is broken','supporting_evidence':['event:1','frame:0']}])
    assert result['observed_failure']['status']=='RECORDED'
    assert result['upstream_root_cause']['status']=='INSUFFICIENT_EVIDENCE'
    claims={c['category']:c for c in result['claims']}
    assert claims['SOURCE_LINE']['verification_outcome']=='VERIFIED_SOURCE'
    assert claims['RECORDED_STACK_FRAME']['verification_outcome']=='RECORDED'
    assert claims['CAUSAL_HYPOTHESIS']['verification_outcome']=='UNVERIFIABLE'
    assert not claims['CAUSAL_HYPOTHESIS']['mechanically_verifiable']


def test_incorrect_source_and_revision_are_not_verified(sample):
    repo,snapshot=sample; fake=copy.deepcopy(snapshot);fake['evidence'][1]['source_line']='    return 9'
    c=assess_snapshot(repo,fake)['claims'];assert next(x for x in c if x['category']=='SOURCE_LINE')['verification_outcome']=='CONTRADICTED'
    fake['evidence'][1]['commit']='0'*40
    c=assess_snapshot(repo,fake)['claims'];assert next(x for x in c if x['category']=='SOURCE_LINE')['verification_outcome']=='UNVERIFIABLE'


def test_source_excerpt_verified_and_traversal_rejected(sample):
    repo,snapshot=sample; rev=snapshot['evidence'][0]['commit']
    context={'id':'code:0','type':'code_context','commit':rev,'path':'app.py','line':1,'end_line':2,'source':'def f(x):\n    return int(x)'}
    snapshot['evidence'].append(context)
    claims=assess_snapshot(repo,snapshot)['claims'];assert next(x for x in claims if x['category']=='SOURCE_EXCERPT')['verification_outcome']=='VERIFIED_SOURCE'
    context['path']='../app.py';claims=assess_snapshot(repo,snapshot)['claims'];assert next(x for x in claims if x['category']=='SOURCE_EXCERPT')['verification_outcome']=='UNVERIFIABLE'


def trusted_record(code, **extra):
    checks=[{'code':x,'ok':True} for x in ('source_pinned','repository_trusted','recorded_revision')]
    return {'validation':{'eligibility':{'checks':checks}},'reproduction_before':{'isolation':'docker','returncode':code,'output':'ValueError','timed_out':False,'environment_error':False,**extra}}


def test_fixture_contradiction_is_limited_to_registered_scenario():
    fixture={'reproduction':{'reproducible':False,'failure_marker':'ValueError'}}
    result=assess_execution(trusted_record(0),fixture)
    assert result['status']=='CONTRADICTED_IN_REGISTERED_FIXTURE_SCENARIO'
    assert 'historical' in result['notice']
    assert assess_execution(trusted_record(1),fixture)['status']=='FAILURE_REPRODUCED_IN_TEST'
    assert assess_execution(trusted_record(None),fixture)['status']=='UNVERIFIABLE'
    assert assess_execution(trusted_record(0,security_blocked=True),fixture)['status']=='UNVERIFIABLE'
    assert assess_execution({'reproduction_before':{'returncode':0}},fixture)['status']=='UNVERIFIABLE'


def test_passing_test_does_not_verify_upstream_cause(sample):
    repo,snapshot=sample
    result=assess_snapshot(repo,snapshot,[{'explanation':'caller is at fault','supporting_evidence':['event:1','frame:0']}])
    assert result['upstream_root_cause']['status']=='INSUFFICIENT_EVIDENCE'
    assert result['immediate_mechanism']['status']=='HYPOTHESIS_REQUIRES_REVIEW'


def test_invalid_model_response_keeps_only_safe_diagnostic_and_usage(sample,tmp_path):
    import json,uuid
    from datetime import datetime,timezone
    from blackbox.store import Store
    from blackbox.schemas import Event,Frame
    from blackbox.providers import ProviderResult
    from blackbox.investigator import investigate
    repo,snapshot=sample; rev=snapshot['evidence'][0]['commit']; store=Store(str(tmp_path/'db.sqlite'))
    event=Event(event_id=uuid.uuid4(),occurred_at=datetime.now(timezone.utc),commit=rev,
                exception_type='ValueError',message='bad',traceback='bad',frames=[Frame(path='app.py',line=2,function='f')])
    iid,_=store.ingest(event)
    class Invalid:
        name='ollama';model='mock'
        def analyze(self,prompt): return ProviderResult('{"secret":"unique-unredacted-canary"',{'input_tokens':7,'output_tokens':3})
    result,_=investigate(store,repo,iid,Invalid())
    assert result['status']=='failed' and result['failure_kind']=='INVALID_MODEL_RESPONSE'
    assert result['findings']['diagnostic']['category']=='SCHEMA_OR_JSON'
    assert result['findings']['diagnostic']['raw_response_retained'] is False
    assert result['usage']['input_tokens']==7
    assert b'unique-unredacted-canary' not in (tmp_path/'db.sqlite').read_bytes()
    assert result['findings']['reasoning_levels']['upstream_root_cause']['status']=='INSUFFICIENT_EVIDENCE'


def test_contradicted_snapshot_fails_closed_before_model(sample,tmp_path):
    import uuid
    from datetime import datetime,timezone
    from blackbox.store import Store
    from blackbox.schemas import Event,Frame
    from blackbox.investigator import investigate
    repo,snapshot=sample;store=Store(str(tmp_path/'events.db')); rev=snapshot['evidence'][0]['commit']
    event=Event(event_id=uuid.uuid4(),occurred_at=datetime.now(timezone.utc),commit=rev,
                exception_type='ValueError',message='bad',traceback='bad',frames=[Frame(path='app.py',line=2,function='f')])
    iid,_=store.ingest(event)
    snapshot['evidence'][1]['source_line']='    return 9'
    class Never:
        name='ollama';model='never';calls=0
        def analyze(self,prompt): self.calls+=1;raise AssertionError('must not call model')
    provider=Never(); result,_=investigate(store,repo,iid,provider,snapshot=snapshot)
    assert provider.calls==0 and result['status']=='failed'
    assert result['findings']['diagnostic']['reason_code']=='PINNED_SOURCE_MISMATCH'
    claims=result['findings']['atomic_claims']
    assert next(c for c in claims if c['category']=='source_statement')['verification_status']=='CONTRADICTED'


def _retry_inputs(sample,tmp_path):
    import uuid
    from datetime import datetime,timezone
    from blackbox.store import Store
    from blackbox.schemas import Event,Frame
    repo,snapshot=sample;store=Store(str(tmp_path/'retry.db'));rev=snapshot['evidence'][0]['commit']
    event=Event(event_id=uuid.uuid4(),occurred_at=datetime.now(timezone.utc),commit=rev,
                exception_type='ValueError',message='bad',traceback='bad',frames=[Frame(path='app.py',line=2,function='f')])
    incident,_=store.ingest(event)
    bad={'outcome':'LIKELY_CAUSE','observed_failure':{'text':'recorded','evidence_ids':['event:1']},
         'observed_facts':[],'hypotheses':[{'explanation':'maybe','supporting_evidence':['frame:0'],'contradicting_evidence':[]}],
         'alternatives':[],'missing_evidence':['unknown'],'verification_steps':['inspect']}
    abstain={**bad,'outcome':'INSUFFICIENT_EVIDENCE','hypotheses':[]}
    return repo, snapshot, store, incident, bad, abstain


def test_missing_reference_gets_one_validated_retry_not_fabricated(sample,tmp_path):
    import json
    from blackbox.investigator import investigate
    from blackbox.providers import ProviderResult
    repo,snapshot,store,incident,bad,abstain=_retry_inputs(sample,tmp_path)
    class P:
        name='ollama';model='retry-test';calls=0
        def analyze(self,prompt):
            self.calls+=1
            return ProviderResult(json.dumps(bad if self.calls==1 else abstain),{'input_tokens':10,'output_tokens':4})
    p=P(); result,_=investigate(store,repo,incident,p,snapshot=snapshot)
    assert p.calls==2 and result['outcome']=='INSUFFICIENT_EVIDENCE'
    assert result['findings']['reference_retry']=={'attempted':True,'reason':'MISSING_REQUIRED_REFERENCE'}
    assert result['findings']['hypotheses']==[] and result['usage']['input_tokens']==20


def test_malformed_retry_is_failure_not_abstention(sample,tmp_path):
    import json
    from blackbox.investigator import investigate
    from blackbox.providers import ProviderResult
    repo,snapshot,store,incident,bad,_=_retry_inputs(sample,tmp_path)
    class P:
        name='ollama';model='retry-test';calls=0
        def analyze(self,prompt):
            self.calls+=1
            return ProviderResult(json.dumps(bad) if self.calls==1 else '{broken',{'input_tokens':2,'output_tokens':1})
    p=P();result,_=investigate(store,repo,incident,p,snapshot=snapshot)
    assert p.calls==2 and result['outcome']=='INVESTIGATION_FAILED'
    assert result['findings']['diagnostic']['category']=='SCHEMA_OR_JSON'
    assert result['findings']['reference_retry']['attempted']


def test_unknown_reference_does_not_get_retry(sample,tmp_path):
    import json
    from blackbox.investigator import investigate
    from blackbox.providers import ProviderResult
    repo,snapshot,store,incident,bad,_=_retry_inputs(sample,tmp_path)
    bad['hypotheses'][0]['supporting_evidence']=['not-real']
    class P:
        name='ollama';model='retry-test';calls=0
        def analyze(self,prompt):
            self.calls+=1;return ProviderResult(json.dumps(bad),{'input_tokens':2,'output_tokens':1})
    p=P();result,_=investigate(store,repo,incident,p,snapshot=snapshot)
    assert p.calls==1 and result['outcome']=='INVESTIGATION_FAILED'
    assert result['findings']['diagnostic']['reason_code']=='UNKNOWN_EVIDENCE_ID'


def test_valid_abstention_does_not_require_hypothesis_citations(sample,tmp_path):
    import json
    from blackbox.investigator import investigate
    from blackbox.providers import ProviderResult
    repo,snapshot,store,incident,_,abstain=_retry_inputs(sample,tmp_path)
    class P:
        name='ollama';model='retry-test';calls=0
        def analyze(self,prompt):
            self.calls+=1;return ProviderResult(json.dumps(abstain),{'input_tokens':2,'output_tokens':1})
    p=P();result,_=investigate(store,repo,incident,p,snapshot=snapshot)
    assert p.calls==1 and result['outcome']=='INSUFFICIENT_EVIDENCE'
    assert not result['findings']['reference_retry']['attempted']


def test_bounded_hypothesis_review_keeps_static_provenance_unverified(sample):
    from blackbox.semantic_verification import assess_snapshot,review_hypotheses
    repo,snapshot=sample
    h={'explanation':'incorrect causal claim','supporting_evidence':['event:1','frame:0'],'contradicting_evidence':[]}
    assessment=assess_snapshot(repo,snapshot,[h])
    review=review_hypotheses({'hypotheses':[h]*4,'missing_evidence':['runtime input'],
                              'verification_steps':['Collect input; do not run a command']},assessment)
    assert len(review['hypotheses'])==3 and review['omitted_hypotheses']==1
    assert review['hypotheses'][0]['decision']=='QUALIFIED_REQUIRES_REVIEW'
    assert review['hypotheses'][0]['source_checks']==[{'evidence_id':'frame:0','source_status':'VERIFIED_SOURCE'}]
    assert review['proposed_verification_experiments']==['Collect input; do not run a command']
    assert 'no commands' in review['notice']


def test_incomplete_abstention_is_not_promoted(sample,tmp_path):
    import json
    from blackbox.investigator import investigate
    from blackbox.providers import ProviderResult
    repo,snapshot,store,incident,_,_=_retry_inputs(sample,tmp_path)
    class P:
        name='ollama';model='incomplete';calls=0
        def analyze(self,prompt):
            self.calls+=1;return ProviderResult(json.dumps({'outcome':'INSUFFICIENT_EVIDENCE'}),{'input_tokens':2,'output_tokens':1})
    p=P();result,_=investigate(store,repo,incident,p,snapshot=snapshot)
    assert p.calls==1 and result['outcome']=='INVESTIGATION_FAILED'
    assert result['findings']['diagnostic']['category']=='SCHEMA_OR_JSON'


def test_retry_provider_failure_keeps_both_usage_and_fails(sample,tmp_path):
    import json
    from blackbox.investigator import investigate
    from blackbox.providers import ProviderError,ProviderResult
    repo,snapshot,store,incident,bad,_=_retry_inputs(sample,tmp_path)
    class P:
        name='ollama';model='cutoff';calls=0
        def analyze(self,prompt):
            self.calls+=1
            if self.calls==1: return ProviderResult(json.dumps(bad),{'input_tokens':10,'output_tokens':4})
            raise ProviderError('Model output reached the token limit',{'input_tokens':11,'output_tokens':9})
    p=P();result,_=investigate(store,repo,incident,p,snapshot=snapshot)
    assert p.calls==2 and result['outcome']=='INVESTIGATION_FAILED'
    assert result['usage']['input_tokens']==21 and result['usage']['output_tokens']==13
