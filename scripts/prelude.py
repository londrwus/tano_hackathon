"""Shared constants for the eval/engine scripts. Keys come from the environment only."""
import json, os, pathlib
JEV = os.environ["JEV_API_KEY"]
OA  = os.environ.get("OPENAI_API_KEY", "")
REPO = pathlib.Path(__file__).resolve().parent.parent
_P = json.loads((REPO / "data" / "case-001-maya.json").read_text(encoding="utf-8"))
SHELF, VOICE = _P["shelf"], _P["voice"]
_cat = REPO / "data" / "real-catalogue-openbeautyfacts.json"
CAT = json.loads(_cat.read_text(encoding="utf-8")) if _cat.exists() else []
BAD = ("body","hand","foot","feet","hair","shampoo","deodorant","soap bar","lip balm","baby","shaving")
CAND = [p for p in CAT if not any(b in (p.get("product_name","")+" "+" ".join(p.get("categories_tags_en",[]))).lower() for b in BAD)]
