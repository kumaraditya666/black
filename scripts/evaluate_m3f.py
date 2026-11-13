"""M3F preregistered paired evaluation: only local, frozen trusted cases."""
import json,sqlite3,subprocess,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import blackbox.investigator as im
import blackbox.repair.fixtures as fx
from blackbox.repair.execution import detect_isolation
from blackbox.repair.eligibility import evidence_reference_errors
from blackbox.providers import configured_provider
from blackbox.schemas import Event,Frame
from blackbox.store import Store
REV='ee674ffb46dc83c5d78585ac23cd86217bcc2dec'; DB=ROOT/'data/m3f-paired.db'; OUT=ROOT/'data/m3f-paired-results.json'

def main():
 if DB.exists() or OUT.exists(): raise RuntimeError('refuse overwrite')
 reg=ROOT/'fixtures/repair/m3f-registry.json'; gold=ROOT/'fixtures/repair/m3f-ground-truth.json'
 for p in (reg,gold):
  if p.read_bytes()!=subprocess.check_output(['git','-C',str(ROOT),'show',REV+':'+p.relative_to(ROOT).as_posix()]): raise RuntimeError('metadata changed')
 cases=fx.load_registry(reg); audit=json.loads((ROOT/'data/m3f-fixture-audit.json').read_text(encoding='utf8'))
 if audit['revision']!=REV: raise RuntimeError('wrong audit revision')
 logs={x['name']:x['result'] for x in audit['cases']}
 mode=detect_isolation(); assert mode.mode=='docker' and mode.available
 provider=configured_provider(); assert provider.name=='ollama' and provider.model=='qwen3.5:4b'
 source=sqlite3.connect(ROOT/'data/m3c-evaluation.db');target=sqlite3.connect(DB);source.backup(target);target.close();source.close()
 store=Store(str(DB)); snapshots={};incidents={}
 for f in cases:
  ok,_=fx.content_pinned(ROOT,REV,f)
  if not ok: raise RuntimeError('pin mismatch')
  log=logs[f['name']]
  if log['environment_error'] or log.get('security_blocked'): raise RuntimeError('security or environment block')
  if f['reproduction']['reproducible'] and (log['returncode']!=1 or f['event']['message'] not in log['output']): raise RuntimeError('ground truth mismatch')
  if not f['reproduction']['reproducible'] and log['returncode']!=0: raise RuntimeError('negative control mismatch')
  ev=f['event']; e=Event(event_id=uuid.uuid4(),occurred_at=datetime.now(timezone.utc),commit=REV,exception_type=ev['exception_type'],message=ev['message'],traceback=log['output'] if f['reproduction']['reproducible'] else 'Intentionally false reported event; negative control.',frames=[Frame(**ev['frame'])])
  incident,_=store.ingest(e);incidents[f['name']]=incident;snapshots[f['name']]=im.collect(store,ROOT,incident)
 prior=json.loads((ROOT/'data/m3d-paired-results.json').read_text(encoding='utf8'))
 tune=next(x for x in prior['rows'] if x['case']=='m3c_ambiguous' and x['arm']=='B' and not x['repeat'])['investigation']
 incidents['m3c_ambiguous']=tune['incident_id'];snapshots['m3c_ambiguous']=tune['evidence']
 rows=[]
 def save(): OUT.write_text(json.dumps({'revision':REV,'model':provider.model,'protocol':'research/39_M3F_PREREGISTRATION.md','rows':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
 def run(name,arm,repeat):
  im.REFERENCE_RETRY_LIMIT=0 if arm=='A' else 1
  start=time.monotonic(); result,_=im.investigate(store,ROOT,incidents[name],provider,force=True,snapshot=snapshots[name])
  row={'case':name,'arm':arm,'repeat':repeat,'split':'tuning' if name=='m3c_ambiguous' else 'new_unblinded',
       'investigation':result,'wall_ms':int((time.monotonic()-start)*1000)}
  if result['status']=='completed': row['reference_errors']=evidence_reference_errors(result['findings'],result['evidence'])
  rows.append(row);save();print(name,arm,'repeat' if repeat else 'primary',result['outcome'],result['findings'].get('reference_retry'),flush=True)
 for index,name in enumerate(['m3c_ambiguous']+[f['name'] for f in cases]):
  order=('A','B') if index%2==0 else ('B','A')
  for arm in order: run(name,arm,False)
  for arm in reversed(order): run(name,arm,True)
 im.REFERENCE_RETRY_LIMIT=1
if __name__=='__main__': main()
