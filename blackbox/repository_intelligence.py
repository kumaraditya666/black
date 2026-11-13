"""Bounded static Python relationships read only from a recorded Git revision.

Name matches are possibilities, never evidence of execution or dynamic binding. The search scope is
one source directory subtree, with explicit caps; unsupported or omitted material is reported.
"""
import ast
import os
import re
import subprocess
from pathlib import Path, PurePosixPath
from .redaction import redact

MAX_FILES = 40
MAX_FILE_BYTES = 65536
MAX_TREE_BYTES = 200000
MAX_EXCERPTS = 3
MAX_CONTEXT_CHARS = 1100
MAX_PATH_CHARS = 512
MAX_LIMITATIONS = 10


class _LimitedNotes(list):
    def append(self, item):
        if len(self) < MAX_LIMITATIONS:
            super().append(str(item)[:200])
        elif len(self) == MAX_LIMITATIONS:
            super().append('Additional limitations omitted due to output limit.')


def _git(repo, *args):
    env = os.environ.copy()
    env.update({'GIT_TERMINAL_PROMPT':'0', 'GIT_CONFIG_NOSYSTEM':'1',
                'GIT_CONFIG_GLOBAL':os.devnull, 'GIT_NO_REPLACE_OBJECTS':'1'})
    return subprocess.run(['git','-C',str(repo),*args],capture_output=True,timeout=10,env=env,check=False)


def _safe_path(value):
    if not isinstance(value,str) or not value or len(value)>MAX_PATH_CHARS or redact(value)!=value or '\\' in value or ':' in value or any(ord(x)<32 for x in value):
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and all(x not in ('', '.', '..') for x in value.split('/')) and not value.startswith('-')


def _calls(node):
    """Calls lexically in this function, not those belonging to nested functions/classes."""
    result=[]
    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, child):
            if child is node:
                for part in child.body: self.visit(part)
        visit_AsyncFunctionDef = visit_FunctionDef
        def visit_ClassDef(self, child): pass
        def visit_Lambda(self, child): pass
        def visit_Call(self, child):
            result.append(child)
            self.generic_visit(child)
    Visitor().visit(node)
    return result


def retrieve(repo: Path, commit: str, frame: dict, max_chars: int = MAX_CONTEXT_CHARS) -> dict:
    """Return one-hop related whole functions and limitations; no working-tree source is read."""
    out={'excerpts':[], 'limitations':_LimitedNotes(), 'notice':'Static possibilities only; execution and binding are unverified.'}
    path=frame.get('path',''); function=frame.get('function','')
    if not re.fullmatch(r'[0-9a-f]{40}',str(commit)) or not _safe_path(path) or not path.endswith('.py'):
        out['limitations'].append('Invalid revision or source path.'); return out
    parent=PurePosixPath(path).parent
    scope='' if str(parent)=='.' else str(parent)+'/'
    try:
        args=['ls-tree','-r','-z','--full-tree',commit]
        if scope: args.extend(['--',scope])
        listed=_git(repo,*args)
        if listed.returncode or len(listed.stdout)>MAX_TREE_BYTES:
            out['limitations'].append('Revision tree unavailable or tree listing exceeds limit.'); return out
        entries=[]
        for raw in listed.stdout.split(b'\0'):
            if not raw: continue
            meta, raw_path=raw.split(b'\t',1)
            mode,kind,_=meta.decode('ascii').split()
            name=raw_path.decode('utf8')
            if name.endswith('.py') and _safe_path(name) and '/tests/' not in '/'+name and not name.endswith('/conftest.py'):
                if mode not in ('100644','100755') or kind!='blob':
                    out['limitations'].append('Skipped symlink or unsupported Git object: '+name); continue
                entries.append(name)
        entries=sorted(entries)
        if path not in entries:
            out['limitations'].append('Frame source missing, unsafe, or not a regular Python file.'); return out
        if len(entries)>MAX_FILES:
            out['limitations'].append('File-count limit reached; dependency search incomplete.')
            entries=[path]+[x for x in entries if x!=path][:MAX_FILES-1]
        modules={}; sources={}; trees={}
        for name in entries:
            size=_git(repo,'cat-file','-s',commit+':'+name)
            if size.returncode or not size.stdout.strip().isdigit() or int(size.stdout)>MAX_FILE_BYTES:
                out['limitations'].append('Source unavailable or too large: '+name); continue
            blob=_git(repo,'show',commit+':'+name)
            if blob.returncode or b'\0' in blob.stdout:
                out['limitations'].append('Source unavailable or binary: '+name); continue
            try:
                source=blob.stdout.decode('utf8'); tree=ast.parse(source)
            except (UnicodeDecodeError,SyntaxError,RecursionError,ValueError):
                out['limitations'].append('Malformed or unsupported Python: '+name); continue
            relative=name[len(scope):] if name.startswith(scope) else name
            module=relative[:-3].replace('/','.')
            if module.endswith('.__init__'): module=module[:-9]
            modules[module]=name; sources[name]=source; trees[name]=tree
        defs={}; imports={}; classes={}
        for name,tree in trees.items():
            relative=name[len(scope):] if name.startswith(scope) else name
            module=relative[:-3].replace('/','.')
            if module.endswith('.__init__'): module=module[:-9]
            alias={}
            for node in tree.body:
                if isinstance(node,ast.ImportFrom) and node.module and node.level in (0,1):
                    for item in node.names:
                        if item.name!='*': alias[item.asname or item.name]=(node.module,item.name)
                elif isinstance(node,ast.Import):
                    for item in node.names: alias[item.asname or item.name.split('.')[0]]=(item.name,None)
            imports[name]=alias
            for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
                for method in cls.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        classes[(name, method.name, method.lineno)] = (cls.name, cls.lineno)
            # Definitions include classes and nested functions; duplicate names are deliberately ambiguous.
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    defs.setdefault((name,node.name),[]).append(node)
        roots=[n for n in defs.get((path,function),[]) if n.lineno<=frame.get('line',0)<=getattr(n,'end_lineno',n.lineno)]
        if len(roots) != 1:
            out['limitations'].append('No unique enclosing function for reported frame.'); return out
        edges=[]; unresolved=set()
        for (caller_file,caller_name), nodes in defs.items():
            if len(nodes)!=1: continue
            for call in _calls(nodes[0]):
                target_file=caller_file; target=None
                if isinstance(call.func,ast.Name):
                    target=call.func.id
                    if target in imports[caller_file]:
                        module,target=imports[caller_file][target]
                        target_file=modules.get(module)
                elif isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name):
                    imported=imports[caller_file].get(call.func.value.id)
                    if imported and imported[1] is None:
                        target_file=modules.get(imported[0]); target=call.func.attr
                matches=defs.get((target_file,target),[]) if target_file and target else []
                if len(matches)==1:
                    edges.append(((caller_file,caller_name),(target_file,target),call.lineno))
                elif caller_file==path and caller_name==function:
                    unresolved.add(ast.unparse(call.func)[:80])
        if unresolved:
            out['limitations'].append('Unresolved or dynamic calls: '+', '.join(sorted(unresolved)[:8]))
        key=(path,function); candidates=[]
        for caller,callee,line in sorted(set(edges)):
            if caller==key and callee!=key: candidates.append((callee,'callee',line))
            if callee==key and caller!=key: candidates.append((caller,'caller',line))
        seen=set(); used=0
        for target,relation,callline in candidates:
            if target in seen: continue
            seen.add(target)
            if len(out['excerpts'])>=MAX_EXCERPTS:
                out['limitations'].append('Relationship excerpt count limit reached.'); break
            node=defs[target][0]; lines=sources[target[0]].splitlines(); end=node.end_lineno or node.lineno
            text='\n'.join(lines[node.lineno-1:end]); text=redact(text)
            if used+len(text)>max_chars:
                out['limitations'].append('Related function exceeds context limit: '+target[0]+':'+str(node.lineno)); continue
            excerpt={'path':target[0], 'function':target[1], 'line':node.lineno,
                     'end_line':end, 'commit':commit, 'relation':relation,
                     'call_line':callline, 'source':text}
            owner=classes.get((target[0], target[1], node.lineno))
            if owner: excerpt['class']={'name':owner[0], 'line':owner[1]}
            out['excerpts'].append(excerpt)
            used+=len(text)
        return out
    except (OSError,subprocess.TimeoutExpired,UnicodeDecodeError,ValueError,RecursionError):
        out['limitations'].append('Git or static analysis failed; context incomplete.'); return out
