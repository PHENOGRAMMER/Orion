# Unresolved Object Calls Report

Total unresolved object calls: 238

## Bucket Summary

- Constructor assignment: 0
- Imported constructor: 0
- Factory methods: 0
- Method return: 18
- self attribute: 28
- Nested attribute: 89
- Other / external: 103

## Task List

- `Constructor assignment` and `Imported constructor` are currently zero in this scan, so they are not the immediate next gain.
- `Method return`, `self attribute`, and `Nested attribute` are the actionable buckets inside the project code.
- `Other / external` is the dominant remainder and should stay unresolved unless you decide to broaden resolution beyond project symbols.

## Constructor assignment (0)

None in current scan.

## Imported constructor (0)

None in current scan.

## Factory methods (0)

None in current scan.

## Method return (18)

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
91
CALLER:
CallResolver._lookup_file_symbols
CALLEE:
relative_path.endswith
RECEIVER:
relative_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
100
CALLER:
ReturnTypeCollector._infer_expr_type
CALLEE:
callee.startswith
RECEIVER:
callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
101
CALLER:
ReturnTypeCollector._infer_expr_type
CALLEE:
callee.split
RECEIVER:
callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
106
CALLER:
ReturnTypeCollector._infer_expr_type
CALLEE:
callee.split
RECEIVER:
callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
382
CALLER:
CallVisitor._infer_expr_type
CALLEE:
callee.startswith
RECEIVER:
callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
383
CALLER:
CallVisitor._infer_expr_type
CALLEE:
callee.split
RECEIVER:
callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
388
CALLER:
CallVisitor._infer_expr_type
CALLEE:
callee.split
RECEIVER:
callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
113
CALLER:
FrameworkDetector._detect_requirements
CALLEE:
package.startswith
RECEIVER:
package
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
116
CALLER:
FrameworkDetector._detect_requirements
CALLEE:
package.split
RECEIVER:
package
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
211
CALLER:
FrameworkDetector._detect_package_json
CALLEE:
data.get
RECEIVER:
data
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
215
CALLER:
FrameworkDetector._detect_package_json
CALLEE:
data.get
RECEIVER:
data
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\module_utils.py
LINE:
76
CALLER:
ModuleNameBuilder.build
CALLEE:
relative.with_suffix
RECEIVER:
relative
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\module_utils.py
LINE:
114
CALLER:
ModuleNameBuilder.build
CALLEE:
module_name.rsplit
RECEIVER:
module_name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\utils.py
LINE:
36
CALLER:
normalize_module_name
CALLEE:
module.endswith
RECEIVER:
module
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
91
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
relative_path.as_posix
RECEIVER:
relative_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
85
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
relative_path.as_posix
RECEIVER:
relative_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
91
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
relative_path.as_posix
RECEIVER:
relative_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\test_project.py
LINE:
31
CALLER:
main
CALLEE:
project.exists
RECEIVER:
project
RECEIVER TYPE:
None

## self attribute (28)

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
34
CALLER:
CallGraphBuilder.build
CALLEE:
self.calls.clear
RECEIVER:
self.calls
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
35
CALLER:
CallGraphBuilder.build
CALLEE:
self.class_attr_types.clear
RECEIVER:
self.class_attr_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
97
CALLER:
CallGraphBuilder.build
CALLEE:
self.calls.extend
RECEIVER:
self.calls
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
104
CALLER:
CallResolver._record_unresolved
CALLEE:
self.unresolved_category_counts.get
RECEIVER:
self.unresolved_category_counts
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
165
CALLER:
CallResolver._resolve_method_with_inheritance
CALLEE:
self.symbol_index.lookup_qualified
RECEIVER:
self.symbol_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
170
CALLER:
CallResolver._resolve_method_with_inheritance
CALLEE:
self.symbol_index.lookup_qualified
RECEIVER:
self.symbol_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
226
CALLER:
CallResolver._resolve_call
CALLEE:
self.symbol_index.lookup_qualified
RECEIVER:
self.symbol_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
238
CALLER:
CallResolver._resolve_call
CALLEE:
self.symbol_index.lookup_qualified
RECEIVER:
self.symbol_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
266
CALLER:
CallResolver._resolve_call
CALLEE:
self.symbol_index.lookup_qualified
RECEIVER:
self.symbol_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
300
CALLER:
CallResolver._resolve_call
CALLEE:
self.symbol_index.lookup_qualified
RECEIVER:
self.symbol_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
356
CALLER:
CallResolver._resolve_call
CALLEE:
self.symbol_index.lookup_qualified
RECEIVER:
self.symbol_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
402
CALLER:
CallResolver._resolve_call
CALLEE:
self.symbol_index.lookup_qualified
RECEIVER:
self.symbol_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
213
CALLER:
CallVisitor._lookup_class_attribute_type
CALLEE:
self.collected_class_attr_types.get
RECEIVER:
self.collected_class_attr_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
220
CALLER:
CallVisitor._lookup_class_attribute_type
CALLEE:
self.project_class_attr_types.items
RECEIVER:
self.project_class_attr_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
242
CALLER:
CallVisitor._infer_receiver_type
CALLEE:
self.collected_class_attr_types.get
RECEIVER:
self.collected_class_attr_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
291
CALLER:
CallVisitor._collect_imports
CALLEE:
self.module.split
RECEIVER:
self.module
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
448
CALLER:
CallVisitor.visit_Call
CALLEE:
self.calls.append
RECEIVER:
self.calls
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
120
CALLER:
FrameworkDetector._detect_requirements
CALLEE:
self.PYTHON_PACKAGES.get
RECEIVER:
self.PYTHON_PACKAGES
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
220
CALLER:
FrameworkDetector._detect_package_json
CALLEE:
self.JS_PACKAGES.get
RECEIVER:
self.JS_PACKAGES
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\graph.py
LINE:
76
CALLER:
KnowledgeGraph.add_edge
CALLEE:
self.edges.append
RECEIVER:
self.edges
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\graph.py
LINE:
90
CALLER:
KnowledgeGraph.get_node
CALLEE:
self.nodes.get
RECEIVER:
self.nodes
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\graph.py
LINE:
100
CALLER:
KnowledgeGraph.outgoing
CALLEE:
self._outgoing.get
RECEIVER:
self._outgoing
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\graph.py
LINE:
110
CALLER:
KnowledgeGraph.incoming
CALLEE:
self._incoming.get
RECEIVER:
self._incoming
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\graph.py
LINE:
153
CALLER:
KnowledgeGraph.has_edge
CALLEE:
self._outgoing.get
RECEIVER:
self._outgoing
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\models.py
LINE:
48
CALLER:
SourceRoot.source_file_count
CALLEE:
self.language_counts.values
RECEIVER:
self.language_counts
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_index.py
LINE:
93
CALLER:
SymbolIndex.add
CALLEE:
self.symbols.setdefault
RECEIVER:
self.symbols
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_index.py
LINE:
110
CALLER:
SymbolIndex.lookup
CALLEE:
self.symbols.get
RECEIVER:
self.symbols
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_index.py
LINE:
123
CALLER:
SymbolIndex.lookup_qualified
CALLEE:
self.qualified_symbols.get
RECEIVER:
self.qualified_symbols
RECEIVER TYPE:
None

## Nested attribute (89)

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
70
CALLER:
CallGraphBuilder.build
CALLEE:
app.scanner.call_graph.visitor.CallVisitor.collected_class_attr_types.items
RECEIVER:
analysis_visitor.collected_class_attr_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
100
CALLER:
CallGraphBuilder.build
CALLEE:
app.scanner.call_graph.visitor.CallVisitor.collected_class_attr_types.items
RECEIVER:
visitor.collected_class_attr_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
34
CALLER:
CallResolver._is_builtin_call
CALLEE:
call.callee.split
RECEIVER:
call.callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
38
CALLER:
CallResolver._is_builtin_call
CALLEE:
call.receiver.split
RECEIVER:
call.receiver
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
52
CALLER:
CallResolver._unresolved_category
CALLEE:
call.callee.startswith
RECEIVER:
call.callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
58
CALLER:
CallResolver._unresolved_category
CALLEE:
call.receiver.startswith
RECEIVER:
call.receiver
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
68
CALLER:
CallResolver._unresolved_category
CALLEE:
call.callee.split
RECEIVER:
call.callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
77
CALLER:
CallResolver._lookup_file_symbols
CALLEE:
call.file.relative_to
RECEIVER:
call.file
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
79
CALLER:
CallResolver._lookup_file_symbols
CALLEE:
call.file.as_posix
RECEIVER:
call.file
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
81
CALLER:
CallResolver._lookup_file_symbols
CALLEE:
self.scan_result.symbol_graph.files.get
RECEIVER:
self.scan_result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
85
CALLER:
CallResolver._lookup_file_symbols
CALLEE:
call.file.as_posix
RECEIVER:
call.file
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
86
CALLER:
CallResolver._lookup_file_symbols
CALLEE:
self.scan_result.symbol_graph.files.get
RECEIVER:
self.scan_result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
90
CALLER:
CallResolver._lookup_file_symbols
CALLEE:
self.scan_result.symbol_graph.files.items
RECEIVER:
self.scan_result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
176
CALLER:
CallResolver._resolve_method_with_inheritance
CALLEE:
class_symbol.path.as_posix
RECEIVER:
class_symbol.path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
180
CALLER:
CallResolver._resolve_method_with_inheritance
CALLEE:
self.scan_result.symbol_graph.files.get
RECEIVER:
self.scan_result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
221
CALLER:
CallResolver._resolve_call
CALLEE:
call.callee.split
RECEIVER:
call.callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
253
CALLER:
CallResolver._resolve_call
CALLEE:
call.callee.startswith
RECEIVER:
call.callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
258
CALLER:
CallResolver._resolve_call
CALLEE:
call.callee.split
RECEIVER:
call.callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
370
CALLER:
CallResolver._resolve_call
CALLEE:
call.callee.split
RECEIVER:
call.callee
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
383
CALLER:
CallResolver._resolve_call
CALLEE:
imp.module.endswith
RECEIVER:
imp.module
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\dependency_detector.py
LINE:
37
CALLER:
DependencyDetector.analyze
CALLEE:
index.files_by_extension.get
RECEIVER:
index.files_by_extension
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
136
CALLER:
FileSystemScanner._scan_directory
CALLEE:
app.scanner.models.DirectoryScanResult.files.extend
RECEIVER:
result.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
143
CALLER:
FileSystemScanner._scan_directory
CALLEE:
app.scanner.models.DirectoryScanResult.files.append
RECEIVER:
result.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
178
CALLER:
FileSystemScanner._should_ignore
CALLEE:
path.suffix.lower
RECEIVER:
path.suffix
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
198
CALLER:
FileSystemScanner._create_file_info
CALLEE:
file_path.suffix.lower
RECEIVER:
file_path.suffix
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
212
CALLER:
FileSystemScanner._create_file_info
CALLEE:
file_path.suffix.lower
RECEIVER:
file_path.suffix
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
243
CALLER:
FileSystemScanner._update_extension_stats
CALLEE:
statistics.extensions.setdefault
RECEIVER:
statistics.extensions
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
263
CALLER:
FileSystemScanner._update_hidden_files
CALLEE:
file_path.name.startswith
RECEIVER:
file_path.name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
95
CALLER:
FrameworkDetector._detect_requirements
CALLEE:
index.config_files.get
RECEIVER:
index.config_files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
138
CALLER:
FrameworkDetector._detect_pyproject
CALLEE:
index.config_files.get
RECEIVER:
index.config_files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
190
CALLER:
FrameworkDetector._detect_package_json
CALLEE:
index.config_files.get
RECEIVER:
index.config_files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
264
CALLER:
FrameworkDetector._detect_docker
CALLEE:
result.framework_statistics.containerization.append
RECEIVER:
result.framework_statistics.containerization
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
274
CALLER:
FrameworkDetector._detect_docker
CALLEE:
result.framework_statistics.containerization.append
RECEIVER:
result.framework_statistics.containerization
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
292
CALLER:
FrameworkDetector._detect_github_actions
CALLEE:
result.framework_statistics.ci_cd.append
RECEIVER:
result.framework_statistics.ci_cd
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\git_detector.py
LINE:
87
CALLER:
GitDetector.analyze
CALLEE:
git.Repo.git.symbolic_ref
RECEIVER:
repo.git
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\module_utils.py
LINE:
139
CALLER:
normalize_import_path
CALLEE:
index.files_by_name.get
RECEIVER:
index.files_by_name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\resolver.py
LINE:
34
CALLER:
ImportResolver.resolve
CALLEE:
result.symbol_graph.files.items
RECEIVER:
result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\resolver.py
LINE:
86
CALLER:
ImportResolver._module_name
CALLEE:
index.module_index.items
RECEIVER:
index.module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\symbol_resolver.py
LINE:
86
CALLER:
SymbolResolver.resolve
CALLEE:
symbol.path.as_posix
RECEIVER:
symbol.path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\utils.py
LINE:
68
CALLER:
lookup_module
CALLEE:
index.module_index.get
RECEIVER:
index.module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\utils.py
LINE:
82
CALLER:
lookup_file_symbols
CALLEE:
symbol_graph.files.get
RECEIVER:
symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\utils.py
LINE:
180
CALLER:
resolve_relative_module
CALLEE:
imported.module.split
RECEIVER:
imported.module
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\index_builder.py
LINE:
103
CALLER:
ProjectIndexBuilder._index_file
CALLEE:
index.files_by_name.setdefault
RECEIVER:
index.files_by_name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\index_builder.py
LINE:
112
CALLER:
ProjectIndexBuilder._index_file
CALLEE:
index.files_by_extension.setdefault
RECEIVER:
index.files_by_extension
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\index_builder.py
LINE:
118
CALLER:
ProjectIndexBuilder._index_file
CALLEE:
index.total_size_by_extension.get
RECEIVER:
index.total_size_by_extension
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\index_builder.py
LINE:
131
CALLER:
ProjectIndexBuilder._index_file
CALLEE:
pathlib.Path.parent.as_posix
RECEIVER:
relative_path.parent
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\index_builder.py
LINE:
135
CALLER:
ProjectIndexBuilder._index_file
CALLEE:
index.directories.add
RECEIVER:
index.directories
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\index_builder.py
LINE:
139
CALLER:
ProjectIndexBuilder._index_file
CALLEE:
index.directories_by_name.setdefault
RECEIVER:
index.directories_by_name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\index_builder.py
LINE:
150
CALLER:
ProjectIndexBuilder._index_file
CALLEE:
index.config_files.setdefault
RECEIVER:
index.config_files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
42
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
module.path.resolve
RECEIVER:
module.path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
43
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
index.module_index.values
RECEIVER:
index.module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
71
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
index.module_index.values
RECEIVER:
index.module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
87
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
module.path.relative_to
RECEIVER:
module.path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
114
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
index.symbol_index.qualified_symbols.values
RECEIVER:
index.symbol_index.qualified_symbols
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
121
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
symbol.symbol_type.lower
RECEIVER:
symbol.symbol_type
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
154
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
result.symbol_graph.files.items
RECEIVER:
result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
191
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
result.symbol_graph.files.values
RECEIVER:
result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
42
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
module.path.resolve
RECEIVER:
module.path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
43
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
index.module_index.values
RECEIVER:
index.module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
65
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
index.module_index.values
RECEIVER:
index.module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
81
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
module.path.relative_to
RECEIVER:
module.path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
108
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
index.symbol_index.qualified_symbols.values
RECEIVER:
index.symbol_index.qualified_symbols
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
115
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
symbol.symbol_type.lower
RECEIVER:
symbol.symbol_type
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
148
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
result.symbol_graph.files.items
RECEIVER:
result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
177
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
result.symbol_graph.files.values
RECEIVER:
result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
42
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
module.path.resolve
RECEIVER:
module.path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
43
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
index.module_index.values
RECEIVER:
index.module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
71
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
index.module_index.values
RECEIVER:
index.module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
87
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
module.path.relative_to
RECEIVER:
module.path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
114
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
index.symbol_index.qualified_symbols.values
RECEIVER:
index.symbol_index.qualified_symbols
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
121
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
symbol.symbol_type.lower
RECEIVER:
symbol.symbol_type
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
154
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
result.symbol_graph.files.items
RECEIVER:
result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
191
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
result.symbol_graph.files.values
RECEIVER:
result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\language_detector.py
LINE:
50
CALLER:
LanguageDetector.analyze
CALLEE:
result.statistics.extensions.items
RECEIVER:
result.statistics.extensions
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\detector.py
LINE:
98
CALLER:
SourceRootDetector.detect
CALLEE:
candidate.path.relative_to
RECEIVER:
candidate.path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\scoring.py
LINE:
106
CALLER:
SourceRootScorer._score_directory_name
CALLEE:
directory.name.lower
RECEIVER:
directory.name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\scoring.py
LINE:
179
CALLER:
SourceRootScorer._score_structure
CALLEE:
child.name.lower
RECEIVER:
child.name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\utils.py
LINE:
77
CALLER:
count_source_files
CALLEE:
file.suffix.lower
RECEIVER:
file.suffix
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_detector.py
LINE:
41
CALLER:
SymbolDetector.analyze
CALLEE:
index.files_by_extension.get
RECEIVER:
index.files_by_extension
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_index_builder.py
LINE:
40
CALLER:
SymbolIndexBuilder.build
CALLEE:
scan_result.symbol_graph.files.items
RECEIVER:
scan_result.symbol_graph.files
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_parser.py
LINE:
47
CALLER:
SymbolParser.parse
CALLEE:
app.scanner.models.FileSymbols.imports.append
RECEIVER:
symbols.imports
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_parser.py
LINE:
58
CALLER:
SymbolParser.parse
CALLEE:
app.scanner.models.FileSymbols.imports.append
RECEIVER:
symbols.imports
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_parser.py
LINE:
69
CALLER:
SymbolParser.parse
CALLEE:
app.scanner.models.FileSymbols.classes.append
RECEIVER:
symbols.classes
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_parser.py
LINE:
95
CALLER:
SymbolParser.parse
CALLEE:
app.scanner.models.FileSymbols.functions.append
RECEIVER:
symbols.functions
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_parser.py
LINE:
174
CALLER:
SymbolParser._collect_assignment
CALLEE:
symbols.variables.append
RECEIVER:
symbols.variables
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_parser.py
LINE:
187
CALLER:
SymbolParser._collect_assignment
CALLEE:
symbols.variables.append
RECEIVER:
symbols.variables
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\test_call_resolution_patterns.py
LINE:
15
CALLER:
_write
CALLEE:
path.parent.mkdir
RECEIVER:
path.parent
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\test_call_visitor.py
LINE:
25
CALLER:
main
CALLEE:
app.scanner.call_graph.visitor.CallVisitor.local_variable_types.items
RECEIVER:
visitor.local_variable_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\test_project.py
LINE:
63
CALLER:
main
CALLEE:
Any.language_statistics.languages.items
RECEIVER:
scan_result.language_statistics.languages
RECEIVER TYPE:
None

## Other / external (103)

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\api\health.py
LINE:
8
CALLER:
health
CALLEE:
router.get
RECEIVER:
router
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\main.py
LINE:
15
CALLER:
root
CALLEE:
app.get
RECEIVER:
app
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
40
CALLER:
CallGraphBuilder.build
CALLEE:
module_index.values
RECEIVER:
module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
44
CALLER:
CallGraphBuilder.build
CALLEE:
file_path.read_text
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
62
CALLER:
CallGraphBuilder.build
CALLEE:
project_return_types.update
RECEIVER:
project_return_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
76
CALLER:
CallGraphBuilder.build
CALLEE:
module_index.values
RECEIVER:
module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\builder.py
LINE:
81
CALLER:
CallGraphBuilder.build
CALLEE:
file_path.read_text
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
48
CALLER:
CallResolver._unresolved_category
CALLEE:
import_aliases.add
RECEIVER:
import_aliases
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
50
CALLER:
CallResolver._unresolved_category
CALLEE:
import_aliases.add
RECEIVER:
import_aliases
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
91
CALLER:
CallResolver._lookup_file_symbols
CALLEE:
file_key.endswith
RECEIVER:
file_key
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
111
CALLER:
CallResolver._record_unresolved
CALLEE:
f.write
RECEIVER:
f
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
112
CALLER:
CallResolver._record_unresolved
CALLEE:
f.write
RECEIVER:
f
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
113
CALLER:
CallResolver._record_unresolved
CALLEE:
f.write
RECEIVER:
f
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
114
CALLER:
CallResolver._record_unresolved
CALLEE:
f.write
RECEIVER:
f
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
115
CALLER:
CallResolver._record_unresolved
CALLEE:
f.write
RECEIVER:
f
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
116
CALLER:
CallResolver._record_unresolved
CALLEE:
f.write
RECEIVER:
f
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
117
CALLER:
CallResolver._record_unresolved
CALLEE:
f.write
RECEIVER:
f
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
118
CALLER:
CallResolver._record_unresolved
CALLEE:
f.write
RECEIVER:
f
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
147
CALLER:
CallResolver.resolve
CALLEE:
name.startswith
RECEIVER:
name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
149
CALLER:
CallResolver.resolve
CALLEE:
name.startswith
RECEIVER:
name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
158
CALLER:
CallResolver.resolve
CALLEE:
resolved.append
RECEIVER:
resolved
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
190
CALLER:
CallResolver._resolve_method_with_inheritance
CALLEE:
base.startswith
RECEIVER:
base
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\resolver.py
LINE:
191
CALLER:
CallResolver._resolve_method_with_inheritance
CALLEE:
base.split
RECEIVER:
base
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
30
CALLER:
ReturnTypeCollector.visit_Module
CALLEE:
self.visit
RECEIVER:
self
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
38
CALLER:
ReturnTypeCollector.visit_ClassDef
CALLEE:
self.generic_visit
RECEIVER:
self
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
116
CALLER:
ReturnTypeCollector._infer_expr_type
CALLEE:
elts_types.append
RECEIVER:
elts_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
208
CALLER:
CallVisitor._lookup_class_attribute_type
CALLEE:
class_type.split
RECEIVER:
class_type
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
221
CALLER:
CallVisitor._lookup_class_attribute_type
CALLEE:
qualified_name.endswith
RECEIVER:
qualified_name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
286
CALLER:
CallVisitor._collect_imports
CALLEE:
name.split
RECEIVER:
name
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
314
CALLER:
CallVisitor.visit_ClassDef
CALLEE:
self.generic_visit
RECEIVER:
self
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
337
CALLER:
CallVisitor.visit_FunctionDef
CALLEE:
self.generic_visit
RECEIVER:
self
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
350
CALLER:
CallVisitor.visit_Assign
CALLEE:
self.generic_visit
RECEIVER:
self
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
398
CALLER:
CallVisitor._infer_expr_type
CALLEE:
elts_types.append
RECEIVER:
elts_types
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
432
CALLER:
CallVisitor.visit_Call
CALLEE:
self.generic_visit
RECEIVER:
self
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\call_graph\visitor.py
LINE:
472
CALLER:
CallVisitor.visit_Call
CALLEE:
self.generic_visit
RECEIVER:
self
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\dependency_parser.py
LINE:
36
CALLER:
DependencyParser.parse
CALLEE:
file_path.exists
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\dependency_parser.py
LINE:
40
CALLER:
DependencyParser.parse
CALLEE:
file_path.read_text
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\dependency_parser.py
LINE:
44
CALLER:
DependencyParser.parse
CALLEE:
file_path.read_text
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\dependency_parser.py
LINE:
63
CALLER:
DependencyParser.parse
CALLEE:
imports.add
RECEIVER:
imports
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\dependency_parser.py
LINE:
71
CALLER:
DependencyParser.parse
CALLEE:
imports.add
RECEIVER:
imports
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
88
CALLER:
FileSystemScanner._scan_directory
CALLEE:
current.iterdir
RECEIVER:
current
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
93
CALLER:
FileSystemScanner._scan_directory
CALLEE:
item.is_dir
RECEIVER:
item
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
138
CALLER:
FileSystemScanner._scan_directory
CALLEE:
item.is_file
RECEIVER:
item
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
170
CALLER:
FileSystemScanner._should_ignore
CALLEE:
path.is_dir
RECEIVER:
path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
194
CALLER:
FileSystemScanner._create_file_info
CALLEE:
file_path.stat
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
197
CALLER:
FileSystemScanner._create_file_info
CALLEE:
file_path.relative_to
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
211
CALLER:
FileSystemScanner._create_file_info
CALLEE:
file_path.relative_to
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
226
CALLER:
FileSystemScanner._get_timezone
CALLEE:
time_zone.upper
RECEIVER:
time_zone
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
253
CALLER:
FileSystemScanner._merge_extensions
CALLEE:
source.items
RECEIVER:
source
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\filesystem.py
LINE:
255
CALLER:
FileSystemScanner._merge_extensions
CALLEE:
target.get
RECEIVER:
target
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
106
CALLER:
FrameworkDetector._detect_requirements
CALLEE:
path.exists
RECEIVER:
path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
111
CALLER:
FrameworkDetector._detect_requirements
CALLEE:
line.strip
RECEIVER:
line
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
117
CALLER:
FrameworkDetector._detect_requirements
CALLEE:
package.split
RECEIVER:
package
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
118
CALLER:
FrameworkDetector._detect_requirements
CALLEE:
package.split
RECEIVER:
package
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
147
CALLER:
FrameworkDetector._detect_pyproject
CALLEE:
path.exists
RECEIVER:
path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
201
CALLER:
FrameworkDetector._detect_package_json
CALLEE:
path.exists
RECEIVER:
path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
210
CALLER:
FrameworkDetector._detect_package_json
CALLEE:
dependencies.update
RECEIVER:
dependencies
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
214
CALLER:
FrameworkDetector._detect_package_json
CALLEE:
dependencies.update
RECEIVER:
dependencies
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
290
CALLER:
FrameworkDetector._detect_github_actions
CALLEE:
directory.startswith
RECEIVER:
directory
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\framework_detector.py
LINE:
312
CALLER:
FrameworkDetector._read_text_files
CALLEE:
f.readlines
RECEIVER:
f
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\module_utils.py
LINE:
57
CALLER:
ModuleNameBuilder.build
CALLEE:
file_path.relative_to
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\module_utils.py
LINE:
74
CALLER:
ModuleNameBuilder.build
CALLEE:
file_path.relative_to
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\module_utils.py
LINE:
90
CALLER:
ModuleNameBuilder.build
CALLEE:
parts.pop
RECEIVER:
parts
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\module_utils.py
LINE:
141
CALLER:
normalize_import_path
CALLEE:
path.as_posix
RECEIVER:
path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\module_utils.py
LINE:
145
CALLER:
normalize_import_path
CALLEE:
path.as_posix
RECEIVER:
path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\symbol_resolver.py
LINE:
70
CALLER:
SymbolResolver.resolve
CALLEE:
symbol_index.lookup_qualified
RECEIVER:
symbol_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\utils.py
LINE:
34
CALLER:
normalize_module_name
CALLEE:
module.strip
RECEIVER:
module
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\utils.py
LINE:
40
CALLER:
normalize_module_name
CALLEE:
module.replace
RECEIVER:
module
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\utils.py
LINE:
80
CALLER:
lookup_file_symbols
CALLEE:
file_path.as_posix
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\utils.py
LINE:
155
CALLER:
resolve_relative_module
CALLEE:
base.split
RECEIVER:
base
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\import_resolver\utils.py
LINE:
180
CALLER:
resolve_relative_module
CALLEE:
current_parts.extend
RECEIVER:
current_parts
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
64
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
node_id.startswith
RECEIVER:
node_id
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
120
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
symbol_type_map.get
RECEIVER:
symbol_type_map
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder.py
LINE:
193
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
module_lookup.get
RECEIVER:
module_lookup
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
114
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
symbol_type_map.get
RECEIVER:
symbol_type_map
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_corrected.py
LINE:
179
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
module_lookup.get
RECEIVER:
module_lookup
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
64
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
node_id.startswith
RECEIVER:
node_id
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
120
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
symbol_type_map.get
RECEIVER:
symbol_type_map
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\builder_debug.py
LINE:
193
CALLER:
KnowledgeGraphBuilder.build
CALLEE:
module_lookup.get
RECEIVER:
module_lookup
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\knowledge_graph\graph.py
LINE:
128
CALLER:
KnowledgeGraph.neighbors
CALLEE:
result.append
RECEIVER:
result
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\language_detector.py
LINE:
58
CALLER:
LanguageDetector.analyze
CALLEE:
languages.get
RECEIVER:
languages
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\detector.py
LINE:
44
CALLER:
SourceRootDetector.detect
CALLEE:
project_root.resolve
RECEIVER:
project_root
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\detector.py
LINE:
52
CALLER:
SourceRootDetector.detect
CALLEE:
candidates.append
RECEIVER:
candidates
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\detector.py
LINE:
62
CALLER:
SourceRootDetector.detect
CALLEE:
path.is_dir
RECEIVER:
path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\detector.py
LINE:
71
CALLER:
SourceRootDetector.detect
CALLEE:
candidates.append
RECEIVER:
candidates
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\detector.py
LINE:
77
CALLER:
SourceRootDetector.detect
CALLEE:
candidates.sort
RECEIVER:
candidates
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\detector.py
LINE:
120
CALLER:
SourceRootDetector.detect
CALLEE:
filtered.append
RECEIVER:
filtered
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\scoring.py
LINE:
109
CALLER:
SourceRootScorer._score_directory_name
CALLEE:
reasons.add
RECEIVER:
reasons
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\scoring.py
LINE:
125
CALLER:
SourceRootScorer._score_project_files
CALLEE:
child.is_file
RECEIVER:
child
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\scoring.py
LINE:
131
CALLER:
SourceRootScorer._score_project_files
CALLEE:
reasons.add
RECEIVER:
reasons
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\scoring.py
LINE:
150
CALLER:
SourceRootScorer._score_source_files
CALLEE:
reasons.add
RECEIVER:
reasons
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\scoring.py
LINE:
156
CALLER:
SourceRootScorer._score_source_files
CALLEE:
reasons.add
RECEIVER:
reasons
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\scoring.py
LINE:
175
CALLER:
SourceRootScorer._score_structure
CALLEE:
child.is_dir
RECEIVER:
child
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\scoring.py
LINE:
188
CALLER:
SourceRootScorer._score_structure
CALLEE:
reasons.add
RECEIVER:
reasons
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\utils.py
LINE:
35
CALLER:
safe_iterdir
CALLEE:
directory.iterdir
RECEIVER:
directory
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\utils.py
LINE:
47
CALLER:
safe_rglob
CALLEE:
directory.rglob
RECEIVER:
directory
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\utils.py
LINE:
73
CALLER:
count_source_files
CALLEE:
file.is_file
RECEIVER:
file
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\source_detector\utils.py
LINE:
86
CALLER:
count_source_files
CALLEE:
languages.get
RECEIVER:
languages
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_index_builder.py
LINE:
37
CALLER:
SymbolIndexBuilder.build
CALLEE:
module_index.values
RECEIVER:
module_index
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_index_builder.py
LINE:
44
CALLER:
SymbolIndexBuilder.build
CALLEE:
path_to_module.get
RECEIVER:
path_to_module
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_parser.py
LINE:
145
CALLER:
SymbolParser._collect_methods
CALLEE:
methods.append
RECEIVER:
methods
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\app\scanner\symbol_parser.py
LINE:
208
CALLER:
SymbolParser._read_source
CALLEE:
file_path.read_text
RECEIVER:
file_path
RECEIVER TYPE:
None

FILE:
C:\Users\cools\OneDrive\Desktop\Orion\backend\test_call_resolution_patterns.py
LINE:
16
CALLER:
_write
CALLEE:
path.write_text
RECEIVER:
path
RECEIVER TYPE:
None
