from pathlib import Path
import ast,json,sys,re,html
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
S=R/json.loads((R/'_research/pinned.json').read_text())['snapshot_root']
arg=sys.argv[1]
if arg=='reference':
    s=(R/'_research/reference-chapter01.html').read_text(encoding='utf-8')
    s=re.sub(r'<(script|style)[\s\S]*?</\1>','',s)
    print(html.unescape(re.sub('<[^>]+>','\n',s)))
elif arg=='list':
    for p in S.rglob('*.py'):
        if any(x in str(p.relative_to(S)).replace('\\','/') for x in sys.argv[2:]):
            try:t=ast.parse(p.read_text(encoding='utf-8'))
            except SyntaxError:continue
            print('\n'+p.relative_to(S).as_posix())
            for c in t.body:
                if isinstance(c,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef)):
                    print(c.lineno,c.end_lineno,c.name)
                    if isinstance(c,ast.ClassDef):
                        for x in c.body:
                            if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)):print(' ',x.lineno,x.end_lineno,c.name+'.'+x.name)
else:
    lines=(S/arg).read_text(encoding='utf-8').splitlines()
    lo=int(sys.argv[2]) if len(sys.argv)>2 else 1
    hi=int(sys.argv[3]) if len(sys.argv)>3 else len(lines)
    for i in range(lo,min(hi,len(lines))+1):print(f'{i:5} {lines[i-1]}')
