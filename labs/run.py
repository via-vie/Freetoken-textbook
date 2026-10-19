"""Small deterministic teaching experiments; no FreeToken import and no GPU claims."""
import argparse,json,math,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
def mm(a,b):return [[sum(x*y for x,y in zip(row,col)) for col in zip(*b)] for row in a]
def softmax(x):
    p=[math.exp(v-max(x)) for v in x];return [v/sum(p) for v in p]
def moe():
    x=[[1.,0.,-1.,2.]]
    router=[[.1,.3,-.2,.4,0.,-.1,.2,.1],[.2,-.1,.1,0.,.3,.2,0.,-.2],[0.,.2,.1,-.1,.1,0.,.3,-.1],[.1,.2,0.,.3,-.2,.1,-.1,.2]]
    logits=mm(x,router)[0];probs=softmax(logits)
    ids=sorted(range(8),key=lambda e:(-probs[e],e))[:2]
    weights=[probs[e]/sum(probs[i] for i in ids) for e in ids]
    def expert(e):
        # Every matrix element has a deterministic definition, not a trained weight.
        gate=[[(e+1)*(i+1)*(j+1)/100 for j in range(6)] for i in range(4)]
        up=[[(i-j+e+1)/20 for j in range(6)] for i in range(4)]
        down=[[(j+1)*(i+1)/(50*(e+1)) for j in range(4)] for i in range(6)]
        g=mm(x,gate)[0];u=mm(x,up)[0]
        mid=[a/(1+math.exp(-a))*b for a,b in zip(g,u)]
        return dict(id=e,gate=gate,up=up,down=down,g=g,u=u,mid=mid,y=mm([mid],down)[0])
    es=[expert(e) for e in ids]
    y=[sum(w*z['y'][j] for w,z in zip(weights,es)) for j in range(4)]
    return dict(label='教学 MoE：float64，top-2 后重新归一化；不代表所有模型 router',x=x,router=router,logits=logits,probabilities=probs,selected=ids,weights=weights,experts=es,output=y)
def cache():
    # LRU simulator for one global pool, keyed by (layer,expert).
    requests=[[(0,1),(0,3)],[(1,1),(1,4)],[(0,1),(0,2)],[(1,4),(1,6)]]
    slots=[None]*4;age={};rows=[];clock=0
    for step,needed in enumerate(requests):
        before=slots.copy();hits=[k for k in needed if k in slots];misses=[k for k in needed if k not in slots]
        victims=[]
        for key in misses:
            free=next((i for i,k in enumerate(slots) if k is None),None)
            if free is None:
                candidates=[i for i,k in enumerate(slots) if k not in needed]
                free=min(candidates,key=lambda i:age[slots[i]])
                victims.append(slots[free]);del age[slots[free]]
            slots[free]=key;age[key]=clock
        for k in needed:clock+=1;age[k]=clock
        rows.append(dict(step=step+1,routed=needed,before=before,hits=hits,misses=misses,victims=victims,after=slots.copy(),slot_ids=[slots.index(k) for k in needed]))
    return dict(label='LRU 控制流模拟；未复刻 flashlib 并行内核',rows=rows)
def hybrid():
    m=8;bp=20.;bh=80.;s=64*2**20
    rows=[]
    for q in range(m+1):
        # B denotes decimal GB/s; S is bytes. This ideal model omits fixed overhead.
        fill=q*s/(bp*10**9)*1000
        cpu=(m-q)*s/((bh-bp)*10**9)*1000
        rows.append(dict(q=q,cpu_experts=m-q,fill_ms=fill,cpu_ms=cpu,critical_ms=max(fill,cpu)))
    return dict(label='带宽模型：假设值，不是本机跑分；q=0 行为仅用于比较理想模型',m=m,expert_MiB=64,bp_GBs=bp,bh_GBs=bh,q_continuous=m*bp/bh,rows=rows,best_q=min(rows,key=lambda r:r['critical_ms'])['q'])
def prefill():
    load=2.;compute=3.;n=4;rows=[];end_copy=0.;end_compute=0.
    for layer in range(n):
        # Two buffers: layer l can reuse l-2's buffer after its compute completes.
        reusable=rows[layer-2]['compute_end'] if layer>=2 else 0.
        start=max(end_copy,reusable);end_copy=start+load
        cs=max(end_compute,end_copy);end_compute=cs+compute
        rows.append(dict(layer=layer,buffer=layer%2,copy_start=start,copy_end=end_copy,compute_start=cs,compute_end=end_compute))
    return dict(label='双缓冲理想时间线，毫秒为假设值，单拷贝流+单计算流',rows=rows,serial_ms=n*(load+compute),pipeline_ms=end_compute)
def kv():
    page=4;table=[7,2,9];rows=[]
    for position in range(10):rows.append(dict(position=position,logical_page=position//page,offset=position%page,physical_page=table[position//page],linear_slot=table[position//page]*page+position%page))
    return dict(label='普通全注意力分页教学；MLA/SWA/线性状态的布局需另读实现',page_size=page,page_table=table,rows=rows)
def anchor():
    a=[10,11,12,13,14,15,16,17,18,19];b=a[:7]+[90,91]
    common=0
    for x,y in zip(a,b):
        if x!=y:break
        common+=1
    checkpoints=[4,6,10];valid=[x for x in checkpoints if x<=common];resume=max(valid,default=0)
    return dict(label='边界 checkpoint 教学；数字为已处理 token 数，非真实 special-token id',old=a,new=b,common_prefix=common,checkpoints=checkpoints,resume=resume,recompute=len(b)-resume,kv_reusable=common)
def request():
    return dict(label='单请求教学轨迹，ids 自定义；非 FreeToken 实机 trace',rows=[
      dict(event='tokenize',known=3,computed=0,ids=[11,10,7],new_output=None),
      dict(event='prefill positions 0..2',known=4,computed=3,ids=[11,10,7,8],new_output=8),
      dict(event='decode position 3',known=5,computed=4,ids=[11,10,7,8,1],new_output=1),
      dict(event='EOS finish',known=5,computed=4,ids=[11,10,7,8,1],new_output=None)])
def budget():
    total=40.;dense=8.;runtime=3.;margin=2.;slot=.125;kv=7.;available=total-dense-runtime-margin-kv
    return dict(label='GiB 假设账本，不是 A100 空闲显存预测',total=total,dense=dense,runtime=runtime,margin=margin,kv=kv,expert_budget=available,slot=slot,slots=int(available/slot))
def check():
    a=moe();assert len(a['output'])==4 and abs(sum(a['weights'])-1)<1e-12
    # Partitioned sum equals the unpartitioned MoE sum.
    gpu=[a['weights'][0]*v for v in a['experts'][0]['y']];cpu=[a['weights'][1]*v for v in a['experts'][1]['y']]
    assert max(abs(x+y-z) for x,y,z in zip(gpu,cpu,a['output']))<1e-12
    assert cache()['rows'][2]['hits']==[(0,1)]
    assert hybrid()['best_q']==2 and prefill()['pipeline_ms']==14
    assert kv()['rows'][4]['linear_slot']==8
    assert anchor()['resume']==6 and anchor()['recompute']==3
    assert request()['rows'][-1]['computed']==4 and budget()['slots']==160
    return dict(passed=True,checks=8,engine_executed=False)
ALL={'moe':moe,'cache':cache,'hybrid':hybrid,'prefill':prefill,'kv':kv,'anchor':anchor,'request':request,'budget':budget}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('experiment',choices=[*ALL,'check','all']);p.add_argument('--out');args=p.parse_args()
    result=check() if args.experiment=='check' else {k:f() for k,f in ALL.items()} if args.experiment=='all' else ALL[args.experiment]()
    s=json.dumps(result,ensure_ascii=False,indent=2)
    if args.out:Path(args.out).write_text(s,encoding='utf-8')
    print(s)
