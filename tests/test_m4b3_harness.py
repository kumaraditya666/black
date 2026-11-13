import json
import subprocess
from types import SimpleNamespace
import pytest
import scripts.evaluate_m4b3 as runner
from scripts.evaluate_m4b3 import plan, validate_response, ARMS, execute
from scripts.m4b3_layered_schema import validate_layered, LayeredFindings

def test_plan_has_all_six_cases_four_arms_and_no_labels():
    plans,rev=plan()
    assert len(plans)==24 and len({p['case'] for p in plans})==6
    assert len({(p['case'],p['arm']) for p in plans})==24
    assert {p['arm'] for p in plans}==set(ARMS)
    assert len({p['case'] for p in plans if p['arm']=='A'})==6
    assert all(p['revision']==rev and 'ground_truth' not in p['context'] for p in plans)
    assert all('singleton sequence makes denominator zero' not in p['context'] for p in plans)
    for case in runner.CASE_ORDER:
        rows=[p for p in plans if p['case']==case]
        assert len({p['evidence_hash'] for p in rows})==1
        assert {p['arm'] for p in rows}==set(ARMS)

def test_plan_uses_expected_counterbalanced_order_from_frozen_registry():
    plans,_=plan()
    actual={case:tuple(p['arm'] for p in plans if p['case']==case) for case in runner.CASE_ORDER}
    assert actual==runner.ARM_ORDER_BY_CASE

def test_schedule_covers_and_balances_every_arm_position():
    plans,_=plan()
    orders=[tuple(p['arm'] for p in plans if p['case']==case) for case in runner.CASE_ORDER]
    position_counts={arm:[sum(order[position]==arm for order in orders) for position in range(4)] for arm in ARMS}
    assert all(all(count>0 for count in counts) for counts in position_counts.values())
    assert all(max(counts)-min(counts)<=1 for counts in position_counts.values())

def test_plan_schedule_is_deterministic():
    first,_=plan(); second,_=plan()
    assert [(p['case'],p['arm']) for p in first]==[(p['case'],p['arm']) for p in second]

def test_layered_schema_accepts_mechanism_without_causal_claim():
    p,_=plan(); snap=p[0]['snapshot']
    raw={'outcome':'INSUFFICIENT_EVIDENCE','static_code_facts':[{'text':'function divides by denominator','evidence_ids':['code:0']}],
      'runtime_observations':[{'text':'incident record reports ZeroDivisionError','evidence_ids':['event:0']}],
      'behavioral_contract':[{'text':'non-empty sequences include singleton','evidence_ids':['doc:0']}],
      'mechanism_hypotheses':[{'explanation':'singleton makes denominator zero','supporting_evidence':['code:0'],'missing_evidence':['missing_evidence']}],
      'causal_attribution':{'status':'NOT_ESTABLISHED','explanation':'input and execution are unrecorded','evidence_ids':['event:0'],'missing_evidence':['missing_evidence']},
      'uncertainties':[{'text':'runtime input unknown','evidence_ids':['missing_evidence']}]}
    assert validate_response('D',raw,snap)['causal_attribution']['status']=='NOT_ESTABLISHED'

def test_layered_schema_rejects_unknown_ids_and_false_causality():
    p,_=plan(); snap=p[0]['snapshot']; raw={'outcome':'LIKELY_CAUSE','static_code_facts':[],
      'runtime_observations':[],'behavioral_contract':[],'mechanism_hypotheses':[],
      'causal_attribution':{'status':'ESTABLISHED','explanation':'caused it','evidence_ids':['event:0'],'missing_evidence':[]},'uncertainties':[]}
    with pytest.raises(ValueError): validate_layered(raw,snap['evidence'])
    raw['causal_attribution']['status']='NOT_ESTABLISHED'; raw['causal_attribution']['evidence_ids']=['fake']
    with pytest.raises(ValueError): validate_layered(raw,snap['evidence'])

def test_existing_schema_keeps_its_citation_validation():
    from blackbox.investigator import validate_model_output
    p,_=plan(); snap=p[0]['snapshot']
    raw={'outcome':'LIKELY_CAUSE','observed_failure':{'text':'reported failure','evidence_ids':['event:0']},
      'observed_facts':[],'hypotheses':[{'explanation':'bad citation','supporting_evidence':['fake'],'contradicting_evidence':[]}],
      'alternatives':[],'missing_evidence':[],'verification_steps':['check input']}
    with pytest.raises(ValueError): validate_model_output(raw,snap)
class MockProvider:
    name='mock'; model='offline-mock'
    def __init__(self,fail_once=False): self.calls=0; self.fail_once=fail_once; self.invocations=[]
    def structured(self,prompt,schema,max_output_tokens):
        self.calls+=1
        marker='UNTRUSTED EVIDENCE JSON:\n'
        snapshot=json.loads(prompt.split(marker,1)[1])
        layered_prompt=prompt.startswith(runner.LAYERED_PROMPT)
        layered_schema='static_code_facts' in schema.get('properties',{})
        arm={(False,False):'A',(True,False):'B',(False,True):'C',(True,True):'D'}[(layered_prompt,layered_schema)]
        self.invocations.append((snapshot['incident_id'],arm))
        if self.fail_once and self.calls==1: return SimpleNamespace(text='{}',usage={'input_tokens':1,'output_tokens':1})
        if 'static_code_facts' in str(schema):
            obj={'outcome':'INSUFFICIENT_EVIDENCE','static_code_facts':[],'runtime_observations':[],
              'behavioral_contract':[],'mechanism_hypotheses':[],
              'causal_attribution':{'status':'NOT_ESTABLISHED','explanation':'runtime telemetry missing','evidence_ids':['event:0'],'missing_evidence':['missing_evidence']},'uncertainties':[]}
        else:
            obj={'outcome':'INSUFFICIENT_EVIDENCE','observed_failure':{'text':'reported error','evidence_ids':['event:0']},
              'observed_facts':[],'hypotheses':[],'alternatives':[],'missing_evidence':['not recorded'],'verification_steps':['collect telemetry']}
        return SimpleNamespace(text=json.dumps(obj),usage={'input_tokens':1,'output_tokens':1})

def test_arbitrary_provider_execution_api_is_rejected(tmp_path):
    plans,_=plan(); provider=MockProvider(fail_once=True); out=tmp_path/'partial.json'
    with pytest.raises(TypeError):
        execute(plans,provider,out)
    assert provider.calls==0

def test_runner_selects_original_immutable_revision_and_reads_its_blobs():
    seen=[]
    def spy(*args):
        seen.append(args)
        return runner.git(*args)
    plans,rev=plan(git_fn=spy)
    assert rev=='13bdc52bad27c49b77e85daac16876133f382009'
    assert all(p['revision']==rev for p in plans)
    assert any(x[0]=='show' and x[1].startswith(rev+':fixtures/repair/m4b3/') for x in seen)
    assert not any('refs/blackbox/m4b3-freeze' in x for x in seen)

def test_all_six_registered_source_hashes_match_at_preregistered_revision():
    plans,rev=plan()
    assert rev==runner.PINNED_REV
    assert len({p['case'] for p in plans})==6

def test_original_registry_metadata_is_read_without_mutation():
    raw=runner.git('show',runner.PINNED_REV+':'+runner.REG)
    registry=json.loads(raw)
    assert registry['revision']=='TO_BE_FILLED_BEFORE_FREEZE'
    assert 'freeze_ref' not in registry
    assert len(registry['sha256'])==7
    assert runner.git('show',runner.PINNED_REV+':'+runner.REG)==raw
    plan()

def test_results_template_must_match_original_revision():
    runner.validate_template(runner.OUT,runner.PINNED_REV)
    with pytest.raises(ValueError): runner.validate_template(runner.OUT,'9b5d444209a92776ee9e2fd2063135518d3c921a')

def test_results_template_rejects_nonempty_results(tmp_path):
    target=tmp_path/'results.json'
    target.write_text(json.dumps({'status':'template_only_no_model_calls','revision':runner.PINNED_REV,'results':[{}]}))
    with pytest.raises(ValueError): runner.validate_template(target,runner.PINNED_REV)

def test_missing_pinned_commit_fails_closed():
    def missing(*args): raise subprocess.CalledProcessError(128,args)
    with pytest.raises(subprocess.CalledProcessError): plan('0000000000000000000000000000000000000000',git_fn=missing)

def test_incorrect_registered_source_hash_fails_closed():
    def corrupted(*args):
        result=runner.git(*args)
        if args[0]=='show' and args[-1].endswith('fixtures/repair/m4b3/contracted_mean/app.py'): return b'wrong source'
        return result
    with pytest.raises(ValueError,match='source hash mismatch'):
        plan(git_fn=corrupted)

def test_scorer_labels_are_not_investigator_inputs():
    plans,_=plan()
    assert all('m4b3-ground-truth' not in p['context'] and 'singleton sequence makes denominator zero' not in p['context'] for p in plans)
    assert all(p['scorer_label_sha256'] for p in plans)

def test_live_model_digest_must_match_preregistered_prefix():
    good={'models':[{'name':runner.MODEL,'digest':runner.MODEL_DIGEST}]}
    assert runner.verify_model_config(good,'ollama version '+runner.PROPOSED_OLLAMA_VERSION)['model_digest']==runner.MODEL_DIGEST
    bad={'models':[{'name':runner.MODEL,'digest':'0'*64}]}
    with pytest.raises(RuntimeError,match='digest'):
        runner.verify_model_config(bad,'ollama version mock')

def test_dry_run_never_verifies_or_calls_a_model(monkeypatch,capsys):
    monkeypatch.setattr('sys.argv',['evaluate_m4b3.py','--dry-run'])
    monkeypatch.setattr(runner,'verify_local_model',lambda: (_ for _ in ()).throw(AssertionError('model preflight called')))
    runner.main()
    output=capsys.readouterr().out
    assert 'revision=13bdc52bad27c49b77e85daac16876133f382009 cases=6 arms=4 planned_evaluations=24 model_calls=0' in output
    for case,order in runner.ARM_ORDER_BY_CASE.items():
        assert f"{case}: {','.join(order)}" in output
