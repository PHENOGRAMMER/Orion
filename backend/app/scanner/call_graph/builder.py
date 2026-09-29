from __future__ import annotations

import ast
from pathlib import Path

from app.scanner.import_resolver.models import ModuleInfo

from .models import CallSite
from .visitor import CallVisitor, ReturnTypeCollector

# Maps (file_path, class_name) -> {attr_name -> qualified_type}
ClassAttrTypes = dict[tuple[Path, str], dict[str, str]]


class CallGraphBuilder:
    """
    Builds a project-wide raw call graph.
    """

    def __init__(self):
        self.calls: list[CallSite] = []
        # Populated after build(); maps (file_path, class_name) -> {attr: qualified_type}
        self.class_attr_types: ClassAttrTypes = {}

    def build(
        self,
        module_index: dict[str, ModuleInfo],
    ) -> list[CallSite]:
        """
        Scan every Python module and collect function calls.
        Also collects class attribute type maps for resolver use.
        """

        self.calls.clear()
        self.class_attr_types.clear()

        project_return_types: dict[str, str | list[str]] = {}
        project_class_attr_types: dict[str, dict[str, str]] = {}

        for module in module_index.values():
            file_path = module.path

            try:
                source = file_path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

                tree = ast.parse(source)

                import_visitor = CallVisitor(
                    file_path=file_path,
                    module=module.name,
                )
                import_visitor._collect_imports(tree)

                collector = ReturnTypeCollector(
                    file_imports=import_visitor.file_imports,
                    module_name=module.name,
                )
                collector.visit(tree)
                project_return_types.update(collector.return_types)

                analysis_visitor = CallVisitor(
                    file_path=file_path,
                    module=module.name,
                )
                analysis_visitor.visit(tree)

                for class_name, attr_types in analysis_visitor.collected_class_attr_types.items():
                    project_class_attr_types[f"{module.name}.{class_name}"] = attr_types

            except Exception:
                continue

        for module in module_index.values():

            file_path = module.path

            try:
                source = file_path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

                tree = ast.parse(source)

                visitor = CallVisitor(
                    file_path=file_path,
                    module=module.name,
                    project_return_types=project_return_types,
                )
                visitor.project_class_attr_types = project_class_attr_types

                visitor.visit(tree)

                self.calls.extend(visitor.calls)

                # Collect class attribute types gathered during the visit
                for (class_name, attr_types) in visitor.collected_class_attr_types.items():
                    self.class_attr_types[(file_path, class_name)] = attr_types

            except Exception:
                continue

        return self.calls