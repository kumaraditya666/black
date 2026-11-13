"""Final post-review paired iteration; frozen evidence, separate output."""
import json,sqlite3,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import blackbox.investigator as im
from blackbox.providers import configured_provider
from blackbox.store import Store
from blackbox.repair.eligibility import evidence_reference_errors
DB=ROOT/'data/m3f-final.db';OUT=ROOT/'data/m3f-final-results.json'

def main():
 if DB.exists() or OUT.exists(): raise RuntimeError('refuse overwrite')
 prior=json.loads((ROOT/'data/m3f-paired-results.json').read_text(encoding='utf8'))
 if prior['revision']!='ee674ffb46dc83c5d78585ac23cd86217bcc2dec': raise RuntimeError('wrong revision')
 snaps={r['case']:r['investigation']['evidence'] for r in prior['rows'] if not r['repeat'] and r['arm']=='A'}
 ids={r['case']:r['investigation']['incident_id'] for r in prior['rows'] if not r['repeat'] and r['arm']=='A'}
 source=sqlite3.connect(ROOT/'data/m3f-paired.db');target=sqlite3.connect(DB);source.backup(target);target.close();source.close()
 store=Store(str(DB)); provider=configured_provider();assert provider.name=='ollama' and provider.model=='qwen3.5:4b'
 rows=[]
 for n,name in enumerate(['m3c_ambiguous','m3f_feed_multi','m3f_checksum','m3f_misleading','m3f_origin','m3f_absent']):
  for arm in (('A','B') if n%2==0 else ('B','A')):
   im.REFERENCE_RETRY_LIMIT=0 if arm=='A' else 1; im.STRICT_ABSTENTION=(arm=='B')
   start=time.monotonic();inv,_=im.investigate(store,ROOT,ids[name],provider,force=True,snapshot=snaps[name])
   row={'case':name,'arm':arm,'split':'tuning' if name=='m3c_ambiguous' else 'new_unblinded','investigation':inv,'wall_ms':int((time.monotonic()-start)*1000)}
   if inv['status']=='completed':row['reference_errors']=evidence_reference_errors(inv['findings'],inv['evidence'])
   rows.append(row);OUT.write_text(json.dumps({'revision':prior['revision'],'protocol':'research/39_M3F_PREREGISTRATION.md#final-validation-iteration-registered-after-exploratory-run-before-this-iteration','rows':rows},indent=2,ensure_ascii=False)+'\n',encoding='utf8')
   print(name,arm,inv['outcome'],inv['findings'].get('reference_retry'),flush=True)
 im.REFERENCE_RETRY_LIMIT=1;im.STRICT_ABSTENTION=True
if __name__=='__main__':main()
