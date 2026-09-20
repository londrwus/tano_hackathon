import os
import base64, json, time, asyncio, httpx
OA=os.environ["OPENAI_API_KEY"]
JEV=os.environ["JEV_API_KEY"]
P=json.load(open(r"C:\Users\Lenovo\Documents\tano_hackathon\data\case-001-maya.json"))
SHELF=P["shelf"]; VOICE=P["voice"]

IMGS={
 "La Roche-Posay sunscreen":"https://thumb.wikimedia.org/wikipedia/commons/thumb/b/bd/LRP_sunscreen_bottle.jpg/960px-LRP_sunscreen_bottle.jpg",
 "Dior lipstick":"https://thumb.wikimedia.org/wikipedia/commons/thumb/5/5e/DiorLippenstift.jpg/960px-DiorLippenstift.jpg",
}
UA={"User-Agent":"tano-hackathon/1.0"}

SCHEMA={"name":"product","schema":{"type":"object","additionalProperties":False,
 "properties":{
  "product_name":{"type":"string"},"brand":{"type":"string"},
  "category":{"type":"string","description":"cleanser/moisturiser/serum/spf/base/balm/other"},
  "texture_or_finish":{"type":"string"},
  "claims_on_pack":{"type":"array","items":{"type":"string"}},
  "likely_skin_types":{"type":"array","items":{"type":"string"}},
  "fragranced":{"type":"string","enum":["yes","no","unknown"]},
  "positioning":{"type":"string","enum":["drugstore","mid","premium","luxury"]},
  "visible_text":{"type":"string"}},
 "required":["product_name","brand","category","texture_or_finish","claims_on_pack",
             "likely_skin_types","fragranced","positioning","visible_text"]},"strict":True}

def see(url):
    b=httpx.get(url,headers=UA,follow_redirects=True,timeout=60).content
    d="data:image/jpeg;base64,"+base64.b64encode(b).decode()
    r=httpx.post("https://api.openai.com/v1/chat/completions",
      headers={"Authorization":f"Bearer {OA}"},timeout=120,
      json={"model":"gpt-4o-mini","messages":[{"role":"user","content":[
        {"type":"text","text":"Extract the product attributes from this photo. Read any text on the packaging. If a field is not visible, infer conservatively."},
        {"type":"image_url","image_url":{"url":d}}]}],
        "response_format":{"type":"json_schema","json_schema":SCHEMA}})
    return json.loads(r.json()["choices"][0]["message"]["content"]), len(b)

def judge(attrs, price):
    universe=[{"product":p["product"],"gbp":p["gbp"],"type":p["type"],"maya_rating":p["maya_rating"],
               "maya_note":p["maya_note"]} for p in SHELF]
    st={"creator":{"name":"Maya Rao","language":VOICE["style_rules"],"creed":VOICE["creed"],
                   "routing":P["decision_rules"]["routing"]},
        "her_shelf_for_context":universe,
        "price_context_note":"Maya's own shelf runs GBP 20-62. Judge against HER standards.",
        "unseen_product":attrs,"asking_price_gbp":price}
    qs={
     "would_stock":{"type":"noul","instructions":"Would Maya put `unseen_product` on her own shelf at all?",
        "criteria":{"true":"She would recommend it to someone","false":"She would not put her name on it"}},
     "worth_price":{"type":"noul","instructions":"Would Maya tell her audience `unseen_product` is worth `asking_price_gbp`?",
        "criteria":{"true":"Fair price for what it does, by her standards","false":"Good, but the price is doing work the product does not"}},
     "who_for":{"type":"choice","instructions":"Which of Maya's audience would she send `unseen_product` to first?",
        "criteria":{"emily_price_sensitive":"22, budget-capped","priya_sensitive_skin":"reacts to everything",
                    "sophie_beauty_obsessive":"wants her judgement","hannah_overwhelmed":"wants fewer choices",
                    "grace_busy":"5 minutes, 2 products","nobody":"She would not recommend it to any of them"}},
     "displaces":{"type":"choice","instructions":"Which product on `her_shelf_for_context` would `unseen_product` most directly compete with?",
        "criteria":{p["product"]:p["maya_note"] for p in SHELF} | {"none":"Competes with nothing she stocks"}},
     "verdict":{"type":"score","instructions":"How would Maya characterise `unseen_product` at `asking_price_gbp`?",
        "criteria":["Underpriced - she'd defend it higher","Fair","Slightly rich",
                    "Good, but not worth the money","She'd tell you not to buy it"]},
     "on_brand":{"type":"score","instructions":"If Maya endorsed `unseen_product`, what happens to her credibility?",
        "criteria":["Trust grows, obviously her kind of thing","Neutral","Mild mismatch her audience would notice","It would read as a paid plug"]},
    }
    t=time.time()
    r=httpx.post("https://api.typesafe.ai/v1/systemone",headers={"Authorization":f"Bearer {JEV}"},
                 json={"model":"jev-latest","state":st,"questions":qs},timeout=90)
    return r.json(), time.time()-t

for name,url in IMGS.items():
    t0=time.time(); attrs,nb=see(url); tv=time.time()-t0
    price={"La Roche-Posay sunscreen":19,"Dior lipstick":38}[name]
    js,tj=judge(attrs,price)
    a=js["answers"]
    print("="*72)
    print(f"IMAGE: {name}  ({nb//1024}KB)   vision {tv:.1f}s -> Jev {tj:.2f}s")
    print(f"  SEEN: {attrs['brand']} / {attrs['product_name']} | {attrs['category']} | {attrs['positioning']} | fragranced={attrs['fragranced']}")
    print(f"        claims={attrs['claims_on_pack'][:3]}  skin={attrs['likely_skin_types']}")
    print(f"  --- MAYA'S VERDICT at GBP{price} ---")
    print(f"    would stock it      : {a['would_stock']['noul']:.2f}")
    print(f"    worth the price     : {a['worth_price']['noul']:.2f}")
    print(f"    send it to          : {a['who_for']['choice']} ({a['who_for']['confidence']:.2f})")
    print(f"    competes with       : {a['displaces']['choice']} ({a['displaces']['confidence']:.2f})")
    v=a['verdict']; print(f"    verdict             : {v['legend'][str(round(v['score']))]}  [{v['score']:.2f}]")
    c=a['on_brand']; print(f"    credibility effect  : {c['legend'][str(round(c['score']))]}  [{c['score']:.2f}]")
