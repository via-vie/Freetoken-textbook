"""Check the exact tracked upload list without modifying project files."""
from pathlib import Path
import json,subprocess,sys
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
raw=subprocess.check_output(['git','ls-files','-z'],cwd=R)
paths=[x.decode('utf-8') for x in raw.split(b'\0') if x]
assert paths,'Nothing staged'
for name in paths:
    assert '__pycache__' not in Path(name).parts,name
    assert not name.startswith('_qa/'),name
    assert name not in ('_research/reference-chapter01.html','_research/paper.html'),name
    assert (R/name).is_file(),name
sizes=sorted(((R/p).stat().st_size,p) for p in paths)
assert sizes[-1][0]<100*1024*1024,sizes[-1]
print(json.dumps(dict(files=len(paths),total_bytes=sum(n for n,p in sizes),largest=[dict(path=p,bytes=n) for n,p in sizes[-5:]],source_snapshots=sum(p.startswith('_source/') for p in paths)),ensure_ascii=False,indent=2))
