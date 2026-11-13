"""Pre-registered paired 3D experiment on frozen trusted M3C incidents."""
import json,os,sqlite3,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import blackbox.investigator as investigation
import blackbox.repair.fixtures as fixtures
import blackbox.repair.pipeline as pipeline
from blackbox.repair.eligibility import evaluate,hypothesis_digest,evidence_reference_errors
from blackbox.repair.execution import detect_isolation
from blackbox.providers import configured_provider
from blackbox.store import Store

ORIGINAL=ROOT/'data/m3c-evaluation.db'; DB=ROOT/'data/m3d-paired.db'; OUTPUT=ROOT/'data/m3d-paired-results.json'
REVISION='2221398fc77cdffaad69db6ac615e6c8be661056'

def main():
    if DB.exists() or OUTPUT.exists(): raise RuntimeError('refuse to overwrite earlier run')
    source=sqlite3.connect(ORIGINAL); target=sqlite3.connect(DB); source.backup(target); target.close(); source.close()
    fixtures.REGISTRY_PATH=ROOT/'fixtures/repair/m3c-registry.json'
    baseline=json.loads((ROOT/'data/m3c-live-results.json').read_text(encoding='utf8'))
    gold=json.loads((ROOT/'fixtures/repair/m3c-ground-truth.json').read_text(encoding='utf8'))
    if baseline['revision']!=REVISION: raise RuntimeError('wrong frozen revision')
    cases=fixtures.load_registry(); labels={x['name']:x['expected'] for x in gold['cases']}
    incidents={r['name']:r['incident'] for r in baseline['runs'] if r['iteration']=='primary'}
    for f in cases:
        if not fixtures.content_pinned(ROOT,REVISION,f)[0]: raise RuntimeError('fixture pin mismatch')
    mode=detect_isolation()
    if mode.mode!='docker' or not mode.available: raise RuntimeError('Docker required')
    provider=configured_provider()
    if provider.model!='qwen3.5:4b': raise RuntimeError('wrong model')
    store=Store(str(DB)); rows=[]; original_retrieve=investigation.retrieve; original_prompt=pipeline.build_prompt
    def baseline_prompt(eligibility,files):
        system,prompt=original_prompt(eligibility,files); packet=json.loads(prompt)
        packet.pop('related_code',None)
        packet['constraints']=[x for x in packet['constraints'] if not x.startswith('preserve caller expectations')]
        return system,json.dumps(packet,sort_keys=True,ensure_ascii=False,indent=2)
    def save():
        OUTPUT.write_text(json.dumps({'revision':REVISION,'model':provider.model,'context':2048,'protocol':'research/36_M3D_PAIRED_PREREGISTRATION.md','rows':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    def run(name,arm,repeat=False):
        investigation.retrieve=(lambda *a,**k:{'excerpts':[],'limitations':[]}) if arm=='A' else original_retrieve
        pipeline.build_prompt=baseline_prompt if arm=='A' else original_prompt
        start=time.monotonic(); inv,_=investigation.investigate(store,ROOT,incidents[name],provider,force=True)
        row={'case':name,'arm':arm,'repeat':repeat,'investigation':inv,'investigation_wall_ms':int((time.monotonic()-start)*1000),'attempt':None}
        if inv['status']=='completed': row['reference_errors']=evidence_reference_errors(inv['findings'],inv['evidence'])
        if not repeat:
            if labels[name]=='diagnosable' and inv['status']=='completed' and inv.get('outcome')=='LIKELY_CAUSE':
                h=inv['findings']['hypotheses'][0]
                row['approval']=store.add_repair_approval(inv['id'],0,hypothesis_digest(h),inv['evidence_hash'],'m3d-fixture-benchmark','Synthetic fixture approval; not human production review')
            gate=evaluate(store,ROOT,inv['id'],name);row['eligibility']=gate.summary()
            if gate.eligible:
                start=time.monotonic();row['attempt']=pipeline.run_repair(store,ROOT,inv['id'],name,provider,isolation=mode);row['repair_wall_ms']=int((time.monotonic()-start)*1000)
        rows.append(row);save()
        print(name,arm,'repeat' if repeat else 'primary',inv.get('outcome'),(row['attempt'] or {}).get('status','-'),flush=True)
        if row['attempt'] and row['attempt']['status']=='SECURITY_BLOCKED': raise RuntimeError('security control failed; halted')
    for f in cases:
        for arm in ('A','B'): run(f['name'],arm)
    for name in ('m3c_window','m3c_ambiguous'):
        for arm in ('A','B'): run(name,arm,True)
    investigation.retrieve=original_retrieve;pipeline.build_prompt=original_prompt
if __name__=='__main__': main()
