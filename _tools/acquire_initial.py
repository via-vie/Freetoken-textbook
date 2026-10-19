from pathlib import Path
import ast,concurrent.futures,hashlib,json,time,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'_research';OUT.mkdir(parents=True,exist_ok=True)
OWNER='FlashML-org';REPO='FreeToken'
def save(name,url):
    req=urllib.request.Request(url,headers={'User-Agent':'freetoken-textbook-reader','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=35) as res:data=res.read()
    (OUT/name).write_bytes(data)
    return data
meta=json.loads(save('repository.json',f'https://api.github.com/repos/{OWNER}/{REPO}'))
commit=json.loads(save('commit.json',f"https://api.github.com/repos/{OWNER}/{REPO}/commits/{meta['default_branch']}"))
sha=commit['sha']
tree=json.loads(save('repository-tree.json',f'https://api.github.com/repos/{OWNER}/{REPO}/git/trees/{sha}?recursive=1'))
for name in ('AGENTS.md','CLAUDE.md','CONTRIBUTING.md','README.md','LICENSE','pyproject.toml'):
    try:save(name,f'https://raw.githubusercontent.com/{OWNER}/{REPO}/{sha}/{name}')
    except urllib.error.HTTPError as e:print(name,e.code)
try:save('tags.json',f'https://api.github.com/repos/{OWNER}/{REPO}/tags?per_page=10')
except urllib.error.HTTPError as e:print('tags',e.code)
reference='https://tutorial.baimuyuan.online/minimind-tutorial/chapters/01-LLM%E5%85%A8%E6%99%AF%E4%B8%8E%E9%A1%B9%E7%9B%AE%E5%AF%BC%E8%A7%88'
try:save('reference-chapter01.html',reference)
except Exception as e:print('reference',type(e).__name__)
try:save('paper.html','https://arxiv.org/html/2608.16157v1')
except Exception as e:print('paper',type(e).__name__)
config={'owner':OWNER,'repo':REPO,'commit':sha,'commit_date':commit['commit']['committer']['date'],'snapshot_root':'_source/FreeToken-'+sha[:7]}
(OUT/'pinned.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
print(json.dumps(dict(commit=sha,date=config['commit_date'],files=len(tree['tree']),message=commit['commit']['message'].splitlines()[0]),ensure_ascii=True))
snapshot=ROOT/config['snapshot_root'];snapshot.mkdir(parents=True,exist_ok=True)
suffixes={'.py','.md','.rst','.c','.cc','.cpp','.cu','.cuh','.h','.hpp','.toml','.json','.yaml','.yml','.txt','.html','.js'}
roots=('python/freetoken/','tests/','docs/','benchmarks/')
chosen=[f for f in tree['tree'] if f['type']=='blob' and f.get('size',0)<=2_000_000 and
        ((f['path'].startswith(roots) and Path(f['path']).suffix in suffixes) or
         f['path'] in ('AGENTS.md','CLAUDE.md','CONTRIBUTING.md','README.md','LICENSE','pyproject.toml','setup.py'))]
def fetch(record):
    path=record['path'];target=snapshot/path;target.parent.mkdir(parents=True,exist_ok=True)
    def valid(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==record['sha']
    if target.exists() and valid(target.read_bytes()):raw=target.read_bytes()
    else:
        last=None
        for attempt in range(4):
            try:
                req=urllib.request.Request(f'https://raw.githubusercontent.com/{OWNER}/{REPO}/{sha}/{path}',headers={'User-Agent':'freetoken-textbook-reader'})
                with urllib.request.urlopen(req,timeout=45) as res:raw=res.read()
                if not valid(raw):raise ValueError('Git blob identity mismatch')
                target.write_bytes(raw);break
            except Exception as err:last=err;time.sleep(attempt+1)
        else:return {'path':path,'error':type(last).__name__}
    return {'path':path,'git_blob':record['sha'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'lines':len(raw.splitlines())}
records=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for record in pool.map(fetch,chosen):
        records.append(record)
        if len(records)%40==0:print(f'Sources: {len(records)}/{len(chosen)}',flush=True)
manifest={**config,'files':records}
(OUT/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
index={}
for record in records:
    if 'error' in record:continue
    path=record['path'];info={**record,'symbols':{}}
    if path.endswith('.py'):
        try:
            tree_ast=ast.parse((snapshot/path).read_text(encoding='utf-8'),filename=path)
            def walk(node,prefix=''):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
                        name=prefix+child.name
                        info['symbols'][name]={'start':min([child.lineno]+[d.lineno for d in getattr(child,'decorator_list',[])]),'end':child.end_lineno}
                        walk(child,name+'.')
                    elif not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):walk(child,prefix)
            walk(tree_ast)
        except SyntaxError as err:info['ast_error']=str(err)
    index[path]=info
(OUT/'source-index.json').write_text(json.dumps({'commit':sha,'snapshot_root':config['snapshot_root'],'files':index},ensure_ascii=False,indent=2),encoding='utf-8')
errors=[r for r in records if 'error' in r]
print(json.dumps({'downloaded':len(index),'failed':errors,'source_lines':sum(r['lines'] for r in index.values())},ensure_ascii=True),flush=True)
if errors:raise SystemExit(1)
