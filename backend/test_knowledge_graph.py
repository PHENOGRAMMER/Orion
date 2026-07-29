from app.scanner.scanner import ProjectScanner

scanner = ProjectScanner()

_, index = scanner.scan(".")

graph = index.knowledge_graph

print("\nKnowledge Graph")
print("=" * 60)

print(f"Nodes : {graph.node_count}")
print(f"Edges : {graph.edge_count}")

print("\nNodes")

for node in graph.nodes.values():

    print(
        f"{node.type.value:10} {node.name}"
    )

print("\nEdges")

for edge in graph.edges:
    if edge.type.value == "imports":
        print(
            f"{edge.source} --> {edge.target}"
        )