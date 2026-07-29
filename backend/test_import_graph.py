from app.scanner.scanner import ProjectScanner
from app.scanner.knowledge_graph.models import EdgeType

scanner = ProjectScanner()

_, index = scanner.scan(".")

graph = index.knowledge_graph

imports = [
    edge
    for edge in graph.edges
    if edge.type == EdgeType.IMPORTS
]

print("=" * 80)
print("IMPORT GRAPH")
print("=" * 80)
print()

print(f"IMPORT EDGES: {len(imports)}")
print()

for edge in imports:
    print(
        f"{edge.source} --IMPORTS--> {edge.target}"
    )