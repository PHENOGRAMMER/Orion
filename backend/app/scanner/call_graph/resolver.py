from __future__ import annotations

from builtins import __dict__ as builtins_dict

from app.core.logging import logger
from app.scanner.symbol_index import SymbolIndex, SymbolInfo
from app.scanner.models import ProjectScanResult

from .models import (
    CallSite,
    ResolvedCall,
)


class CallResolver:
    """
    Resolves extracted CallSite objects into project symbols.
    """

    #: How many unresolved call sites to keep as diagnostic samples.
    MAX_UNRESOLVED_SAMPLES = 200

    def __init__(self, symbol_index: SymbolIndex, scan_result: ProjectScanResult):
        self.symbol_index = symbol_index
        self.scan_result = scan_result
        self.unresolved_logged = 0
        self.raw_calls = 0
        self.resolved_calls = 0
        self.unresolved_calls = 0
        self.simple_calls = 0
        self.self_calls = 0
        self.class_calls = 0
        self.attribute_calls = 0
        self.unresolved_category_counts: dict[str, int] = {}
        # Diagnostic sample of unresolved call sites, capped at MAX_UNRESOLVED_SAMPLES.
        # Held in memory rather than written to a file so that scanning stays a pure
        # read-only operation — a scan should never write into the caller's cwd.
        self.unresolved_samples: list[dict[str, object]] = []

    def _is_builtin_call(self, call: CallSite) -> bool:
        callee_root = call.callee.split(".", 1)[0]
        if callee_root in builtins_dict:
            return True

        if call.receiver and call.receiver.split(".", 1)[0] in builtins_dict:
            return True

        return False

    def _unresolved_category(self, call: CallSite, file_symbols) -> str:
        import_aliases = set()
        if file_symbols:
            for imp in file_symbols.imports:
                if imp.alias:
                    import_aliases.add(imp.alias)
                elif imp.name:
                    import_aliases.add(imp.name)

        if call.callee.startswith("self."):
            return "self.attr.method()"

        if call.receiver and call.receiver in import_aliases:
            return "imported alias calls"

        if call.receiver and call.receiver.startswith("self."):
            return "self.attr.method()"

        if call.receiver and call.receiver[0].isupper():
            return "Class.method()"

        if call.receiver:
            return "obj.method()"

        if "." in call.callee:
            head = call.callee.split(".", 1)[0]
            if head and head[0].isupper():
                return "Class.method()"
            return "module.function()"

        return "foo()"

    def _lookup_file_symbols(self, call: CallSite):
        try:
            relative_path = call.file.relative_to(self.scan_result.root_path).as_posix()
        except ValueError:
            relative_path = call.file.as_posix()

        file_symbols = self.scan_result.symbol_graph.files.get(relative_path)
        if file_symbols is not None:
            return file_symbols

        absolute_path = call.file.as_posix()
        file_symbols = self.scan_result.symbol_graph.files.get(absolute_path)
        if file_symbols is not None:
            return file_symbols

        for file_key, candidate in self.scan_result.symbol_graph.files.items():
            if file_key.endswith(relative_path) or relative_path.endswith(file_key):
                return candidate

        return None

    def _record_unresolved(self, call: CallSite, caller: str, file_symbols) -> None:
        if self._is_builtin_call(call):
            return

        if call.receiver is None or call.receiver_type is not None:
            return

        category = self._unresolved_category(call, file_symbols)
        self.unresolved_category_counts[category] = self.unresolved_category_counts.get(category, 0) + 1
        self.unresolved_calls += 1

        if self.unresolved_logged >= self.MAX_UNRESOLVED_SAMPLES:
            return

        self.unresolved_samples.append(
            {
                "file": call.file,
                "line": call.line,
                "caller": caller,
                "callee": call.callee,
                "receiver": call.receiver,
                "category": category,
            }
        )
        self.unresolved_logged += 1

    def resolve(
        self,
        calls: list[CallSite],
    ) -> list[ResolvedCall]:

        resolved: list[ResolvedCall] = []

        self.raw_calls = 0
        self.resolved_calls = 0
        self.unresolved_calls = 0
        self.simple_calls = 0
        self.self_calls = 0
        self.class_calls = 0
        self.attribute_calls = 0
        self.unresolved_category_counts = {}
        self.unresolved_logged = 0
        self.unresolved_samples = []

        for call in calls:
            self.raw_calls += 1
            name = call.callee

            if "." not in name:
                self.simple_calls += 1
            elif name.startswith("self."):
                self.self_calls += 1
            elif name.startswith("cls."):
                self.class_calls += 1
            else:
                self.attribute_calls += 1

            edge = self._resolve_call(call)

            if edge is not None:
                self.resolved_calls += 1
                resolved.append(edge)

        logger.info(
            "Call resolution: %d/%d resolved, %d unresolved (%s)",
            self.resolved_calls,
            self.raw_calls,
            self.unresolved_calls,
            ", ".join(
                f"{category}={count}"
                for category, count in sorted(
                    self.unresolved_category_counts.items(),
                    key=lambda item: -item[1],
                )
            )
            or "none",
        )

        return resolved

    def _resolve_method_with_inheritance(self, class_qualified_name: str, method_name: str) -> SymbolInfo | None:
        # 1. Check if the method is defined directly in this class
        qualified_method = f"{class_qualified_name}.{method_name}"
        symbol = self.symbol_index.lookup_qualified(qualified_method)
        if symbol:
            return symbol

        # 2. Otherwise look up the class symbol itself to find its bases
        class_symbol = self.symbol_index.lookup_qualified(class_qualified_name)
        if not class_symbol or class_symbol.symbol_type != "class":
            return None

        # Check in the class_symbol's file_symbols for base class imports
        try:
            relative_path = class_symbol.path.as_posix()
        except Exception:
            relative_path = str(class_symbol.path)

        file_symbols = self.scan_result.symbol_graph.files.get(relative_path)
        if file_symbols:
            class_def = next((c for c in file_symbols.classes if c.name == class_symbol.name), None)
            if class_def:
                for base in class_def.base_classes:
                    base_qualified = None
                    for imp in file_symbols.imports:
                        if base == imp.alias or (not imp.alias and base == imp.name):
                            base_qualified = f"{imp.resolved_module or imp.module}.{imp.resolved_symbol or imp.name}"
                            break
                        elif base.startswith((imp.alias or imp.name or "") + "."):
                            parts = base.split(".", 1)
                            if len(parts) > 1:
                                base_qualified = f"{imp.resolved_module or imp.module}.{parts[1]}"
                                break
                    
                    if not base_qualified:
                        base_qualified = f"{class_symbol.module}.{base}"

                    res_sym = self._resolve_method_with_inheritance(base_qualified, method_name)
                    if res_sym:
                        return res_sym
        return None

    def _resolve_call(
        self,
        call: CallSite,
    ) -> ResolvedCall | None:

        if call.class_name:
            # call.caller sometimes already includes the class name prefix
            # (e.g. "SourceRootScorer.evaluate") — avoid doubling it.
            if call.caller.startswith(call.class_name + "."):
                caller = f"{call.module}.{call.caller}"
            else:
                caller = f"{call.module}.{call.class_name}.{call.caller}"
        else:
            caller = f"{call.module}.{call.caller}"

        #
        # PASS 0
        # Direct lookup / Inheritance lookup (for fully qualified callee names)
        #
        if "." in call.callee:
            # Try to split callee into a class name and method name by looking up
            # the prefix in SymbolIndex as a class.
            callee_parts = call.callee.split(".")
            for prefix_len in range(len(callee_parts) - 1, 0, -1):
                class_prefix = ".".join(callee_parts[:prefix_len])
                method_part = ".".join(callee_parts[prefix_len:])
                
                class_symbol = self.symbol_index.lookup_qualified(class_prefix)
                if class_symbol and class_symbol.symbol_type == "class":
                    resolved_symbol = self._resolve_method_with_inheritance(class_prefix, method_part)
                    if resolved_symbol:
                        return ResolvedCall(
                            caller_symbol=caller,
                            callee_symbol=resolved_symbol.qualified_name,
                            file=call.file,
                            line=call.line,
                        )

            # Direct lookup if it's already a fully qualified function/variable
            symbol = self.symbol_index.lookup_qualified(call.callee)
            if symbol:
                return ResolvedCall(
                    caller_symbol=caller,
                    callee_symbol=symbol.qualified_name,
                    file=call.file,
                    line=call.line,
                )

        #
        # PASS 0b
        # If receiver_type is known, use it directly with the method name.
        # This handles two cases:
        #   1. Callee is over-qualified (e.g. includes intermediate attribute path)
        #      e.g. callee = 'app.x.Class.attr.method', receiver_type = 'app.y.Class'
        #   2. receiver_type was resolved via __init__.py re-export to a short alias
        #      but the actual symbol lives in the sub-module.
        #
        if call.receiver_type:
            method_name = call.callee.split(".")[-1]

            # Try receiver_type + method directly
            qualified = f"{call.receiver_type}.{method_name}"
            symbol = self.symbol_index.lookup_qualified(qualified)
            if symbol:
                return ResolvedCall(
                    caller_symbol=caller,
                    callee_symbol=symbol.qualified_name,
                    file=call.file,
                    line=call.line,
                )

            # Inheritance walk on the receiver_type
            resolved_symbol = self._resolve_method_with_inheritance(call.receiver_type, method_name)
            if resolved_symbol:
                return ResolvedCall(
                    caller_symbol=caller,
                    callee_symbol=resolved_symbol.qualified_name,
                    file=call.file,
                    line=call.line,
                )

            # Fallback: receiver_type may be a re-exported alias (e.g. app.pkg.ClassName
            # but actual qualified name is app.pkg.module.ClassName).  Look up by class name.
            class_name = call.receiver_type.split(".")[-1]
            if class_name and class_name[0].isupper():
                candidates = self.symbol_index.lookup(class_name)
                for candidate in candidates:
                    if candidate.symbol_type == "class":
                        method_sym = self.symbol_index.lookup_qualified(
                            f"{candidate.qualified_name}.{method_name}"
                        )
                        if method_sym:
                            return ResolvedCall(
                                caller_symbol=caller,
                                callee_symbol=method_sym.qualified_name,
                                file=call.file,
                                line=call.line,
                            )

        #
        # PASS 1
        # Resolve self.method()
        #

        if (
            call.callee.startswith("self.")
            and call.class_name
            and call.module
        ):

            method_name = call.callee.split(".", 1)[1]

            qualified = (
                f"{call.module}."
                f"{call.class_name}."
                f"{method_name}"
            )

            symbol = self.symbol_index.lookup_qualified(
                qualified
            )

            if symbol:

                return ResolvedCall(
                    caller_symbol=caller,
                    callee_symbol=symbol.qualified_name,
                    file=call.file,
                    line=call.line,
                )

        #
        # PASS 2
        # Resolve local function calls:
        #
        # def foo():
        #     ...
        #
        # def bar():
        #     foo()
        #

        if "." not in call.callee and call.module:

            qualified = f"{call.module}.{call.callee}"

            symbol = self.symbol_index.lookup_qualified(
                qualified
            )

            if symbol:

                return ResolvedCall(
                    caller_symbol=caller,
                    callee_symbol=symbol.qualified_name,
                    file=call.file,
                    line=call.line,
                )

        #
        # PASS 3 & 4 & 5
        # Resolve imported symbols and module attributes
        #

        file_symbols = self._lookup_file_symbols(call)

        if file_symbols:

            for imp in file_symbols.imports:
                
                #
                # Step 3 & 5: Simple function/class call (e.g. ProjectIndex() or np.array() if array was imported? No, np.array is module.attr)
                # If call.callee has no dots, it could be an imported symbol.
                #
                if "." not in call.callee:
                    if (imp.alias and imp.alias == call.callee) or (not imp.alias and imp.name == call.callee):
                        
                        target_module = imp.resolved_module or imp.module
                        target_symbol = imp.resolved_symbol or imp.name
                        
                        if target_module and target_symbol:
                            qualified = f"{target_module}.{target_symbol}"
                            symbol = self.symbol_index.lookup_qualified(qualified)
                            
                            if symbol:
                                return ResolvedCall(
                                    caller_symbol=caller,
                                    callee_symbol=symbol.qualified_name,
                                    file=call.file,
                                    line=call.line,
                                )

                #
                # Step 4 & 5: Module attribute call (e.g. scanner.scan(), math.sqrt(), np.array(), app.scanner.models.ProjectScanResult())
                #
                else:
                    callee_parts = call.callee.split(".")
                    # Try matching prefix parts from longest to shortest
                    for prefix_len in range(len(callee_parts) - 1, 0, -1):
                        prefix_parts = callee_parts[:prefix_len]
                        symbol_parts = callee_parts[prefix_len:]
                        
                        module_part = ".".join(prefix_parts)
                        symbol_part = ".".join(symbol_parts)
                        
                        is_match = False
                        
                        if imp.alias and imp.alias == module_part:
                            is_match = True
                        elif not imp.alias and imp.name is None and (imp.module == module_part or imp.module.endswith("." + module_part)):
                            is_match = True
                        elif not imp.alias and imp.name == module_part:
                            is_match = True
                            
                        if is_match:
                            # Determine the prefix base name for the imported entity.
                            # If imp.resolved_symbol is set, then the imported name refers to a symbol (e.g. class)
                            # rather than a module itself.
                            if imp.resolved_symbol:
                                target_base = f"{imp.resolved_module or imp.module}.{imp.resolved_symbol}"
                            elif imp.name and not imp.resolved_module:
                                # Fallback if resolution fields are not fully set
                                target_base = f"{imp.module}.{imp.name}"
                            else:
                                target_base = imp.resolved_module or imp.module
                            
                            if target_base:
                                qualified = f"{target_base}.{symbol_part}"
                                symbol = self.symbol_index.lookup_qualified(qualified)
                                
                                if symbol:
                                    return ResolvedCall(
                                        caller_symbol=caller,
                                        callee_symbol=symbol.qualified_name,
                                        file=call.file,
                                        line=call.line,
                                    )


        #
        # PASS 6
        # Unambiguous single-match: if callee has no dots and exactly one project
        # symbol with that name exists, resolve it confidently.
        # Handles bare calls like visit() inside a visitor class where the method
        # is defined in the project and there is no ambiguity.
        #
        if "." not in call.callee:
            matches = self.symbol_index.lookup(call.callee)
            if len(matches) == 1:
                return ResolvedCall(
                    caller_symbol=caller,
                    callee_symbol=matches[0].qualified_name,
                    file=call.file,
                    line=call.line,
                )

        #
        # Not handled yet.
        #

        file_symbols = self._lookup_file_symbols(call)

        self._record_unresolved(call, caller, file_symbols)
        return None