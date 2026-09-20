import os
import asyncio, json, time, httpx
KEY=os.environ["JEV_API_KEY"]
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"}
PACK=json.load(open(r"C:\Users\Lenovo\Documents\tano_hackathon\data\case-001-maya.json"))
SHELF=PACK["shelf"]; RULES=PACK["decision_rules"]; VOICE=PACK["voice"]

CREATOR={"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"],
         "routing_rules":RULES["routing"],"hard_rule":RULES["hard_rule"],
         "note":"She will say a product is not worth its price even when she rates it highly."}

# Ground truth derived ONLY from E-02.2 routing + E-04 shelf + E-08 discounted leads.
CASES=[
 {"id":"gracelee","brief":"dry skin + redness, budget 60 GBP, wants to be told what to buy","expect_in":["Cloud Cream","Red Reset"],"expect_out":["Glass Drop","Clear Wash","Daily Gel"],"src":"E-01.2"},
 {"id":"oily_gym","brief":"oily skin, goes to the gym daily, hates heavy creams, budget 50 GBP","expect_in":["Daily Gel","Clear Wash"],"expect_out":["Cloud Cream","Oil Balm"],"src":"E-02.2 OILY"},
 {"id":"priya_sensitive","brief":"very sensitive skin, reacts to everything, angry red skin right now","expect_in":["Red Reset"],"expect_out":["Night Serum","Glass Drop"],"src":"E-02.2 SENSITIVE/REDNESS"},
 {"id":"joanna_2step","brief":"will not do more than 2 products, no patience, normal skin","expect_in":["SPF 50"],"expect_out":["Oil Balm","Glass Drop"],"src":"E-01.9"},
 {"id":"emily_budget","brief":"22, trusts Maya but will not spend 100 GBP on serum, budget 30 GBP","expect_in":["Clear Wash","Soft Clean","SPF 50","Daily Gel"],"expect_out":["Glass Drop","Night Serum"],"src":"persona emily"},
 {"id":"kate_date","brief":"first date Friday, wants to look good tomorrow, does not care about skincare routines","expect_in":["Tint Veil"],"expect_out":["Night Serum"],"src":"E-01.8 + E-02.1"},
]

def payload(case):
    st={"creator":CREATOR,"shelf":SHELF,"shopper":case["brief"]}
    qs={}
    for p in SHELF:
        k=p["product"].lower().replace(" ","_")
        qs[k]={"type":"noul",
               "instructions":{"question":"Would Maya recommend this specific product to `shopper`? Apply `creator.routing_rules` and her willingness to reject a product on price.","product":p},
               "criteria":{"true":"Maya would put this in their basket","false":"Maya would leave it out for this person"}}
    return {"model":"jev-latest","state":st,"questions":qs}

async def main():
    async with httpx.AsyncClient() as c:
        t0=time.time()
        rs=await asyncio.gather(*[c.post(URL,headers=H,json=payload(x),timeout=90) for x in CASES])
        wall=time.time()-t0
        hits=miss=fp=0
        print(f"{len(CASES)} shoppers x {len(SHELF)} products = {len(CASES)*len(SHELF)} judgments in {wall:.2f}s\n")
        for case,r in zip(CASES,rs):
            a=r.json()["answers"]
            ranked=sorted(((p["product"],a[p["product"].lower().replace(' ','_')]["noul"]) for p in SHELF),key=lambda x:-x[1])
            picked=[n for n,v in ranked if v>=0.5]
            ok_in=[e for e in case["expect_in"] if e in picked]
            bad=[e for e in case["expect_out"] if e in picked]
            hits+=len(ok_in); miss+=len(case["expect_in"])-len(ok_in); fp+=len(bad)
            flag="OK " if len(ok_in)==len(case["expect_in"]) and not bad else "!! "
            print(f"{flag}{case['id']:16s} ({case['src']})")
            print(f"    top5: "+", ".join(f"{n} {v:.2f}" for n,v in ranked[:5]))
            print(f"    expected-in hit {len(ok_in)}/{len(case['expect_in'])}   forbidden-recommended: {bad or 'none'}")
        tot=hits+miss
        print(f"\nRECALL on Maya's documented rules: {hits}/{tot} = {hits/tot:.0%}")
        print(f"VIOLATIONS (recommended something her rules exclude): {fp}")
asyncio.run(main())
