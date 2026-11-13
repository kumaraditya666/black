"""Bounded oracle-context reuse diagnostic for the frozen M4B.1 fixtures."""
import copy, hashlib, json, subprocess, sys, tempfile, time, uuid, ast
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from blackbox.agent_retrieval import Dispatcher
from blackbox.providers import Provider
from blackbox.store import Store
from blackbox.schemas import Event, Frame
import blackbox.investigator as investigator
import blackbox.repair.fixtures as fixtures

REV = '76564779c56068107aeccda8205147c6bbbea86e'
REG = ROOT / 'fixtures/repair/m4b1-registry.json'
LABELS = ROOT / 'fixtures/repair/m4b1-ground-truth.json'
RESULTS = ROOT / 'data/m4b1-results.json'
OUT = ROOT / 'data/m4b2-results.json'
DB = ROOT / ('data/m4b2-diagnostic-' + uuid.uuid4().hex + '.db')

def oracle_excerpt(case, fixture, snapshot, symbol):
    dispatcher = Dispatcher(ROOT, REV, fixture)
    # The dispatcher validates registered scope and immutable regular Git blobs.
    choices = [p for p in sorted(dispatcher.paths)]
    if symbol:
        raw = {'action':'find_symbol','symbol':symbol,'reason':'Resolve approved function symbol'}
        found = dispatcher.dispatch(raw)
        if found['status'] != 'FOUND' or len(found['matches']) != 1:
            raise RuntimeError('symbol resolution not unique: ' + case + ':' + repr(found))
        path, line = found['matches'][0]['path'], found['matches'][0]['line']
    else:
        frame = next(x for x in snapshot['evidence'] if x.get('type') == 'stack_frame')
        path, line = frame['path'], frame['line']
    source = dispatcher._blob(path)
    tree = ast.parse(source)
    nodes = [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))
             and n.lineno <= line <= getattr(n,'end_lineno',0)]
    if len(nodes) > 1:
        nodes.sort(key=lambda n:n.end_lineno-n.lineno)
        nodes=nodes[:1]
    if len(nodes) != 1 or not getattr(nodes[0], 'end_lineno', None):
        raise RuntimeError('cannot resolve exact symbol span: ' + case)
    end = nodes[0].end_lineno
    raw = {'action':'read_source','path':path,'start':line,'end':end,'reason':'Trusted evaluator excerpt span'}
    result = dispatcher.dispatch(raw)
    result['id'] = 'oracle:' + hashlib.sha256((REV+path+str(line)+str(end)).encode()).hexdigest()[:16]
    result['notice'] = 'Exact static source at frozen revision; execution and intended contract are unverified.'
    return result, dispatcher.trace

def main():
    for p in (REG,LABELS):
        frozen = subprocess.check_output(['git','-C',str(ROOT),'show',REV+':'+p.relative_to(ROOT).as_posix()])
        if p.read_bytes() != frozen: raise RuntimeError('frozen metadata mismatch')
    fixtures.REGISTRY_PATH = REG
    fixture_by_name = {x['name']:x for x in fixtures.load_registry()}
    labels = {x['case']:x for x in json.loads(LABELS.read_text(encoding='utf8'))['labels']}
    old = json.loads(RESULTS.read_text(encoding='utf8'))
    initial = {}
    for row in old['rows']:
        if row['arm'] == 'A' and row['run'].get('investigation'):
            initial.setdefault(row['case'], row['run']['investigation']['evidence'])
    provider = Provider('ollama','qwen3.5:4b')
    prior=json.loads(OUT.read_text(encoding='utf8'))['rows'] if OUT.exists() else []
    rows=list(prior)
    store=Store(str(DB))
    completed={(r['case'],r['condition']) for r in rows}
    for fixture in fixtures.load_registry():
            case=fixture['name']
            if (case,'fixed') in completed and (case,'oracle') in completed: continue
            snap=copy.deepcopy(initial.get(case))
            if snap is None:
                snap={'incident_id':0,'evidence':[]}
                ev=fixture['event']; fr=ev['frame']
                event=Event(event_id=uuid.uuid4(),occurred_at=datetime.now(timezone.utc),commit=REV,
                    exception_type=ev['exception_type'],message=ev['message'],traceback='frozen synthetic report',
                    frames=[Frame(path=fr['path'],line=fr['line'],function=fr['function'])])
                iid,_=store.ingest(event)
                snap=investigator.collect(store,ROOT,iid)
            else:
                ev0=next(x for x in snap['evidence'] if x['type']=='event')
                fr0=next(x for x in snap['evidence'] if x['type']=='stack_frame')
                event=Event(event_id=uuid.UUID(ev0['event_id']),occurred_at=datetime.now(timezone.utc),commit=REV,
                    exception_type=ev0['exception_type'],message=ev0['message'],traceback='frozen synthetic report',
                    frames=[Frame(path=fr0['path'],line=fr0['line'],function=fr0['function'])])
                iid,_=store.ingest(event); snap['incident_id']=iid
            selected=labels[case]['useful_symbols']
            excerpt,trace=oracle_excerpt(case,fixture,snap,selected[0] if selected else None)
            for condition in ('fixed','oracle'):
                if (case,condition) in completed: continue
                current=copy.deepcopy(snap)
                if condition=='oracle': current['evidence'].append(excerpt)
                t=time.monotonic()
                result,_=investigator.investigate(store,ROOT,iid,provider,force=True,snapshot=current)
                elapsed=int((time.monotonic()-t)*1000)
                findings=result.get('findings')
                usage=result.get('usage') or {}
                rows.append({'case':case,'condition':condition,'status':result['status'],'findings':findings,
                    'error':result.get('error'),'usage':usage,'latency_ms':elapsed,
                    'excerpt_source':excerpt if condition=='oracle' else None,
                    'resolver_trace':trace if condition=='oracle' else None})
                OUT.write_text(json.dumps({'revision':REV,'model':provider.model,'context':2048,
                    'temperature':0,'thinking':False,'rows':rows},indent=2,ensure_ascii=False),encoding='utf8')
                completed.add((case,condition))
                print(case,condition,result['status'],(findings or {}).get('outcome'),usage,elapsed,flush=True)

if __name__=='__main__': main()
