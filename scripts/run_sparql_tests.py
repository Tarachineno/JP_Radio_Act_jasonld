from rdflib import Graph
import sys

g = Graph()
g.parse("data/RadioAct_eli.jsonld", format="json-ld")

# division_typeが全て"article"かチェック
q1 = """
ASK {
  ?s <http://data.europa.eu/eli/ontology#division_type> "article" .
}
"""
if not g.query(q1).askAnswer:
    print("[FAIL] division_type=articleが見つかりません")
    sys.exit(1)

# validが正しい形式かチェック
q2 = """
SELECT ?valid WHERE {
  ?s <http://data.europa.eu/eli/ontology#valid> ?valid
}
"""
for row in g.query(q2):
    if "/" not in str(row.valid):
        print(f"[FAIL] validの値が期間形式でありません: {row.valid}")
        sys.exit(1)

# version, titleの存在チェック
q3 = """
ASK {
  ?s <http://data.europa.eu/eli/ontology#version> ?v .
  ?s <http://data.europa.eu/eli/ontology#title> ?t .
}
"""
if not g.query(q3).askAnswer:
    print("[FAIL] versionまたはtitleが見つかりません")
    sys.exit(1)

print("SPARQL tests passed.") 