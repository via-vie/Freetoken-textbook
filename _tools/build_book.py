"""Build an offline, source-pinned textbook. No runtime dependencies."""
from pathlib import Path
from urllib.parse import quote
import hashlib,html,json,re,sys
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'labs'))
import run as labs
import diagrams
B=R/'_book';B.mkdir(exist_ok=True)
PIN=json.loads((R/'_research/pinned.json').read_text())
IDX=json.loads((R/'_research/source-index.json').read_text(encoding='utf-8'))['files']
SNAP=R/PIN['snapshot_root'];REFS=[]
def e(s):return html.escape(str(s),quote=True)
def inline(s):
    s=e(s);s=re.sub(r'\[([^\]]+)\]\(([^ )]+)\)',r'<a href="\2">\1</a>',s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    return re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
def source(spec):
    path,symbol,note=spec.split('|',2);path=path if path in IDX else 'python/freetoken/'+path
    assert path in IDX,path
    info=IDX[path];pos=info['symbols'][symbol];lo,hi=pos['start'],pos['end']
    REFS.append(dict(path=path,symbol=symbol,start=lo,end=hi))
    local='source/'+quote(path)+'.html#L'+str(lo)
    remote=f"https://github.com/FlashML-org/FreeToken/blob/{PIN['commit']}/{quote(path)}#L{lo}-L{hi}"
    lines=(SNAP/path).read_text(encoding='utf-8').splitlines()
    excerpts={
        'Scheduler._process_last_data':[(312,348),(350,399),(419,429)],
        'Scheduler.overlap_loop':[(214,251),(253,261)],
        'GraphRunner._capture_graphs':[(174,191),(204,230)],
        '_ensure_experts_hybrid_kernel':[(317,347),(361,398),(413,417)],
    }
    spans=excerpts.get(symbol,[(lo,hi)] if hi-lo<80 else [(lo,min(hi,lo+25))])
    chunks=[]
    for start,end in spans:
        assert lo<=start<=end<=hi,(symbol,start,end,lo,hi)
        chunks.append(f'--- L{start}–L{end} ---\n'+'\n'.join(f'{i:5}  {lines[i-1]}' for i in range(start,end+1)))
    code='\n\n'.join(chunks)
    caption='显示完整符号范围。' if spans==[(lo,hi)] else '显示标注行号的选段，可能省略中间分支；完整控制流请打开本地源码核对。'
    return f'<details class="sourcecard"><summary>源码对照 · <code>{e(symbol)}</code></summary><p>{inline(note)}</p><p class="small">{e(path)} · L{lo}–L{hi}</p><p><a href="{local}" target="_blank">本地完整源码 ↗</a>　<a href="{remote}" target="_blank" rel="noreferrer">官方固定提交 ↗</a></p><details><summary>展开真实代码 / 选段</summary><p class="small">{caption}</p><pre>{e(code)}</pre></details></details>'
def render(lines):
    out=[];p=[];i=0
    def flush():
        if p:out.append('<p>'+inline(' '.join(p))+'</p>');p.clear()
    while i<len(lines):
        s=lines[i].strip()
        if not s:flush()
        elif s.startswith('## '):flush();out.append('<h3>'+e(s[3:])+'</h3>')
        elif s.startswith('~~~'):
            flush();code=[];i+=1
            while i<len(lines) and not lines[i].startswith('~~~'):code.append(lines[i]);i+=1
            out.append('<div class="codeblock"><button class="copy">复制</button><pre><code>'+e('\n'.join(code))+'</code></pre></div>')
        elif s.startswith('@source '):flush();out.append(source(s[8:]))
        elif s.startswith('@figure '):
            flush();key=s[8:];assert key in diagrams.FIGS,key
            out.append(f'<figure><a href="figures/{key}.svg" target="_blank"><img src="figures/{key}.svg" loading="lazy" alt="{e(diagrams.FIGS[key][0])}"></a><figcaption>{e(diagrams.FIGS[key][0])} · 点击打开矢量图放大阅读</figcaption></figure>')
        elif s.startswith('@lab '):
            flush();key=s[5:];assert key in labs.ALL
            out.append(f'<div class="lab" data-lab="{key}"><span class="label">可检查的教学实验</span><h4>{e(labs.ALL[key]()["label"])}</h4><p>点击事件查看完整精度数据；页面显示的小数约三位。运行 <code>python labs/run.py {key}</code> 可复算。</p><div class="labbuttons"></div><div class="labsummary"></div><pre class="laboutput"></pre></div>')
        elif s.startswith('@note '):
            flush();title,body=s[6:].split('|',1);out.append('<div class="note"><strong>'+inline(title)+'</strong><p>'+inline(body)+'</p></div>')
        elif s.startswith('@check '):
            flush();q,a=s[7:].split('|',1);out.append('<details class="exercise"><summary>停一下，自己推 · '+inline(q)+'</summary><p>'+inline(a)+'</p></details>')
        elif s.startswith('@next '):flush();out.append('<p class="bridge">'+inline(s[6:])+'</p>')
        elif s.startswith('|'):
            flush();rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                rows.append(lines[i].strip().strip('|').split('|'));i+=1
            out.append('<div class="tablewrap"><table>')
            for j,row in enumerate(rows):
                if all(re.fullmatch(r'[-: ]+',x) for x in row):continue
                tag='th' if j==0 else 'td';out.append('<tr>'+''.join(f'<{tag}>{inline(c.strip())}</{tag}>' for c in row)+'</tr>')
            out.append('</table></div>');i-=1
        else:p.append(s)
        i+=1
    flush();return '\n'.join(out)
def main():
    diagrams.build(R)
    text=(B/'manuscript.txt').read_text(encoding='utf-8');chapters=[];nav=[];body=[];last=''
    for chunk in re.split(r'(?m)^@chapter ',text)[1:]:
        head,*lines=chunk.splitlines();num,part,title,question=head.split('|',3)
        assert lines[0].startswith('@handoff ')
        inp,process,out=lines.pop(0)[9:].split('|',2)
        content=render(lines);cid='ch'+num
        chapters.append(dict(id=cid,title=title,part=part,question=question,input=inp,process=process,output=out))
        if part!=last:nav.append('<p class="part">'+e(part)+'</p>');last=part
        nav.append(f'<a href="#{cid}">{num}　{e(title)}</a>')
        body.append(f'<article id="{cid}" class="chapter" data-title="{e(title)}"><div class="chapterkicker">{e(part)} · 第 {int(num)} 章</div><h2>{e(title)}</h2><div class="question"><span class="label">从这个问题开始</span><p>{e(question)}</p></div><div class="handoff"><p><b>带着什么来</b>　{inline(inp)}</p><p><b>本章做什么</b>　{inline(process)}</p><p><b>交出什么</b>　{inline(out)}</p></div>{content}<div class="chapterfoot"><a href="#ch{max(1,int(num)-1):02}">← 上一章</a><button class="done">标记学懂 / 取消</button><a href="#ch{int(num)+1:02}" class="next">下一章 →</a></div></article>')
    body[-1]=body[-1].replace('href="#ch23" class="next">下一章 →','href="#ch01" class="next">回到第一章')
    version=(SNAP/'python/freetoken/version.py').read_text(encoding='utf-8')
    ver=re.search(r'__version__\s*=\s*[\'"]([^\'"]+)',version).group(1)
    data={k:f() for k,f in labs.ALL.items()}
    data_json=json.dumps(data,ensure_ascii=False).replace('<','\\u003c')
    css=(R/'assets/book.css').read_text(encoding='utf-8');js=(R/'assets/book.js').read_text(encoding='utf-8')
    page=f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="从一条请求读懂 FreeToken：MoE 专家缓存、CPU/GPU 协同、双缓冲、CUDA Graph 与状态复用的源码教材。"><title>FreeToken 推理引擎：从一条请求读懂源码</title><style>{css}</style></head><body>
<aside id="sidebar"><div class="brand">FreeToken<span>推理引擎源码教材</span></div><button id="menu" aria-expanded="false">目录 / 搜索</button><div id="navcontent"><p class="small">固定源码 {e(ver)} · {PIN['commit'][:7]}<br>循着数据走，沿着状态读</p><label for="search">搜索全书</label><input id="search" placeholder="如 slot、cached_len、双缓冲"><p id="searchcount" class="small"></p><p id="progress" class="small"></p><nav>{''.join(nav)}</nav></div></aside>
<main><header class="cover"><span class="label">从问题出发 · 亲手算清 · 回到源码</span><h1>FreeToken 推理引擎<br><em>从一条请求读懂源码</em></h1><p>大模型的专家放不下时，一次 token 生成怎样跨越 CPU 内存与 GPU 显存？</p><div class="badges"><span>{len(chapters)} 章连续阅读</span><span>{len(diagrams.FIGS)} 幅 SVG</span><span>8 个 CPU 教学实验</span><span>单 A100 实验路线</span></div><div class="toolbar"><a href="source.html">本地源码索引</a><a href="#ch20">实验与验收</a><button id="smaller">字号 −</button><button id="larger">字号 +</button><button id="print">打印全书 / PDF</button></div></header>{''.join(body)}
<footer>依据官方 FreeToken {e(ver)} · commit {PIN['commit']}。教学实例、时间和容量假设均有标识。未在本机执行真实引擎或 A100 跑分。<br>原始源码归上游作者，Apache-2.0；本书组织受白木原 MiniMind 教程及鱼书循序讲解方式启发，正文与图解为原创。</footer></main><script id="labdata" type="application/json">{data_json}</script><script>{js}</script></body></html>'''
    (R/'index.html').write_text(page,encoding='utf-8')
    # Build offline source pages only for referenced files + useful docs/entries.
    chosen={r['path'] for r in REFS}|{'LICENSE','pyproject.toml','README.md','docs/install.md','docs/cli.md','docs/models.md','docs/quickstart.md','tests/README.md','benchmarks/README.md'}
    source_nav=[]
    for path in sorted(chosen):
        info=IDX[path];raw=(SNAP/path).read_bytes();assert hashlib.sha256(raw).hexdigest()==info['sha256'],path
        target=R/'source'/(path+'.html');target.parent.mkdir(parents=True,exist_ok=True)
        back='../'*len(Path(path).parts)
        options=''.join(f'<option value="L{v["start"]}">{e(k)} · L{v["start"]}–L{v["end"]}</option>' for k,v in info['symbols'].items())
        lines=''.join(f'<div class="line" id="L{i}"><a href="#L{i}">{i}</a><code>{e(line) or " "}</code></div>' for i,line in enumerate(raw.decode('utf-8').splitlines(),1))
        src=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{e(path)}</title><style>body{{margin:0;background:#faf9f5;color:#24382e;font:14px/1.8 Consolas,monospace}}header{{padding:20px;overflow-wrap:anywhere}}h1{{font-size:18px}}a{{color:#286b58}}select{{max-width:96%;padding:8px}}main{{overflow:auto}}.line{{display:flex;min-width:max-content}}.line:target{{background:#fff0a6}}.line>a{{width:60px;flex:0 0 60px;text-align:right;margin-right:18px;text-decoration:none;color:#78857b}}code{{white-space:pre;padding-right:20px}}.line:hover{{background:#edf2e9}}</style><header><a href="{back}index.html">← 教材</a> · <a href="{back}source.html">源码索引</a> · <a href="https://github.com/FlashML-org/FreeToken/blob/{PIN['commit']}/{quote(path)}">官方固定源码</a><h1>{e(path)}</h1><p>{e(ver)} · {PIN['commit']} · {info['lines']} 行 · 原文件未修改</p><select id="symbol" aria-label="跳转函数"><option value="">选择函数或类</option>{options}</select></header><main>{lines}</main><script>document.getElementById('symbol').onchange=e=>{{if(e.target.value)location.hash=e.target.value}}</script></html>'''
        target.write_text(src,encoding='utf-8')
        source_nav.append(f'<li><a href="source/{quote(path)}.html">{e(path)}</a> · {info["lines"]} 行</li>')
    (R/'source.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>FreeToken 本地源码索引</title><style>body{{max-width:1100px;margin:30px auto;padding:20px;font:16px/1.8 system-ui;background:#faf9f5}}li{{overflow-wrap:anywhere}}a{{color:#286b58}}input{{padding:10px;width:80%}}</style><a href="index.html">← 教材</a><h1>固定源码阅读索引</h1><p>commit {PIN['commit']}。本页收录本书直接引用的 {len(chosen)} 个文件；采集快照共 {len(IDX)} 个文件，位于 _source，属于选取的源码快照，不是可安装完整克隆。<a href="source/LICENSE.html">上游 LICENSE</a></p><input id="q" aria-label="搜索文件路径" placeholder="路径关键词"><ul>{''.join(source_nav)}</ul><script>document.getElementById('q').oninput=e=>document.querySelectorAll('li').forEach(x=>x.hidden=!x.textContent.toLowerCase().includes(e.target.value.toLowerCase()))</script></html>''',encoding='utf-8')
    for name,value in [('references',REFS),('chapters',chapters),('lab-results',data)]:
        (B/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    stats=dict(chapters=len(chapters),figures=len(diagrams.FIGS),source_files=len(chosen),source_references=len(REFS),unique_symbols=len({(x['path'],x['symbol']) for x in REFS}),checks=text.count('@check '),characters=len(text),version=ver,commit=PIN['commit'],cpu=labs.check())
    (B/'build.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=True))
if __name__=='__main__':main()
