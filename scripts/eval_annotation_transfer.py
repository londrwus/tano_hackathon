import os
import json, asyncio, httpx, statistics, itertools
JEV=os.environ["JEV_API_KEY"]
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
P=json.load(open(r"C:\Users\Lenovo\Documents\tano_hackathon\data\case-001-maya.json"))
SHELF=P["shelf"]
GT={p["product"]:p["maya_rating"] for p in SHELF}
# the two she has real reservations about - the product's whole value is catching these
REFUSALS={"Glass Drop","Oil Balm"}

def bare(p): return {k:v for k,v in p.items() if k not in ("maya_rating","maya_note","ref","is_contradiction")}
def annotated(p): return {"product":p["product"],"gbp":p["gbp"],"type":p["type"],"maya_rating":p["maya_rating"],"maya_note":p["maya_note"]}

async def trial(c, k, seed_names):
    """seed_names = products she HAS annotated. Judge the REST from her standard."""
    seeds=[annotated(p) for p in SHELF if p["product"] in seed_names]
    targets=[p for p in SHELF if p["product"] not in seed_names]
    st={"creator":{"name":"Maya Rao","niche":"beauty/skincare"},
        "products_she_has_already_judged":seeds,
        "note":"Infer her standard from `products_she_has_already_judged` and apply it. She refuses to endorse things that are not worth their price."}
    qs={}
    for p in targets:
        key=p["product"].lower().replace(" ","_")
        qs[key]={"type":"score","instructions":{"question":"How enthusiastically would she recommend `product`?","product":bare(p)},
          "criteria":["She would warn people off it","Nothing to say","Only if asked","Recommend to the right person","She would champion it"]}
    r=await c.post(URL,headers=H,json={"model":"jev-latest","state":st,"questions":qs},timeout=90)
    a=r.json()["answers"]
    out={p["product"]:a[p["product"].lower().replace(" ","_")]["score"] for p in targets}
    # did it correctly rank the held-out refusals at the bottom?
    held_ref=[n for n in out if n in REFUSALS]
    rank=sorted(out,key=lambda n:out[n])   # ascending = worst first
    hits=sum(1 for n in held_ref if rank.index(n) < max(2,len(rank)//3))
    # spearman-ish corr vs her real ratings
    ks=[out[n] for n in out]; gs=[GT[n] for n in out]
    m1,m2=statistics.mean(ks),statistics.mean(gs)
    num=sum((x-m1)*(y-m2) for x,y in zip(ks,gs)); den=(sum((x-m1)**2 for x in ks)*sum((y-m2)**2 for y in gs))**.5
    return (num/den if den else 0), hits, len(held_ref), out

async def main():
    names=[p["product"] for p in SHELF]
    # seed sets of increasing size; always include at least one refusal in bigger sets to test transfer
    SETS={
      1:[["SPF 50"],["Glass Drop"]],
      2:[["SPF 50","Glass Drop"],["Cloud Cream","Oil Balm"]],
      3:[["SPF 50","Glass Drop","Soft Clean"],["Cloud Cream","Oil Balm","Red Reset"]],
      5:[["SPF 50","Glass Drop","Soft Clean","Red Reset","Daily Gel"]],
    }
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=20)) as c:
        print(f"{'SEEDS':>5}  {'corr vs her ratings':>20}  {'held-out refusals ranked low':>30}")
        for k,sets in SETS.items():
            rs=await asyncio.gather(*[trial(c,k,s) for s in sets])
            cs=[r[0] for r in rs]; hit=sum(r[1] for r in rs); tot=sum(r[2] for r in rs)
            print(f"{k:5d}  {statistics.mean(cs):+20.3f}  {hit}/{tot if tot else 0:<28}")
        # detail for k=2 with one refusal seeded
        corr,h,t,out=await trial(c,2,["SPF 50","Glass Drop"])
        print("\nDETAIL - she annotated only SPF 50 ('Non-negotiable') and Glass Drop ('Good. Not GBP62 good.'):")
        for n,v in sorted(out.items(),key=lambda x:-x[1]):
            print(f"   {v:.2f}  {n:13s}  (her real rating {GT[n]})")
asyncio.run(main())
