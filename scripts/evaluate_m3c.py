"""Frozen M3C evaluation harness: trusted fixtures only, explicit Docker, no prompt changes."""
import hashlib,json,os,subprocess,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from blackbox.investigator import investigate
from blackbox.providers import configured_provider
import blackbox.repair.fixtures as fixtures
from blackbox.repair.eligibility import evaluate,hypothesis_digest,evidence_reference_errors
from blackbox.repair.execution import detect_isolation
from blackbox.repair.pipeline import run_repair
from blackbox.schemas import Event,Frame
from blackbox.store import Store

REVISION='2221398fc77cdffaad69db6ac615e6c8be661056'
REGISTRY=ROOT/'fixtures/repair/m3c-registry.json'
GOLD=ROOT/'fixtures/repair/m3c-ground-truth.json'
DB=ROOT/'data/m3c-evaluation.db'; OUTPUT=ROOT/'data/m3c-live-results.json'

def frozen(path):
    current=path.read_bytes()
    committed=subprocess.check_output(['git','-C',str(ROOT),'show',REVISION+':'+path.relative_to(ROOT).as_posix()])
    if current!=committed: raise RuntimeError('frozen benchmark file changed: '+str(path))
    return hashlib.sha256(current).hexdigest()

def main():
    if DB.exists() or OUTPUT.exists(): raise RuntimeError('refuse to overwrite prior evaluation')
    hashes={'registry':frozen(REGISTRY),'ground_truth':frozen(GOLD)}
    fixtures.REGISTRY_PATH=REGISTRY
    cases=fixtures.load_registry(); labels={x['name']:x for x in json.loads(GOLD.read_text())['cases']}
    baseline=json.loads((ROOT/'data/m3c-ground-truth-audit.json').read_text())
    if baseline['revision'] != REVISION: raise RuntimeError('audit revision mismatch')
    audits={x['name']:x for x in baseline['fixtures']}
    isolation=detect_isolation()
    if isolation.mode!='docker' or not isolation.available: raise RuntimeError('Docker required')
    provider=configured_provider()
    if provider.model!='qwen3.5:4b': raise RuntimeError('unexpected model')
    store=Store(str(DB)); runs=[]; incidents={}
    def save(): OUTPUT.write_text(json.dumps({'revision':REVISION,'hashes':hashes,'model':provider.model,'isolation':'docker','approval':'fixture-level synthetic benchmark only, not human production review','runs':runs},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    for f in cases:
        name=f['name']; valid,why=fixtures.content_pinned(ROOT,REVISION,f)
        if not valid: raise RuntimeError('fixture pin mismatch: '+why)
        audit=audits[name]; spec=f['event']; positive=labels[name]['expected']!='negative_control'
        if positive and (audit['result']['returncode']!=1 or spec['exception_type'] not in audit['result']['output'] or spec['message'] not in audit['result']['output']): raise RuntimeError('event does not match observed failure')
        e=Event(event_id=uuid.uuid4(),occurred_at=datetime.now(timezone.utc),commit=REVISION,exception_type=spec['exception_type'],message=spec['message'],traceback=audit['result']['output'] if positive else 'Synthetic intentionally false reported error; negative control.',frames=[Frame(**spec['frame'])])
        incident,_=store.ingest(e); incidents[name]=incident
        mark=time.monotonic(); inv,_=investigate(store,ROOT,incident,provider,force=True)
        case={'name':name,'iteration':'primary','incident':incident,'investigation':inv,'investigation_wall_ms':int((time.monotonic()-mark)*1000),'approval':None,'eligibility':None,'attempt':None}
        if inv['status']=='completed': case['reference_errors']=evidence_reference_errors(inv['findings'],inv['evidence'])
        if labels[name]['expected']=='diagnosable' and inv['status']=='completed' and inv.get('outcome')=='LIKELY_CAUSE':
            h=inv['findings']['hypotheses'][0]
            # Explicit benchmark scope: automatic fixture-level review; no production permission.
            case['approval']=store.add_repair_approval(inv['id'],0,hypothesis_digest(h),inv['evidence_hash'],'m3c-fixture-benchmark','Synthetic fixture-level approval, not production review')
        gate=evaluate(store,ROOT,inv['id'],name); case['eligibility']=gate.summary()
        if gate.eligible:
            mark=time.monotonic(); case['attempt']=run_repair(store,ROOT,inv['id'],name,provider,isolation=isolation); case['repair_wall_ms']=int((time.monotonic()-mark)*1000)
        runs.append(case); save()
        print(name,inv.get('outcome'),(case['attempt'] or {}).get('status','not attempted'),flush=True)
        if case['attempt'] and case['attempt']['status']=='SECURITY_BLOCKED': raise RuntimeError('security control blocked; evaluation halted')
    for name in ('m3c_window','m3c_ambiguous'):
        mark=time.monotonic(); inv,_=investigate(store,ROOT,incidents[name],provider,force=True)
        runs.append({'name':name,'iteration':'repeat_investigation_only','investigation':inv,'investigation_wall_ms':int((time.monotonic()-mark)*1000),'reference_errors':evidence_reference_errors(inv['findings'],inv['evidence']) if inv['status']=='completed' else None}); save()
        print(name,'repeat',inv.get('outcome'),flush=True)
    return 0
if __name__=='__main__': raise SystemExit(main())
