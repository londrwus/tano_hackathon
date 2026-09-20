# Maya's challenge: "Test me on an ASYMMETRY. I'll defend SPF at 60 and refuse a 34 cleanser.
# If it reproduces that, I believe you."
import asyncio, json, time, httpx
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
BY={p["product"]:p for p in SHELF}
RUNGS=list(range(10,112,2))
V={"name":"Maya Rao","language":"dry, funny, decisive",
   "creed":"People do not need more products. They need confidence.",
   "how_she_talks_about_money":"She will say a product is good and still refuse to tell people to pay its price.",
   "reputation":"Willing to say what is not worth buying."}

def payload(prod, hide_note):
    row={k:v for k,v in prod.items() if k not in ("gbp","ref","is_contradiction")}
    if hide_note: row.pop("maya_note",None)
    universe=[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"maya_rating":p["maya_rating"],
               "maya_note":p["maya_note"]} for p in SHELF if p["product"]!=prod["product"]]
    st={"creator":V,"her_shelf_for_price_context":universe,
        "price_context_note":"Maya's shelf runs GBP20-62. She routinely endorses GBP32-42 items. Judge by HER standards.",
        "product_under_review":row}
    qs={f"p{x}":{"type":"noul",
        "instructions":f"If `product_under_review` cost GBP {x}, would Maya tell her audience to buy it at that price? Compare against `her_shelf_for_price_context`.",
        "criteria":{"true":f"At GBP {x} she would still say buy it - fair by her standards",
                    "false":f"At GBP {x} she would say it is good but not worth that money"}} for x in RUNGS}
    return {"model":"jev-latest","state":st,"questions":qs}

def cross(cur):
    for i in range(1,len(RUNGS)):
        a,b=cur[RUNGS[i-1]],cur[RUNGS[i]]
        if a>=0.5>b:
            t=(a-0.5)/(a-b) if a!=b else 0
            return RUNGS[i-1]+t*(RUNGS[i]-RUNGS[i-1])
    return None if cur[RUNGS[0]]<0.5 else RUNGS[-1]

async def main():
    # the asymmetry pair: a CHEAP product she'd defend HIGH (SPF 50, GBP26, "Non-negotiable")
    # vs a CHEAP product she'd defend only modestly (Soft Clean, GBP22, "Boring in the best way")
    # vs the EXPENSIVE one she refuses (Glass Drop, GBP62)
    jobs=[]
    for name in ["SPF 50","Soft Clean","Clear Wash","Glass Drop","Cloud Cream"]:
        jobs.append((name+"  [with note]", payload(BY[name],False)))
        jobs.append((name+"  [NOTE HELD OUT]", payload(BY[name],True)))
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=30)) as c:
        t0=time.time()
        rs=await asyncio.gather(*[c.post(URL,headers=H,json=j[1],timeout=120) for j in jobs])
        wall=time.time()-t0
    res={}
    for (n,_),r in zip(jobs,rs):
        j=r.json(); res[n]={x:j["answers"][f"p{x}"]["noul"] for x in RUNGS}
    print(f"{len(jobs)*len(RUNGS)} judgments in {wall:.2f}s\n")
    print(f"{'PRODUCT':34s} {'STICKER':>7} {'LINE':>7} {'DELTA':>7}")
    lines={}
    for n in res:
        base=n.split("  [")[0]; st=BY[base]["gbp"]; x=cross(res[n]); lines[n]=x
        s=f"{x:7.1f}" if x else "   none"
        d=f"{x-st:+7.1f}" if x else "      -"
        print(f"{n:34s} {st:7} {s} {d}")
    print("\n" + "="*64)
    print("MAYA'S ASYMMETRY TEST")
    print("="*64)
    spf=lines["SPF 50  [with note]"]; soft=lines["Soft Clean  [with note]"]
    print(f"  Her SPF 50 costs GBP26 and she defends it to      GBP{spf:.0f}")
    print(f"  Her Soft Clean costs GBP22 and she defends it to  GBP{soft:.0f}")
    print(f"  -> Two cheap products, {abs(spf-soft):.0f} pounds apart. Not a price prior.")
    print(f"\n  Would she buy a GBP34 cleanser?  P = {res['Soft Clean  [with note]'][34]:.2f}  -> {'NO' if res['Soft Clean  [with note]'][34]<0.5 else 'yes'}")
    print(f"  Would she buy a GBP60 SPF?       P = {res['SPF 50  [with note]'][60]:.2f}  -> {'YES' if res['SPF 50  [with note]'][60]>=0.5 else 'no'}")
    print("\n  HELD-OUT (does her note carry the signal, in BOTH directions?)")
    for base in ["SPF 50","Soft Clean","Glass Drop"]:
        a=lines[base+"  [with note]"]; b=lines[base+"  [NOTE HELD OUT]"]
        note=BY[base]["maya_note"]
        if a and b: print(f"    {base:12s} with note GBP{a:5.1f}  ->  without GBP{b:5.1f}   shift {b-a:+6.1f}   ({note})")
asyncio.run(main())
