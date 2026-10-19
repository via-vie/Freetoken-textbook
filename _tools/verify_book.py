from pathlib import Path
from urllib.parse import unquote,urlsplit
from html.parser import HTMLParser
import ast,hashlib,json,xml.etree.ElementTree as ET,sys
R=Path(__file__).resolve().parents[1];sys.stdout.reconfigure(encoding='utf-8')
class Links(HTMLParser):
    def __init__(self):super().__init__();self.ids=set();self.links=[];self.stack=[]
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if d.get('id'):assert d['id'] not in self.ids,d['id'];self.ids.add(d['id'])
        for a in ('href','src'):
            if a in d:self.links.append(d[a])
def main():
    manifest=json.loads((R/'_research/source-manifest.json').read_text(encoding='utf-8'));snap=R/manifest['snapshot_root']
    for f in manifest['files']:
        assert 'error' not in f,f
        b=(snap/f['path']).read_bytes()
        assert hashlib.sha256(b).hexdigest()==f['sha256'],f['path']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==f['git_blob'],f['path']
    refs=json.loads((R/'_book/references.json').read_text(encoding='utf-8'))
    idx=json.loads((R/'_research/source-index.json').read_text(encoding='utf-8'))['files']
    for ref in refs:
        pos=idx[ref['path']]['symbols'][ref['symbol']];assert ref['start']==pos['start'] and ref['end']==pos['end'],ref
    parsed={};pages=[R/'index.html',R/'source.html',*(R/'source').rglob('*.html')]
    for p in pages:
        reader=Links();reader.feed(p.read_text(encoding='utf-8'));parsed[p.resolve()]=reader
    link_count=0
    for p,reader in parsed.items():
        for href in reader.links:
            url=urlsplit(href)
            if url.scheme or url.netloc:continue
            target=(p.parent/unquote(url.path)).resolve() if url.path else p
            assert target.exists(),(p,href)
            if url.fragment and target in parsed:assert unquote(url.fragment) in parsed[target].ids,(p,href)
            link_count+=1
    figures=list((R/'figures').glob('*.svg'))
    for p in figures:
        root=ET.parse(p).getroot();assert root.get('viewBox') and root.find('{http://www.w3.org/2000/svg}title') is not None,p
    sys.path.insert(0,str(R/'labs'));import run
    assert run.check()['passed']
    for p in [*(R/'_tools').glob('*.py'),*(R/'labs').glob('*.py')]:ast.parse(p.read_text(encoding='utf-8'))
    stats=json.loads((R/'_book/build.json').read_text(encoding='utf-8'));assert stats['chapters']==22 and stats['figures']==12
    result=dict(passed=True,source_blobs=len(manifest['files']),references=len(refs),html_pages=len(pages),local_links=link_count,svg=len(figures),cpu=run.check(),hardware_engine_run=False)
    (R/'_book/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
