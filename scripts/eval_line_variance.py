import asyncio, httpx, statistics, json
from prelude import JEV, SHELF
exec(open('asymmetry.py').read().split('async def main')[0].split('import asyncio')[1].replace('import json, time, httpx','',1) if False else '')
import time
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
BY={p["product"]:p for p in SHELF}; RUNGS=list(range(10,112,2))
V={"name":"Maya Rao","language":"dry, funny, decisive","creed":"People do not need more products. They need confidence.",
   "how_she_talks_about_money":"She will say a product is good and still refuse to tell people to pay its price.",
   "reputation":"Willing to say what is not worth buying."}
def payload(prod):
    row={k:v for k,v in prod.items() if k not in ("gbp","ref","is_contradiction")}
    uni=[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF if p["product"]!=prod["product"]]
    st={"creator":V,"her_shelf_for_price_context":uni,
        "price_context_note":"Maya's shelf runs GBP20-62. She routinely endorses GBP32-42 items. Judge by HER standards.",
        "product_under_review":row}
    return {"model":"jev-latest","state":st,"questions":{f"p{x}":{"type":"noul",
      "instructions":f"If `product_under_review` cost GBP {x}, would Maya tell her audience to buy it at that price? Compare against `her_shelf_for_price_context`.",
      "criteria":{"true":f"At GBP {x} she would still say buy it - fair by her standards",
                  "false":f"At GBP {x} she would say it is good but not worth that money"}} for x in RUNGS}}
def cross(cur):
    for i in range(1,len(RUNGS)):
        a,b=cur[RUNGS[i-1]],cur[RUNGS[i]]
        if a>=0.5>b: return RUNGS[i-1]+((a-0.5)/(a-b) if a!=b else 0)*(RUNGS[i]-RUNGS[i-1])
    return None
async def main():
    N=7
    prods=["SPF 50","Glass Drop","Soft Clean","Cloud Cream"]
    jobs=[(p,payload(BY[p])) for p in prods for _ in range(N)]
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=40)) as c:
        t0=time.time(); rs=await asyncio.gather(*[c.post(URL,headers=H,json=j[1],timeout=120) for j in jobs]); w=time.time()-t0
    from collections import defaultdict
    out=defaultdict(list)
    for (n,_),r in zip(jobs,rs):
        j=r.json(); cur={x:j["answers"][f"p{x}"]["noul"] for x in RUNGS}
        v=cross(cur)
        if v: out[n].append(v)
    print(f"{len(jobs)} runs x {len(RUNGS)} rungs = {len(jobs)*len(RUNGS)} judgments in {w:.1f}s\n")
    print(f"{'PRODUCT':13s} {'STICKER':>7} {'MEAN LINE':>10} {'SD':>6} {'MIN':>6} {'MAX':>6} {'RANGE':>6}   SUGGESTED BAND")
    for p in prods:
        v=out[p]
        if len(v)<2: print(f"{p:13s} insufficient"); continue
        m=statistics.mean(v); sd=statistics.pstdev(v)
        lo,hi=min(v),max(v)
        b=5*round((m-1.5*sd)/5), 5*round((m+1.5*sd)/5)
        print(f"{p:13s} {BY[p]['gbp']:7} {m:10.1f} {sd:6.2f} {lo:6.1f} {hi:6.1f} {hi-lo:6.1f}   GBP{b[0]}-{b[1]}")
asyncio.run(main())
