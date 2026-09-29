import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import builtins
_real_print = builtins.print
_suppress = True
def _quiet_print(*a, **k):
    if _suppress: return
    _real_print(*a, **k)
builtins.print = _quiet_print

from app.scanner.scanner import ProjectScanner
from app.scanner.call_graph.builder import CallGraphBuilder
from app.scanner.call_graph.resolver import CallResolver

scanner = ProjectScanner()
res, index = scanner.scan('.')
builder = CallGraphBuilder()
raw = builder.build(index.module_index)
_suppress = False

resolver = CallResolver(index.symbol_index, res)

stdlib_external = 0
simple_unresolved = 0
dotted_unresolved = 0
project_dotted_examples = []

for call in raw:
    r = resolver._resolve_call(call)
    if r:
        continue

    try:
        rel = call.file.relative_to(res.root_path).as_posix()
    except ValueError:
        rel = call.file.as_posix()

    if '.' not in call.callee:
        simple_unresolved += 1
    else:
        dotted_unresolved += 1
        if call.module and call.module.startswith('app.'):
            fs = res.symbol_graph.files.get(rel)
            if len(project_dotted_examples) < 25:
                imp_strs = []
                if fs:
                    for i in fs.imports[:5]:
                        imp_strs.append(f"  name={i.name!r} alias={i.alias!r} resolved_module={i.resolved_module!r}")
                project_dotted_examples.append((call.callee, call.module, call.class_name, imp_strs))

print(f'Simple (no-dot) unresolved:    {simple_unresolved}')
print(f'Dotted (obj.foo) unresolved:   {dotted_unresolved}')
print()
print('Project obj.foo() examples:')
for callee, mod, cls, imps in project_dotted_examples:
    print(f'  {callee!r}  in {mod}  cls={cls}')
    for i in imps:
        print(i)
