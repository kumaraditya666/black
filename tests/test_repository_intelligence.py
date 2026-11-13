import os, subprocess
from pathlib import Path
import pytest
from blackbox.repository_intelligence import retrieve

@pytest.fixture
def repository(tmp_path):
    repo=tmp_path/'repo';repo.mkdir()
    subprocess.run(['git','init','-q',str(repo)],check=True)
    def commit(files):
        for name,text in files.items():
            p=repo/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf8')
        subprocess.run(['git','-C',str(repo),'add','.'],check=True,capture_output=True)
        env=os.environ.copy();env.update(GIT_AUTHOR_NAME='test',GIT_AUTHOR_EMAIL='test@local',GIT_COMMITTER_NAME='test',GIT_COMMITTER_EMAIL='test@local')
        subprocess.run(['git','-C',str(repo),'commit','-qm','fixture'],check=True,env=env)
        return subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    return repo,commit


def frame(path='pkg/b.py',name='parse',line=2):
    return {'path':path,'function':name,'line':line}


def test_cross_file_import_and_nested_call(repository):
    repo,commit=repository
    rev=commit({'pkg/b.py':'def parse(x):\n    return int(x)\n',
                'pkg/a.py':'from b import parse as convert\ndef total(xs):\n    return sum(convert(x) for x in xs)\n'})
    result=retrieve(repo,rev,frame())
    assert [(e['function'],e['relation']) for e in result['excerpts']]==[('total','caller')]
    assert 'sum(convert(x)' in result['excerpts'][0]['source']
    assert result['excerpts'][0]['commit']==rev
    assert any('int' in x for x in result['limitations'])


def test_same_file_callee_and_cycles_are_bounded(repository):
    repo,commit=repository
    rev=commit({'pkg/b.py':'def parse(x):\n    return helper(x)\ndef helper(x):\n    return parse(x)\n'})
    result=retrieve(repo,rev,frame())
    assert len(result['excerpts'])==1 and result['excerpts'][0]['function']=='helper'
    assert result['excerpts'][0]['relation'] in ('caller','callee')


def test_duplicate_definitions_are_unresolved(repository):
    repo,commit=repository
    rev=commit({'pkg/b.py':'def parse(x):\n    return helper(x)\ndef helper(x):\n    return 1\ndef helper(x):\n    return 2\n'})
    result=retrieve(repo,rev,frame())
    assert not result['excerpts'] and any('helper' in x for x in result['limitations'])


def test_missing_dynamic_and_malformed_sources(repository):
    repo,commit=repository
    rev=commit({'pkg/b.py':'from missing import compute\ndef parse(x):\n    return compute(x) + x.dynamic()\n','pkg/broken.py':'def broken(:\n'})
    result=retrieve(repo,rev,frame(line=3))
    assert not result['excerpts']
    assert any('Malformed' in x for x in result['limitations'])
    assert any('compute' in x and 'dynamic' in x for x in result['limitations'])


def test_uses_pinned_revision_not_worktree(repository):
    repo,commit=repository
    first=commit({'pkg/b.py':'def parse(x):\n    return helper(x)\ndef helper(x):\n    return 1\n'})
    commit({'pkg/b.py':'def parse(x):\n    return helper(x)\ndef helper(x):\n    return 999\n'})
    result=retrieve(repo,first,frame())
    assert 'return 1' in result['excerpts'][0]['source'] and '999' not in result['excerpts'][0]['source']
    assert retrieve(repo,'0'*40,frame())['limitations']


def test_path_escape_and_missing_frame_rejected(repository):
    repo,commit=repository;rev=commit({'pkg/b.py':'def parse(x):\n    return x\n'})
    for name in ('../b.py','/tmp/b.py','pkg/../../b.py','pkg\\b.py','pkg/no.py'):
        assert not retrieve(repo,rev,frame(path=name))['excerpts']


def test_context_limit_is_explicit(repository):
    repo,commit=repository
    rev=commit({'pkg/b.py':'def parse(x):\n    return helper(x)\ndef helper(x):\n    return x + 123456789\n'})
    result=retrieve(repo,rev,frame(),max_chars=5)
    assert not result['excerpts'] and any('context limit' in x for x in result['limitations'])


def test_symlink_git_object_not_read(repository):
    repo,commit=repository;rev=commit({'pkg/b.py':'def parse(x):\n    return x\n'})
    oid=subprocess.check_output(['git','-C',str(repo),'hash-object','-w','--stdin'],input=b'/etc/passwd').decode().strip()
    subprocess.run(['git','-C',str(repo),'update-index','--add','--cacheinfo','120000,'+oid+',pkg/link.py'],check=True)
    env=os.environ.copy();env.update(GIT_AUTHOR_NAME='test',GIT_AUTHOR_EMAIL='test@local',GIT_COMMITTER_NAME='test',GIT_COMMITTER_EMAIL='test@local')
    subprocess.run(['git','-C',str(repo),'commit','-qm','link'],env=env,check=True)
    rev=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    result=retrieve(repo,rev,frame())
    assert any('symlink' in x for x in result['limitations'])
    assert not retrieve(repo,rev,frame(path='pkg/link.py'))['excerpts']


def test_module_attribute_import_and_class_metadata(repository):
    repo,commit=repository
    rev=commit({'pkg/b.py':'import a\ndef parse(x):\n    return a.helper(x)\n',
                'pkg/a.py':'def helper(x):\n    return x + 1\n'})
    result=retrieve(repo,rev,frame(line=3))
    assert result['excerpts'][0]['function']=='helper' and result['excerpts'][0]['relation']=='callee'


def test_nested_scopes_do_not_create_outer_caller(repository):
    repo,commit=repository
    rev=commit({'pkg/b.py':'def parse(x):\n    return int(x)\ndef outer():\n    def inner():\n        return parse(1)\n    return inner\n'})
    result=retrieve(repo,rev,frame())
    assert [x['function'] for x in result['excerpts']]==['inner']


def test_patch_prompt_includes_read_only_context_and_keeps_scope():
    import json
    from types import SimpleNamespace
    from blackbox.repair.patch import build_prompt
    source='def foo():\n    return 1\n'
    context={'id':'code:0','type':'code_context','path':'outside.py','line':1,'end_line':2,
             'function':'caller','relation':'caller','source':'def caller():\n    return sum([foo()])',
             'commit':'a'*40,'notice':'Static only'}
    snapshot={'evidence':[{'id':'event:x','type':'event','exception_type':'ValueError','message':'bad','commit':'a'*40},context]}
    eligibility=SimpleNamespace(investigation={'evidence':snapshot},fixture={'reproduction':{'test':'tests/test_repro.py::test_x'},'expected_behavior':'safe','allowed_files':['app.py']},hypothesis={'explanation':'test','supporting_evidence':['event:x']},frame={'path':'app.py'})
    _,prompt=build_prompt(eligibility,{'app.py':source,'tests/test_repro.py':'def test_x(): pass'})
    data=json.loads(prompt)
    assert data['related_code'][0]['path']=='outside.py' and data['allowed_files']==['app.py']
    assert 'outside.py' not in data['source']


def test_class_method_caller_identifies_owning_class(repository):
    repo,commit=repository
    rev=commit({'pkg/b.py':'def parse(x):\n    return int(x)\nclass Reader:\n    def load(self, x):\n        return parse(x)\n'})
    result=retrieve(repo,rev,frame())
    assert result['excerpts'][0]['class']=={'name':'Reader','line':3}
    assert result['excerpts'][0]['function']=='load'


def test_limitation_output_is_bounded():
    from blackbox.repository_intelligence import _LimitedNotes, MAX_LIMITATIONS
    notes=_LimitedNotes()
    for _ in range(100): notes.append('x'*1000)
    assert len(notes)==MAX_LIMITATIONS+1 and len(notes[0])==200 and 'omitted' in notes[-1]
