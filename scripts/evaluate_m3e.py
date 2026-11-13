"""Preregistered 3E paired prompt comparison on identical frozen 3D evidence."""
import json, sqlite3, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import blackbox.investigator as invmod
import blackbox.repair.fixtures as fixtures
from blackbox.repair.eligibility import evaluate,hypothesis_digest,evidence_reference_errors
from blackbox.repair.execution import detect_isolation
from blackbox.repair.pipeline import run_repair
from blackbox.providers import configured_provider
from blackbox.store import Store
SOURCE=ROOT/'data/m3c-evaluation.db'; DB=ROOT/'data/m3e-paired.db'; OUT=ROOT/'data/m3e-paired-results.json'
REV='2221398fc77cdffaad69db6ac615e6c8be661056'
INSERT='An immediate exception mechanism does not establish its upstream origin. If the upstream cause is not supported, return INSUFFICIENT_EVIDENCE.\n'

def main():
    if DB.exists() or OUT.exists(): raise RuntimeError('refuse to overwrite earlier evidence')
    prior=json.loads((ROOT/'data/m3d-paired-results.json').read_text(encoding='utf8'))
    if prior['revision']!=REV: raise RuntimeError('wrong revision')
    fixtures.REGISTRY_PATH=ROOT/'fixtures/repair/m3c-registry.json'
    cases=fixtures.load_registry(); gold=json.loads((ROOT/'fixtures/repair/m3c-ground-truth.json').read_text(encoding='utf8'))
    labels={x['name']:x['expected'] for x in gold['cases']}
    import hashlib,subprocess
    for p in (fixtures.REGISTRY_PATH,ROOT/'fixtures/repair/m3c-ground-truth.json'):
        if p.read_bytes()!=subprocess.check_output(['git','-C',str(ROOT),'show',REV+':'+p.relative_to(ROOT).as_posix()]): raise RuntimeError('benchmark metadata mismatch')
    for f in cases:
        if not fixtures.content_pinned(ROOT,REV,f)[0]: raise RuntimeError('fixture pin mismatch')
    snapshots={x['case']:x['investigation']['evidence'] for x in prior['rows'] if x['arm']=='B' and not x['repeat']}
    originals={x['case']:x['investigation']['incident_id'] for x in prior['rows'] if x['arm']=='B' and not x['repeat']}
    if any(next(i for i in s['evidence'] if i['type']=='event')['commit']!=REV for s in snapshots.values()): raise RuntimeError('snapshot revision mismatch')
    mode=detect_isolation()
    if mode.mode!='docker' or not mode.available: raise RuntimeError('Docker required')
    provider=configured_provider()
    if provider.name!='ollama' or provider.model!='qwen3.5:4b': raise RuntimeError('wrong model')
    source=sqlite3.connect(SOURCE);target=sqlite3.connect(DB);source.backup(target);target.close();source.close()
    store=Store(str(DB));rows=[];enhanced=invmod.SYSTEM
    if enhanced.count(INSERT)!=1: raise RuntimeError('prompt baseline cannot be reconstructed')
    baseline=enhanced.replace(INSERT,'')
    def save(): OUT.write_text(json.dumps({'revision':REV,'protocol':'research/38_M3E_PREREGISTRATION.md','model':provider.model,'context':2048,'rows':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    def run(name,arm,repeat):
        invmod.SYSTEM=baseline if arm=='A' else enhanced
        start=time.monotonic(); investigation,_=invmod.investigate(store,ROOT,originals[name],provider,force=True,snapshot=snapshots[name])
        row={'case':name,'arm':arm,'repeat':repeat,'split':'pseudo-held-out' if name in ('m3c_config','m3c_ambiguous') else 'tuning',
             'investigation':investigation,'wall_ms':int((time.monotonic()-start)*1000),'attempt':None}
        if investigation['status']=='completed': row['reference_errors']=evidence_reference_errors(investigation['findings'],investigation['evidence'])
        if not repeat:
            if labels[name]=='diagnosable' and investigation['status']=='completed' and investigation.get('outcome')=='LIKELY_CAUSE':
                h=investigation['findings']['hypotheses'][0]
                row['approval']=store.add_repair_approval(investigation['id'],0,hypothesis_digest(h),investigation['evidence_hash'],'m3e-fixture-benchmark','Synthetic benchmark approval; not human production review')
            gate=evaluate(store,ROOT,investigation['id'],name);row['eligibility']=gate.summary()
            if gate.eligible:
                start=time.monotonic();row['attempt']=run_repair(store,ROOT,investigation['id'],name,provider,isolation=mode);row['repair_wall_ms']=int((time.monotonic()-start)*1000)
        rows.append(row);save();print(name,arm,'repeat' if repeat else 'primary',investigation.get('outcome'),(row['attempt'] or {}).get('status','-'),flush=True)
        if row['attempt'] and row['attempt']['status']=='SECURITY_BLOCKED': raise RuntimeError('security blocked; halted')
    for i,f in enumerate(cases):
        order=('A','B') if i%2==0 else ('B','A')
        for arm in order: run(f['name'],arm,False)
        for arm in reversed(order): run(f['name'],arm,True)
    invmod.SYSTEM=enhanced
if __name__=='__main__': main()
