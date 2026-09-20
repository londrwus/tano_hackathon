# THE FIX: for products we have no price for, ask what Maya's CEILING is.
# No price input required. The shopper is already looking at the price.
import asyncio, json, time, httpx, statistics, random
random.seed(9)
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
W=json.load(open("obf_with_ingredients.json",encoding="utf-8"))
BAD=("body","hand","foot","hair","shampoo","deodorant","baby","shaving")
W=[p for p in W if not any(b in (p.get("product_name","")+" "+" ".join(p.get("categories_tags_en",[]))).lower() for b in BAD)]
S=random.sample(W,10)
RUNGS=list(range(8,92,4))   # 21 rungs
UNI=[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF]

def payload(p):
    st={"creator":{"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
        "how_she_talks_about_money":"She will say a product is good and still refuse to tell people to pay its price."},
        "her_shelf_for_price_context":UNI,
        "price_context_note":"Maya's own shelf runs GBP20-62. Judge by HER standards.",
        "product_under_review":{"name":p["product_name"],"brand":p["brands"],
                                "size":p.get("quantity",""),"ingredients":(p.get("_ing") or "")[:900]}}
    return {"model":"jev-latest","state":st,"questions":{f"p{x}":{"type":"noul",
      "instructions":f"If `product_under_review` cost GBP {x}, would Maya tell her audience to buy it at that price?",
      "criteria":{"true":f"At GBP {x} it is fair for what it does, by her standards",
                  "false":f"At GBP {x} she would say it is not worth that money"}} for x in RUNGS}}

def cross(cur):
    for i in range(1,len(RUNGS)):
        a,b=cur[RUNGS[i-1]],cur[RUNGS[i]]
        if a>=0.5>b: return RUNGS[i-1]+((a-0.5)/(a-b) if a!=b else 0)*(RUNGS[i]-RUNGS[i-1])
    return RUNGS[-1] if cur[RUNGS[0]]>=0.5 else None

async def main():
    REP=3
    jobs=[(p,payload(p)) for p in S for _ in range(REP)]
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=40)) as c:
        t0=time.time(); rs=await asyncio.gather(*[c.post(URL,headers=H,json=j[1],timeout=120) for j in jobs]); w=time.time()-t0
    from collections import defaultdict
    out=defaultdict(list)
    for (p,_),r in zip(jobs,rs):
        j=r.json(); cur={x:j["answers"][f"p{x}"]["noul"] for x in RUNGS}
        v=cross(cur)
        if v: out[p["code"]].append(v)
    print(f"{len(jobs)} sweeps x {len(RUNGS)} rungs = {len(jobs)*len(RUNGS)} judgments in {w:.2f}s")
    print(f"NO PRICE DATA WAS SUPPLIED. The ceiling is derived purely from Maya's standard.\n")
    print(f"{'BRAND':16s} {'PRODUCT':30s} {'MAYA WOULD PAY UP TO':>21} {'SD':>5}  BAND")
    for p in S:
        v=out.get(p["code"],[])
        if not v: print(f"{p['brands'][:15]:16s} {p['product_name'][:29]:30s} {'no ceiling found':>21}"); continue
        m=statistics.mean(v); sd=statistics.pstdev(v)
        lo=5*round(max(0,m-2*sd-2)/5); hi=5*round((m+2*sd+2)/5)
        print(f"{p['brands'][:15]:16s} {p['product_name'][:29]:30s} {'GBP'+format(m,'.0f'):>21} {sd:5.1f}  GBP{lo}-{hi}")
asyncio.run(main())
