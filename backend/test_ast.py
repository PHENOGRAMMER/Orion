from app.scanner.call_graph.visitor import ReturnTypeCollector

class A:
    def foo(self):
        collector = ReturnTypeCollector({}, "app.scanner.call_graph.visitor")
        collector.visit(None)