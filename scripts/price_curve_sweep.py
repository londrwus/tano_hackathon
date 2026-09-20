import asyncio, json, time, httpx
exec(open('fence.py').read().split('def payload')[0])
def crossing(curve):
    for i in range(1,len(RUNGS)):
        a,b=curve[RUNGS[i-1]],curve[RUNGS[i]]
        if a>=0.5>b:
            t=(a-0.5)/(a-b) if a!=b else 0
            return RUNGS[i-1]+t*(RUNGS[i]-RUNGS[i-1])
    return None if curve[RUNGS[0]]<0.5 else RUNGS[-1]

def payload(prod, hide_note=False):
    row={k:v for k,v in prod.items() if k not in ("gbp","ref","is_contradiction")}
    if hide_note: row.pop("maya_note",None)
    # FIX: give Jev Maya's ACTUAL price universe + her endorsed/refused anchors
    universe=[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"maya_rating":p["maya_rating"],
               "maya_note":p["maya_note"]} for p in SHELF if p["product"]!=prod["product"]]
    st={"creator":VOICE,
        "her_shelf_for_price_context":universe,
        "price_context_note":("This is the full range of what Maya actually recommends: GBP 20 to GBP 62. "
                              "She routinely endorses GBP 32-42 items. Judge the product against HER standards, "
                              "not against a generic idea of what skincare should cost."),
        "product_under_review":row}
    qs={}
    for x in RUNGS:
        qs[f"p{x}"]={"type":"noul",
          "instructions":(f"If `product_under_review` cost GBP {x}, would Maya tell her audience to buy it at that price? "
                          "Compare against `her_shelf_for_price_context`, where her own notes show which prices she defends."),
          "criteria":{"true":"At GBP %d she would still say buy it - the price is fair for what it does, by her standards"%x,
                      "false":"At GBP %d she would say it is good but not worth that money"%x}}
    return {"model":"jev-latest","state":st,"questions":qs}

async def main():
    jobs=[(p["product"],payload(p)) for p in SHELF]
    jobs.append(("Glass Drop [HELD OUT]",payload(BY["Glass Drop"],hide_note=True)))
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=60)) as c:
        t0=time.time(); rs=await asyncio.gather(*[c.post(URL,headers=H,json=j[1],timeout=120) for j in jobs]); wall=time.time()-t0
    res={}; tin=0
    for (name,_),r in zip(jobs,rs):
        j=r.json(); tin+=j["usage"]["input_tokens"]
        res[name]={x:j["answers"][f"p{x}"]["noul"] for x in RUNGS}
    print(f"{len(jobs)*len(RUNGS)} judgments in {wall:.2f}s, {tin:,} input tokens (~${tin/1e6*0.042:.4f})\n")
    print(f"{'PRODUCT':22s} {'STICKER':>7} {'MAYA LINE':>9} {'HEADROOM':>9}   @20  @30  @40  @50  @62  @80")
    errs=[]
    for name in res:
        cur=res[name]; x=crossing(cur)
        st_=BY["Glass Drop"]["gbp"] if "Glass Drop" in name else BY[name]["gbp"]
        s=f"{x:9.1f}" if x else "     none"; hr=(x-st_) if x else None
        h=f"{hr:+9.1f}" if hr is not None else "        -"
        pts="  ".join(f"{cur[k]:.2f}" for k in [20,30,40,50,62,80])
        print(f"{name:22s} {st_:7} {s} {h}   {pts}")
        if x and "HELD" not in name: errs.append(abs(hr))
    print(f"\nGlass Drop P(worth it) AT ITS REAL GBP62 STICKER:")
    print(f"   with her note   : {res['Glass Drop'][62]:.3f}")
    print(f"   note HELD OUT   : {res['Glass Drop [HELD OUT]'][62]:.3f}")
    json.dump({k:{str(a):b for a,b in v.items()} for k,v in res.items()},open("fence2_out.json","w"),indent=1)
asyncio.run(main())
