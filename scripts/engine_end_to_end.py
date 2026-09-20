# END TO END: one DM in -> a finished, shareable verdict out. This is the demo's headline number.
import os, asyncio, json, time, httpx, itertools
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
P=json.load(open(os.path.join(r"C:/Users/Lenovo/Documents/tano_hackathon","data","case-001-maya.json"),encoding="utf-8"))
BY={p["product"]:p for p in SHELF}
MAYA={"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
 "her_shelf":[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"skin":p["skin"],
               "maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF],
 "her_written_routing_rules":[{"condition":"DRY","she_reaches_for":["Cloud Cream","Oil Balm"]},
   {"condition":"OILY","she_reaches_for":["Daily Gel","Clear Wash"]},{"condition":"SENSITIVE","rule":"avoid fragrance"},
   {"condition":"REDNESS","she_reaches_for":["Red Reset"]}],
 "her_intake_questions":P["decision_rules"]["intake_questions"],
 "how_she_decides":["Apply `her_written_routing_rules` FIRST.","Fewer steps beats more steps.",
   "She does NOT spend the whole budget just because it is there.","Half her advice is subtraction.",
   "She refuses on price even when she rates something highly."]}
BUD={"under_30":30,"30_to_60":60,"60_to_100":100,"over_100":150,"not_stated":80}
ITM={"one":1,"two":2,"three_or_four":4,"not_stated":3}

def triage_q():
    return {
     "job":{"type":"choice","instructions":"What is `message` asking Maya to do?",
       "criteria":{"pick_for_me":"Choose products under constraints","is_it_worth_it":"Judge a product against its price",
        "do_i_need_it":"They own something; decide if they need more","what_is_it":"Identify an item she used",
        "diagnose_me":"They do not know their skin type","occasion":"Event soon","not_a_question":"Trust or praise",
        "later":"Already decided, waiting on money or time"}},
     "out_of_scope":{"type":"noul","instructions":"Is `message` asking for medical advice, prescription interactions, pregnancy safety, a skin condition needing a doctor, or advice for a child?",
       "criteria":{"true":"Maya must not answer","false":"Within a beauty creator's scope"}},
     "skin":{"type":"choice","instructions":"What skin type does `message` state or imply?",
       "criteria":{"dry":None,"oily":None,"combination":None,"sensitive":None,"redness":None,"not_stated":None}},
     "budget":{"type":"choice","instructions":"What budget does `message` state or imply?",
       "criteria":{k:None for k in BUD}},
     "max_items":{"type":"choice","instructions":"How many products would this person tolerate?",
       "criteria":{k:None for k in ITM}},
     "which_owned":{"type":"choice","instructions":"Which product from `creator.her_shelf` does `message` say they already own?",
       "criteria":{**{p["product"]:None for p in SHELF},"none":None}},
    }

def feasible(b,owns,mx):
    pool=[p["product"] for p in SHELF if p["product"] not in owns]
    return [c for k in range(1,mx+1) for c in itertools.combinations(pool,k) if sum(BY[x]["gbp"] for x in c)<=b]

async def answer(c, text):
    t0=time.time(); calls=0; judg=0
    r=await c.post(URL,headers=H,json={"model":"jev-latest","state":{"creator":MAYA,"message":text},"questions":triage_q()},timeout=60)
    calls+=1; a=r.json()["answers"]; judg+=len(a); t_tri=time.time()-t0
    if a["out_of_scope"]["noul"]>0.5:
        return dict(t=time.time()-t0,calls=calls,judg=judg,verdict="REFERRED ON - outside her scope",basket=None,t_tri=t_tri)
    owns=[a["which_owned"]["choice"]] if a["which_owned"]["choice"]!="none" else []
    combos=feasible(BUD[a["budget"]["choice"]], owns, ITM[a["max_items"]["choice"]])
    shopper={"says":text,"skin":a["skin"]["choice"],"budget_gbp":BUD[a["budget"]["choice"]],"owns":owns}
    CH=70; chs=[combos[i:i+CH] for i in range(0,len(combos),CH)]
    def pl(ch):
        return {"model":"jev-latest","state":{"judge":MAYA,"shopper":shopper,
          "baskets":{f"b{i}":{"items":[{"product":x,"gbp":BY[x]["gbp"],"type":BY[x]["type"],"skin":BY[x]["skin"]} for x in cb],
                              "total_gbp":sum(BY[x]["gbp"] for x in cb)} for i,cb in enumerate(ch)}},
          "questions":{f"b{i}":{"type":"score","instructions":f"Would Maya send `baskets.b{i}` to `shopper`? Judge the SET.",
            "criteria":["Wrong for this person","Defensible but not her pick","Reasonable","Good","Exactly what she would send"]} for i in range(len(ch))}}
    rs=await asyncio.gather(*[c.post(URL,headers=H,json=pl(ch),timeout=120) for ch in chs])
    calls+=len(chs)
    sc={}
    for ch,rr in zip(chs,rs):
        aa=rr.json()["answers"]; judg+=len(aa)
        for i,cb in enumerate(ch): sc[cb]=aa[f"b{i}"]["score"]
    top=sorted(sc,key=lambda k:-sc[k])[0]
    return dict(t=time.time()-t0,calls=calls,judg=judg,verdict=" + ".join(top),
                gbp=sum(BY[x]["gbp"] for x in top),basket=top,t_tri=t_tri,n=len(combos))

TESTS=["i have dry skin + redness and £60. tell me what to buy pls",
       "can you make me a routine but only 2 products bc i will not do 8 steps",
       "i already have the night serum. do i need the barrier cream too???",
       "im pregnant, is any of this safe"]
async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=40)) as c:
        await c.post(URL,headers=H,json={"model":"jev-latest","state":"warm","questions":{"w":{"type":"noul","instructions":"warm?"}}},timeout=30)
        print(f"{'DM':58s} {'TOTAL':>7} {'triage':>7} {'calls':>6} {'judgments':>10}  ANSWER")
        for t in TESTS:
            r=await answer(c,t)
            b=f"{r['verdict']}" + (f"  GBP{r['gbp']}" if r.get('gbp') else "")
            print(f"{t[:57]:58s} {r['t']:6.2f}s {r['t_tri']:6.2f}s {r['calls']:6d} {r['judg']:10d}  {b}")
asyncio.run(main())
