"""
Diagnostic: why are Passes 3/4/5 not resolving more calls?
Suppresses all import resolver debug output.
"""
import sys
import io
import os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Suppress the import resolver print noise
import builtins
_real_print = builtins.print
_suppress = False

def _quiet_print(*args, **kwargs):
    if _suppress:
        return
    _real_print(*args, **kwargs)

builtins.print = _quiet_print

from pathlib import Path
from app.scanner.scanner import ProjectScanner
from app.scanner.call_graph.builder import CallGraphBuilder
from app.scanner.call_graph.resolver import CallResolver

# Run the scan with print suppressed
_suppress = True
scanner = ProjectScanner()
res, index = scanner.scan(".")
builder = CallGraphBuilder()
raw = builder.build(index.module_index)
_suppress = False

print("=" * 80)
print("DIAGNOSTIC: WHY PASSES 3/4/5 AREN'T RESOLVING")
print("=" * 80)

# Show some qualified_symbols from the symbol_index
print("\n-- Sample qualified_symbols keys (first 40) --")
for i, key in enumerate(sorted(index.symbol_index.qualified_symbols.keys())):
    print(f"  {key}")
    if i >= 39:
        break

print(f"\n  ... total: {len(index.symbol_index.qualified_symbols)} qualified symbols")

# Run the actual resolver
resolver = CallResolver(index.symbol_index, res)
resolved_edges = resolver.resolve(raw)

# Find out which calls were not resolved
resolved_set = {(edge.file, edge.line, edge.caller_symbol, edge.callee_symbol) for edge in resolved_edges}

unresolved_examples = []
resolved_count = 0

for call in raw:
    # Try to resolve it using the actual _resolve_call
    resolved_call = resolver._resolve_call(call)
    if resolved_call:
        resolved_count += 1
    else:
        if len(unresolved_examples) < 50:
            try:
                rel = call.file.relative_to(res.root_path).as_posix()
            except ValueError:
                rel = call.file.as_posix()
            
            detail = {
                "callee": call.callee,
                "module": call.module,
                "class_name": call.class_name,
                "file": rel,
            }
            
            fs = res.symbol_graph.files.get(rel)
            if fs:
                detail["available_imports"] = [
                    f"module={imp.module!r} name={imp.name!r} alias={imp.alias!r}"
                    for imp in fs.imports[:10]
                ]
            unresolved_examples.append(detail)

print(f"\n-- Resolution Stats --")
print(f"Total resolved         : {resolved_count}")
print(f"Total raw              : {len(raw)}")
print(f"Unresolved             : {len(raw) - resolved_count}")

print(f"\n-- Unresolved examples (first 50) --")
for i, ex in enumerate(unresolved_examples):
    print(f"\n{'=' * 60}")
    print(f"[{i}] callee={ex['callee']!r}  module={ex['module']!r}  class={ex['class_name']!r}")
    print(f"    file={ex['file']}")
    if "available_imports" in ex:
        print(f"    Available imports ({len(ex['available_imports'])}):")
        for imp_str in ex["available_imports"]:
            print(f"      {imp_str}")

