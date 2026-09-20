# ONE speculative fan-out per DM. Code routes on the answers. This is the Jev signature pattern.
import os, asyncio, json, time, httpx
from prelude import JEV, SHELF, VOICE
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
P=json.load(open(os.path.join(r"C:/Users/Lenovo/Documents/tano_hackathon","data","case-001-maya.json"),encoding="utf-8"))
DMS=P["inbox"]
BY={p["product"]:p for p in SHELF}

MAYA={"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
      "her_shelf":[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"skin":p["skin"],"finish":p["finish"],
                    "maya_rating":p["maya_rating"],"maya_note":p["maya_note"]} for p in SHELF],
      "her_intake_questions":P["decision_rules"]["intake_questions"],
      "her_routing":P["decision_rules"]["routing"]}

def triage(dm):
    """ONE request. Every question asked speculatively. Code consumes what applies."""
    st={"creator":MAYA,"message":dm["text"]}
    qs={
     "job":{"type":"choice","instructions":"What is `message` actually asking Maya to do?",
       "criteria":{
        "pick_for_me":"Choose specific products for them, possibly under constraints",
        "is_it_worth_it":"Judge whether a specific product justifies its price",
        "do_i_need_it":"They already own something; decide if they need another thing",
        "what_is_it":"Identify a specific item she used or wore",
        "diagnose_me":"They do not know their own skin type or problem",
        "occasion":"They need to look good for a specific event soon",
        "not_a_question":"An expression of trust, praise or feeling, with nothing to decide and no purchase pending",
        "later":"They have ALREADY decided to buy and are only waiting for money or time - e.g. payday, next month, when it restocks"}},
     "needs_more_info":{"type":"noul","instructions":"Would Maya have to ask a question back before she could answer `message` responsibly?",
       "criteria":{"true":"She would ask something first","false":"She can answer now"}},
     "which_question_back":{"type":"choice","instructions":"If Maya asked ONE question back, which of `creator.her_intake_questions` would it be?",
       "criteria":{q:None for q in P["decision_rules"]["intake_questions"]}},
     "skin":{"type":"choice","instructions":"What skin type does `message` state or imply?",
       "criteria":{"dry":None,"oily":None,"combination":None,"sensitive":None,"redness":None,"not_stated":"No signal"}},
     "budget":{"type":"choice","instructions":"What budget does `message` state or imply?",
       "criteria":{"under_30":None,"30_to_60":None,"60_to_100":None,"over_100":None,"not_stated":"No budget signal"}},
     "max_items":{"type":"choice","instructions":"How many products would this person tolerate being told to buy?",
       "criteria":{"one":"They want a single answer","two":"Explicitly a minimal routine","three_or_four":"Open to a small set","not_stated":"No signal"}},
     "already_owns":{"type":"noul","instructions":"Does `message` say they already own one of `creator.her_shelf`?",
       "criteria":{"true":"They name something they have","false":"No"}},
     "which_owned":{"type":"choice","instructions":"Which product from `creator.her_shelf` does `message` say they already own?",
       "criteria":{**{p["product"]:None for p in SHELF},"none":"They do not name one"}},
     "named_product":{"type":"choice","instructions":"Which product from `creator.her_shelf` is `message` asking about specifically?",
       "criteria":{**{p["product"]:None for p in SHELF},"none":"No specific product named"}},
     "wants_verdict_not_facts":{"type":"noul","instructions":"Do they want Maya's judgement rather than product information?",
       "criteria":{"true":"They want her to decide","false":"They want a fact"}},
     "urgency_days":{"type":"score","instructions":"How soon does this person need to act?",
       "criteria":["Within 24 hours","This week","Whenever, no deadline","They have already decided and are waiting"]},
    }
    return {"model":"jev-latest","state":st,"questions":qs}

BUDGET={"under_30":30,"30_to_60":60,"60_to_100":100,"over_100":150,"not_stated":80}
ITEMS={"one":1,"two":2,"three_or_four":4,"not_stated":3}

def resolve(dm,a):
    job=a["job"]["choice"]; conf=a["job"]["confidence"]
    owns=a["which_owned"]["choice"] if a["already_owns"]["noul"]>0.5 and a["which_owned"]["choice"]!="none" else None
    named=a["named_product"]["choice"] if a["named_product"]["choice"]!="none" else None
    skin=a["skin"]["choice"]; bud=BUDGET[a["budget"]["choice"]]; mx=ITEMS[a["max_items"]["choice"]]
    ask=a["needs_more_info"]["noul"]>0.55
    qback=a["which_question_back"]["choice"]
    plan={"pick_for_me":"BASKET","do_i_need_it":"BASKET(minus owned)","occasion":"BASKET(occasion)",
          "diagnose_me":"ASK BACK then BASKET","is_it_worth_it":"PRICE CEILING","what_is_it":"ASK BACK (her rule)",
          "later":"PRICE CEILING + watch","not_a_question":"ACKNOWLEDGE, no sell"}[job]
    return job,conf,plan,owns,named,skin,bud,mx,ask,qback

async def main():
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=20)) as c:
        t0=time.time()
        rs=await asyncio.gather(*[c.post(URL,headers=H,json=triage(d),timeout=90) for d in DMS])
        w=time.time()-t0
    tin=sum(r.json()["usage"]["input_tokens"] for r in rs)
    nq=sum(len(r.json()["answers"]) for r in rs)
    print(f"ALL {len(DMS)} REAL DMs from E-01, one request each, {nq} judgments in {w:.2f}s ({tin:,} in tokens)\n")
    print(f"{'REF':8s} {'THEIR MESSAGE':44s} {'JOB':16s} {'CONF':>5}  ROUTE")
    for d,r in zip(DMS,rs):
        a=r.json()["answers"]
        job,conf,plan,owns,named,skin,bud,mx,ask,qback=resolve(d,a)
        extra=[]
        if owns: extra.append(f"owns:{owns}")
        if named: extra.append(f"re:{named}")
        if skin!="not_stated": extra.append(f"skin:{skin}")
        if a["budget"]["choice"]!="not_stated": extra.append(f"GBP{bud}")
        if mx<3: extra.append(f"max{mx}")
        print(f"{d['ref']:8s} {d['text'][:43]:44s} {job:16s} {conf:5.2f}  {plan}")
        if extra: print(f"{'':8s} {'':44s} {'':16s} {'':5s}  -> {', '.join(extra)}")
        if ask: print(f"{'':8s} {'':44s} {'':16s} {'':5s}  -> ASKS BACK: \"{qback}\"")
    # coverage
    jobs=[resolve(d,r.json()["answers"])[0] for d,r in zip(DMS,rs)]
    print(f"\nCOVERAGE: {len(DMS)}/{len(DMS)} DMs routed. Distinct jobs used: {len(set(jobs))}")
asyncio.run(main())
