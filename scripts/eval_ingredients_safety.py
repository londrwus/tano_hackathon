import json, httpx, statistics, random
random.seed(5)
from prelude import JEV, SHELF, VOICE
W=json.load(open("obf_with_ingredients.json",encoding="utf-8"))
BAD=("body","hand","foot","hair","shampoo","deodorant","baby","shaving")
W=[p for p in W if not any(b in (p.get("product_name","")+" "+" ".join(p.get("categories_tags_en",[]))).lower() for b in BAD)]
S=random.sample(W,24)
URL="https://api.typesafe.ai/v1/systemone"; H={"Authorization":f"Bearer {JEV}"}
PRIYA={"who":"Priya, 31","skin":"very sensitive, reacts to new products, some redness",
       "says":"Every time I try something new my face freaks out."}

def ask(items, with_ing):
    st={"creator":{"name":"Maya Rao","voice":VOICE["style_rules"],"creed":VOICE["creed"]},
        "her_shelf":[{"product":x["product"],"gbp":x["gbp"],"maya_rating":x["maya_rating"],"maya_note":x["maya_note"]} for x in SHELF],
        "shopper":PRIYA,
        "candidates":{p["code"]:({"name":p["product_name"],"brand":p["brands"],
            **({"ingredients":p["_ing"][:1200]} if with_ing else {})}) for p in items}}
    qs={}
    for p in items:
        c=p["code"]
        qs[c+"|enough"]={"type":"noul","instructions":f"Is there enough information about `candidates.{c}` for Maya to give `shopper` an honest verdict?",
          "criteria":{"true":"Enough to judge responsibly","false":"She would need more before advising"}}
        qs[c+"|irritate"]={"type":"noul","instructions":f"Is `candidates.{c}` likely to irritate `shopper`'s sensitive, reactive skin?",
          "criteria":{"true":"Contains things that commonly trigger reactive skin","false":"Unlikely to cause a reaction"}}
        qs[c+"|fit"]={"type":"score","instructions":f"How enthusiastically would Maya recommend `candidates.{c}` to `shopper`?",
          "criteria":["Warn her off it","Nothing to say","Only if asked","Recommend to the right person","Champion it"]}
    return httpx.post(URL,headers=H,json={"model":"jev-latest","state":st,"questions":qs},timeout=120).json()

for label,flag in [("WITHOUT ingredients (photo/name only)",False),("WITH real ingredient lists",True)]:
    r=ask(S,flag); a=r["answers"]
    en=[a[p["code"]+"|enough"]["noul"] for p in S]
    ir=[a[p["code"]+"|irritate"]["noul"] for p in S]
    cf=[a[p["code"]+"|fit"]["confidence"] for p in S]
    print(f"\n{label}   ({r['usage']['input_tokens']:,} in)")
    print(f"   'enough info'    median {statistics.median(en):.2f}   >0.5: {sum(1 for x in en if x>.5)}/{len(en)}")
    print(f"   irritation risk  median {statistics.median(ir):.2f}   spread {min(ir):.2f}-{max(ir):.2f}")
    print(f"   fit confidence   median {statistics.median(cf):.2f}")
    if flag:
        risky=sorted(S,key=lambda p:-a[p["code"]+"|irritate"]["noul"])[:4]
        print("   HIGHEST IRRITATION RISK FOR PRIYA:")
        for p in risky:
            print(f"     {a[p['code']+'|irritate']['noul']:.2f}  {p['brands'][:16]:18s} {p['product_name'][:28]:30s}")
        safe=sorted(S,key=lambda p:a[p["code"]+"|irritate"]["noul"])[:3]
        print("   SAFEST FOR PRIYA:")
        for p in safe:
            print(f"     {a[p['code']+'|irritate']['noul']:.2f}  {p['brands'][:16]:18s} {p['product_name'][:28]:30s}")
