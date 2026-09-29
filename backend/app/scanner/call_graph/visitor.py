from __future__ import annotations

import ast
from pathlib import Path

from .models import CallSite


class ReturnTypeCollector(ast.NodeVisitor):
    """
    Pre-pass visitor to collect return types of functions and methods
    defined in a file.
    """

    def __init__(self, file_imports: dict[str, str], module_name: str):
        self.file_imports = file_imports
        self.module_name = module_name
        self.current_class: str | None = None
        # Maps function/method name (e.g. "scan" or "FileSystemScanner.scan") to fully qualified return type(s)
        self.return_types: dict[str, str | list[str]] = {}
        # Maps local variable -> type within the function we are visiting
        self.local_variable_types: dict[str, str] = {}
        # Maps self.attribute -> type within the class
        self.class_variable_types: dict[str, str] = {}

    def visit_Module(self, node: ast.Module):
        # A second pass helps resolve simple forward references to local factories.
        for _ in range(2):
            for child in node.body:
                self.visit(child)

    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self.current_class
        prev_class_vars = self.class_variable_types
        self.class_variable_types = {}
        self.current_class = node.name

        self.generic_visit(node)

        self.current_class = prev_class
        self.class_variable_types = prev_class_vars

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_locals = self.local_variable_types
        self.local_variable_types = {}

        # Build map of param_name -> annotated type for this function's arguments.
        # Covers positional, positional-only, and keyword-only parameters.
        # Used to resolve self.attr = param when param has a type annotation.
        param_annotation_types: dict[str, str] = {}
        all_args = (
            node.args.args
            + node.args.posonlyargs
            + node.args.kwonlyargs
        )
        for arg in all_args:
            if arg.annotation:
                try:
                    ann = ast.unparse(arg.annotation)
                    # Resolve the annotation against imports if possible
                    resolved = self.file_imports.get(ann, None)
                    if resolved is None:
                        # Handle Optional[X], List[X], etc. — extract bare name
                        bare = ann.split("[")[0].strip()
                        resolved = self.file_imports.get(bare, None)
                        if resolved is None and bare and bare[0].isupper():
                            resolved = f"{self.module_name}.{bare}"
                    if resolved:
                        param_annotation_types[arg.arg] = resolved
                except Exception:
                    pass

        # For __init__, track self.attr = annotated_param assignments so that
        # method calls on self.attr later can be type-inferred.
        if node.name == "__init__" and self.current_class:
            for child in node.body:
                if isinstance(child, ast.Assign) and len(child.targets) == 1:
                    target = child.targets[0]
                    if (isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"
                            and isinstance(child.value, ast.Name)
                            and child.value.id in param_annotation_types):
                        self.class_variable_types[target.attr] = param_annotation_types[child.value.id]

        # Scan assignments first to know types of local variables
        for child in node.body:
            if isinstance(child, ast.Assign):
                self._track_assignment(child)

        # Now look for Return statements
        for child in node.body:
            for subnode in ast.walk(child):
                if isinstance(subnode, ast.Return) and subnode.value:
                    ret_type = self._infer_expr_type(subnode.value)
                    if ret_type:
                        func_key = f"{self.current_class}.{node.name}" if self.current_class else node.name
                        self.return_types[func_key] = ret_type
                        self.return_types[f"{self.module_name}.{func_key}"] = ret_type
                        break

        self.local_variable_types = prev_locals

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    def _track_assignment(self, node: ast.Assign):
        if len(node.targets) != 1:
            return
        target = node.targets[0]
        val_type = self._infer_expr_type(node.value)
        if not val_type:
            return

        if isinstance(target, ast.Name):
            if isinstance(val_type, list):
                # If we assigned a tuple to a single variable, it's a list/tuple type
                pass
            else:
                self.local_variable_types[target.id] = val_type
        elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
            if isinstance(val_type, list):
                for i, t_elt in enumerate(target.elts):
                    if isinstance(t_elt, ast.Name) and i < len(val_type):
                        self.local_variable_types[t_elt.id] = val_type[i]
        elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
            if not isinstance(val_type, list):
                self.class_variable_types[target.attr] = val_type

    def _infer_expr_type(self, node: ast.AST) -> str | list[str] | None:
        if isinstance(node, ast.Call):
            callee = self._get_call_name(node.func)
            if not callee:
                return None

            if callee in self.return_types:
                return self.return_types[callee]

            if callee.startswith("self.") and self.current_class:
                method_name = callee.split(".", 1)[1]
                key = f"{self.current_class}.{method_name}"
                if key in self.return_types:
                    return self.return_types[key]

            class_name = callee.split(".")[-1]
            if class_name and class_name[0].isupper():
                return callee

            return None

        if isinstance(node, ast.Tuple) or isinstance(node, ast.List):
            elts_types = []
            for elt in node.elts:
                t = self._infer_expr_type(elt)
                elts_types.append(t if isinstance(t, str) else "Any")
            return elts_types

        if isinstance(node, ast.Name):
            if node.id in self.local_variable_types:
                return self.local_variable_types[node.id]
            if node.id in self.file_imports:
                return self.file_imports[node.id]
            # Do NOT fabricate module-qualified names for unknown identifiers
            return None

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                if node.attr in self.class_variable_types:
                    return self.class_variable_types[node.attr]
                # self.attr with no known type — return None
                return None
            base = self._infer_expr_type(node.value)
            if isinstance(base, str):
                return f"{base}.{node.attr}"
            return None

        return None

    def _get_call_name(self, node: ast.AST) -> str | None:
        """
        Convert AST call expression into a fully qualified name when possible.
        """

        if isinstance(node, ast.Name):
            if node.id in self.local_variable_types:
                return self.local_variable_types[node.id]
            
            if node.id in self.file_imports:
                return self.file_imports[node.id]

            if node.id and node.id[0].isupper():
                return f"{self.module_name}.{node.id}"

            return node.id

        if isinstance(node, ast.Attribute):
            # Check self attribute rewriting
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                if node.attr in self.class_variable_types:
                    return self.class_variable_types[node.attr]

            base = self._get_call_name(node.value)
            if base:
                return f"{base}.{node.attr}"
            return node.attr

        return None


class CallVisitor(ast.NodeVisitor):
    """
    Collects function/method calls from a Python AST, using type inference.
    """

    def __init__(
        self,
        file_path: Path,
        module: str,
        project_return_types: dict[str, str | list[str]] | None = None):

        self.file_path = file_path
        self.module = module
        self.project_return_types = project_return_types or {}

        self.current_function: str | None = None
        self.current_class: str | None = None

        self.calls: list[CallSite] = []
        
        # Maps imported names/aliases to fully qualified paths
        self.file_imports: dict[str, str] = {}
        # Maps local variable -> fully qualified ClassName
        self.local_variable_types: dict[str, str] = {}
        # Maps self.attribute -> fully qualified ClassName (current class scope)
        self.class_variable_types: dict[str, str] = {}
        # Maps function/method to its return type (populated by pre-pass)
        self.return_types: dict[str, str | list[str]] = {}
        # Persists class attribute types for ALL visited classes (class_name -> {attr -> type})
        self.collected_class_attr_types: dict[str, dict[str, str]] = {}
        # Project-wide class attribute types keyed by fully qualified class name
        self.project_class_attr_types: dict[str, dict[str, str]] = {}

    def _lookup_class_attribute_type(self, class_type: str | None, attr_name: str) -> str | None:
        if not class_type:
            return None

        class_name = class_type.split(".")[-1]

        if self.current_class == class_name and attr_name in self.class_variable_types:
            return self.class_variable_types[attr_name]

        local_attr_types = self.collected_class_attr_types.get(class_name, {})
        if attr_name in local_attr_types:
            return local_attr_types[attr_name]

        if class_type in self.project_class_attr_types:
            return self.project_class_attr_types[class_type].get(attr_name)

        for qualified_name, attr_types in self.project_class_attr_types.items():
            if qualified_name.endswith(f".{class_name}") and attr_name in attr_types:
                return attr_types[attr_name]

        return None

    def _infer_receiver_type(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            if node.id in self.local_variable_types:
                return self.local_variable_types[node.id]
            if node.id in self.file_imports:
                return self.file_imports[node.id]
            if node.id and node.id[0].isupper():
                return f"{self.module}.{node.id}"
            return None

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                if node.attr in self.class_variable_types:
                    return self.class_variable_types[node.attr]

                if self.current_class:
                    return self.collected_class_attr_types.get(self.current_class, {}).get(node.attr)

                return None

            base_type = self._infer_receiver_type(node.value)
            if isinstance(base_type, str):
                attr_type = self._lookup_class_attribute_type(base_type, node.attr)
                if attr_type:
                    return attr_type

        if isinstance(node, ast.Call):
            inferred = self._infer_expr_type(node)
            if isinstance(inferred, str):
                return inferred

        return None

    def _expression_to_string(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            base = self._expression_to_string(node.value)
            if base:
                return f"{base}.{node.attr}"
            return node.attr

        return None

    def visit(self, node: ast.AST):
        # Build local imports first
        self._collect_imports(node)
        # Collect return types next
        collector = ReturnTypeCollector(self.file_imports, self.module)
        collector.visit(node)
        self.return_types = {**self.project_return_types, **collector.return_types}
        # Run normal visitor
        super().visit(node)

    def _collect_imports(self, node: ast.AST):
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Import):
                for alias in subnode.names:
                    name = alias.name
                    asname = alias.asname or name.split(".")[0]
                    self.file_imports[asname] = name
            elif isinstance(subnode, ast.ImportFrom) and subnode.module:
                base_module = subnode.module
                if subnode.level > 0:
                    module_parts = self.module.split(".")
                    strip_count = subnode.level
                    if strip_count <= len(module_parts):
                        parent_module = ".".join(module_parts[:-strip_count])
                        if parent_module:
                            base_module = f"{parent_module}.{subnode.module}"
                for alias in subnode.names:
                    name = alias.name
                    asname = alias.asname or name
                    if name != "*":
                        self.file_imports[asname] = f"{base_module}.{name}"

    # ---------------------------------------------------------
    # Classes
    # ---------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef):
        previous_class = self.current_class
        previous_class_vars = self.class_variable_types
        self.class_variable_types = {}
        
        self.current_class = node.name

        self.generic_visit(node)

        # Save the class attribute types collected for this class before restoring
        if self.current_class and self.class_variable_types:
            self.collected_class_attr_types[self.current_class] = dict(self.class_variable_types)

        self.current_class = previous_class
        self.class_variable_types = previous_class_vars

    # ---------------------------------------------------------
    # Functions
    # ---------------------------------------------------------

    def visit_FunctionDef(self, node: ast.FunctionDef):
        previous_function = self.current_function
        previous_locals = self.local_variable_types
        self.local_variable_types = {}

        if self.current_class:
            self.current_function = f"{self.current_class}.{node.name}"
        else:
            self.current_function = node.name

        # Build param_name -> resolved type from annotations.
        # Covers positional, positional-only, and keyword-only parameters.
        # For __init__, use this to record self.attr types when self.attr = annotated_param.
        if node.name == "__init__" and self.current_class:
            param_annotation_types: dict[str, str] = {}
            all_args = (
                node.args.args
                + node.args.posonlyargs
                + node.args.kwonlyargs
            )
            for arg in all_args:
                if arg.annotation:
                    try:
                        ann = ast.unparse(arg.annotation)
                        bare = ann.split("[")[0].strip()
                        resolved = self.file_imports.get(ann) or self.file_imports.get(bare)
                        if resolved is None and bare and bare[0].isupper():
                            resolved = f"{self.module}.{bare}"
                        if resolved:
                            param_annotation_types[arg.arg] = resolved
                    except Exception:
                        pass

            for child in node.body:
                if isinstance(child, ast.Assign) and len(child.targets) == 1:
                    target = child.targets[0]
                    if (isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"
                            and isinstance(child.value, ast.Name)
                            and child.value.id in param_annotation_types):
                        self.class_variable_types[target.attr] = param_annotation_types[child.value.id]

        self.generic_visit(node)

        self.current_function = previous_function
        self.local_variable_types = previous_locals

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)

    # ---------------------------------------------------------
    # Assignments (Type Tracking)
    # ---------------------------------------------------------

    def visit_Assign(self, node: ast.Assign):
        self.generic_visit(node)

        if len(node.targets) != 1:
            return

        target = node.targets[0]
        val_type = self._infer_expr_type(node.value)
        if not val_type:
            return

        if isinstance(target, ast.Name):
            if not isinstance(val_type, list):
                self.local_variable_types[target.id] = val_type

        elif isinstance(target, ast.Tuple) or isinstance(target, ast.List):
            if isinstance(val_type, list):
                for i, t_elt in enumerate(target.elts):
                    if isinstance(t_elt, ast.Name) and i < len(val_type):
                        self.local_variable_types[t_elt.id] = val_type[i]
        elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
            if not isinstance(val_type, list):
                self.class_variable_types[target.attr] = val_type

    def _infer_expr_type(self, node: ast.AST) -> str | list[str] | None:
        if isinstance(node, ast.Call):
            callee = self._get_call_name(node.func)
            if not callee:
                return None

            if callee in self.return_types:
                return self.return_types[callee]

            if callee.startswith("self.") and self.current_class:
                method_name = callee.split(".", 1)[1]
                key = f"{self.current_class}.{method_name}"
                if key in self.return_types:
                    return self.return_types[key]

            class_name = callee.split(".")[-1]
            if class_name and class_name[0].isupper():
                return callee

            return None

        if isinstance(node, ast.Tuple) or isinstance(node, ast.List):
            elts_types = []
            for elt in node.elts:
                t = self._infer_expr_type(elt)
                elts_types.append(t if isinstance(t, str) else "Any")
            return elts_types

        if isinstance(node, ast.Name):
            if node.id in self.local_variable_types:
                return self.local_variable_types[node.id]
            if node.id in self.file_imports:
                return self.file_imports[node.id]
            # Do NOT fabricate module-qualified names for unknown identifiers
            return None

        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                if node.attr in self.class_variable_types:
                    return self.class_variable_types[node.attr]
                # self.attr with no known type — return None
                return None
            base = self._infer_expr_type(node.value)
            if isinstance(base, str):
                attr_type = self._lookup_class_attribute_type(base, node.attr)
                if attr_type:
                    return attr_type
                return f"{base}.{node.attr}"
            return None

        return None

    # ---------------------------------------------------------
    # Calls
    # ---------------------------------------------------------

    def visit_Call(self, node: ast.Call):

        if self.current_function is None:
            self.generic_visit(node)
            return

        callee = self._get_call_name(node.func)

        receiver = None
        receiver_type = None

        #
        # builder.build()
        #
        if isinstance(node.func, ast.Attribute):
            receiver = self._expression_to_string(node.func.value)
            receiver_type = self._infer_receiver_type(node.func.value)

        if callee is not None:
            self.calls.append(

                CallSite(

                    caller=self.current_function,

                    callee=callee,

                    file=self.file_path,

                    line=node.lineno,

                    module=self.module,

                    class_name=self.current_class,

                    receiver=receiver,

                    receiver_type=receiver_type,

                )

            )

        self.generic_visit(node)

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _get_call_name(self, node: ast.AST) -> str | None:
        """
        Convert AST call expression into a fully qualified name when possible.
        """

        if isinstance(node, ast.Name):
            if node.id in self.local_variable_types:
                return self.local_variable_types[node.id]
            
            if node.id in self.file_imports:
                return self.file_imports[node.id]

            if node.id and node.id[0].isupper():
                return f"{self.module}.{node.id}"

            return node.id

        if isinstance(node, ast.Attribute):
            # Check self attribute rewriting
            if isinstance(node.value, ast.Name) and node.value.id == "self":
                if node.attr in self.class_variable_types:
                    return self.class_variable_types[node.attr]

            base = self._get_call_name(node.value)
            if base:
                return f"{base}.{node.attr}"
            return node.attr

        return None