"""Record an actual local FreeToken SSE request. Standard library, no fabricated timings."""
import argparse,json,time,urllib.request,urllib.error,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base-url',default='http://127.0.0.1:1919');p.add_argument('--prompt',default='请用两句话解释什么是混合专家模型。');p.add_argument('--max-tokens',type=int,default=128);p.add_argument('--out',default='probe.json');p.add_argument('--timeout',type=float,default=600);args=p.parse_args()
    base=args.base_url.rstrip('/')
    with urllib.request.urlopen(base+'/v1/models',timeout=20) as res:models=json.load(res)
    if not models.get('data'):raise RuntimeError('/v1/models returned no model')
    model=models['data'][0]['id']
    payload=dict(model=model,messages=[dict(role='user',content=args.prompt)],temperature=0,max_tokens=args.max_tokens,stream=True,stream_options=dict(include_usage=True))
    req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Accept':'text/event-stream'})
    start=time.perf_counter();events=[];first=None;usage=None;error=None;text='';reasoning='';done=False;finish=None
    result=dict(client='stdlib SSE line reader; application timing, not GPU timing',request=payload,base_url=base)
    try:
        with urllib.request.urlopen(req,timeout=args.timeout) as response:
            headers_ms=(time.perf_counter()-start)*1000
            for raw in response:
                line=raw.decode('utf-8').strip()
                if not line.startswith('data:'):continue
                value=line[5:].strip();t=(time.perf_counter()-start)*1000
                if value=='[DONE]':done=True;break
                event=json.loads(value);events.append(dict(arrival_ms=t,data=event))
                if event.get('error'):error=event['error'];break
                if event.get('usage') is not None:usage=event['usage']
                for choice in event.get('choices',[]):
                    delta=choice.get('delta',{});content=delta.get('content') or '';reason=delta.get('reasoning_content') or ''
                    if first is None and (content or reason):first=t
                    text+=content;reasoning+=reason
                    if choice.get('finish_reason') is not None:finish=choice['finish_reason']
            result.update(headers_ms=headers_ms)
    except Exception as exc:
        error=dict(type=type(exc).__name__,message=str(exc))
        if isinstance(exc,urllib.error.HTTPError):error['body']=exc.read().decode('utf-8',errors='replace')
    result.update(first_visible_content_or_reasoning_ms=first,total_ms=(time.perf_counter()-start)*1000,usage=usage,finish_reason=finish,done_received=done,error=error,text=text,reasoning=reasoning,events=events)
    Path(args.out).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('events','reasoning')},ensure_ascii=False,indent=2))
    if error or not done:raise SystemExit(1)
if __name__=='__main__':main()
