from rdflib import Graph

# 1. グラフにJSON-LDをロード
g = Graph()
g.parse("data/RadioAct_eli.jsonld", format="json-ld")

# 2. SPARQLクエリ例（タイトルとバージョンを取得）
query = """
SELECT ?title ?version WHERE {
  ?s <http://data.europa.eu/eli/ontology#title> ?title .
  ?s <http://data.europa.eu/eli/ontology#version> ?version .
}
"""

# 3. クエリ実行
for row in g.query(query):
    print(f"title: {row.title}, version: {row.version}") 