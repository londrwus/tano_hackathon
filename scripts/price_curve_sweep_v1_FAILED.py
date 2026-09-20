import os
import asyncio, json, time, httpx
KEY=os.environ["JEV_API_KEY"]
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"}
P=json.load(open(r"C:\Users\Lenovo\Documents\tano_hackathon\data\case-001-maya.json"))
SHELF=P["shelf"]
BY={p["product"]:p for p in SHELF}
RUNGS=list(range(10,112,2))   # 51 rungs, GBP10..GBP110

VOICE={"name":"Maya Rao","language":"dry, funny, decisive",
 "creed":"People do not need more products. They need confidence.",
 "how_she_talks_about_money":"She will say a product is good and still refuse to tell people to pay its price. She is not anti-spending; she is anti-overpaying.",
 "reputation":"Her audience follows her because she is specific, honest and willing to say what is not worth buying."}

# calibration anchors: an emphatic yes at GBP26, and a modest rating she still endorses at GBP24
def anchors(exclude):
    out=[]
    for n in ["SPF 50","Daily Gel"]:
        if n!=exclude:
            p=BY[n]; out.append({"product":p["product"],"gbp":p["gbp"],"type":p["type"],
                                 "maya_rating":p["maya_rating"],"maya_note":p["maya_note"]})
    return out

def payload(prod, hide_note=False):
    row={k:v for k,v in prod.items() if k not in ("gbp","ref","is_contradiction")}
    if hide_note: row.pop("maya_note",None)
    st={"creator":VOICE,"product":row,"calibration_examples":anchors(prod["product"])}
    qs={}
    for x in RUNGS:
        qs[f"p{x}"]={"type":"noul",
          "instructions":f"Would Maya tell her audience that `product` is worth GBP {x} of their money?",
          "criteria":{"true":"She would say buy it, that is a fair price for what it does",
                      "false":"She would say it is good, but not worth that - the price is doing work the product does not"}}
    return {"model":"jev-latest","state":st,"questions":qs}

def crossing(curve):
    """first price where P drops below 0.5, interpolated"""
    for i in range(1,len(RUNGS)):
        a,b=curve[RUNGS[i-1]],curve[RUNGS[i]]
        if a>=0.5>b:
            t=(a-0.5)/(a-b) if a!=b else 0
            return RUNGS[i-1]+t*(RUNGS[i]-RUNGS[i-1])
    return None if curve[RUNGS[0]]<0.5 else RUNGS[-1]

async def main():
    jobs=[(p["product"],payload(p),False) for p in SHELF]
    jobs.append(("Glass Drop [HELD OUT]",payload(BY["Glass Drop"],hide_note=True),True))
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=60)) as c:
        t0=time.time()
        rs=await asyncio.gather(*[c.post(URL,headers=H,json=j[1],timeout=120) for j in jobs])
        wall=time.time()-t0
    tin=tout=0; res={}
    for (name,_,ho),r in zip(jobs,rs):
        j=r.json(); tin+=j["usage"]["input_tokens"]; tout+=j["usage"]["output_tokens"]
        res[name]={x:j["answers"][f"p{x}"]["noul"] for x in RUNGS}
    n=len(jobs)*len(RUNGS)
    print(f"{len(jobs)} products x {len(RUNGS)} price rungs = {n} judgments in {wall:.2f}s")
    print(f"tokens in={tin:,} out={tout:,}   (~${tin/1e6*0.042:.4f} at $0.042/MTok)\n")
    print(f"{'PRODUCT':22s} {'STICKER':>7} {'MAYA LINE':>9} {'HEADROOM':>9}   curve @ 20/30/40/50/62/80")
    for name in res:
        cur=res[name]; x=crossing(cur)
        base=BY["Glass Drop"] if "Glass Drop" in name else BY[name]
        st=base["gbp"]
        hr=(x-st) if x else None
        s=f"{x:9.1f}" if x else "     none"
        h=f"{hr:+9.1f}" if hr is not None else "        -"
        pts="  ".join(f"{cur[k]:.2f}" for k in [20,30,40,50,62,80])
        print(f"{name:22s} {st:7} {s} {h}   {pts}")
    json.dump({k:{str(a):b for a,b in v.items()} for k,v in res.items()},open("fence_out.json","w"),indent=1)
asyncio.run(main())
