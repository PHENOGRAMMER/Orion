# Orion

Point Orion at a Python repository and it builds an explorable, queryable model
of how that code is structured and how it actually interacts — modules, classes,
functions and methods as nodes; imports, declarations and calls as edges.

The result is less "a chatbot that can read my files" and more an intelligent
map of a software system: you can ask who calls a function, what a change would
break, and how one symbol reaches another.

Orion ships with a browser explorer at `http://localhost:8000/app`.

---

## Requirements

- **Python 3.11 or newer.** This is a hard requirement, not a preference: the
  scanner uses `datetime.UTC` and `tomllib`, both added in 3.11. On 3.10 it
  fails at import with `cannot import name 'UTC' from 'datetime'`.
- No JavaScript toolchain. The frontend is a single dependency-free HTML file.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
cd backend
uvicorn app.main:app --reload
```

Then open:

| URL                            | What it is                        |
| ------------------------------ | --------------------------------- |
| `http://localhost:8000/app`    | The graph explorer                |
| `http://localhost:8000/docs`   | Interactive OpenAPI docs          |
| `http://localhost:8000/`       | Service metadata                  |

### Python-first observatory

The optional Streamlit interface keeps the UI workflow in Python while using
the same FastAPI graph and LLM endpoints:

```bash
pip install -r frontend/requirements.txt
streamlit run frontend/streamlit_app.py
```

Open `http://localhost:8501`. It expects Orion at `http://localhost:8000`; set
`ORION_API_URL` when the backend runs elsewhere. The API key field is only
needed when `AUTH_ENABLED=true`.

With no configuration Orion analyses its own `backend/app` package, so a fresh
checkout is immediately explorable and the tool demonstrates itself.

## Configuration

Settings come from the environment or `backend/.env`.

| Variable        | Default                                              | Purpose |
| --------------- | ---------------------------------------------------- | ------- |
| `PROJECT_ROOT`  | *(Orion's own `backend/app`)*                        | Project scanned at startup. |
| `ALLOWED_ROOTS` | *(your home directory)*                              | Directories `/graph/browse` and `/graph/scan` may read. Separate with `:` / `;` or commas. |
| `ALLOW_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000`        | Browser origins allowed to call the API. |
| `PERSISTENCE_DB` | `backend/.orion/orion.db`                           | SQLite database used for graph snapshots, scan jobs, and project metadata. |
| `DEBUG`         | `True`                                               | Debug flag. |

Example `backend/.env`:

```dotenv
PROJECT_ROOT=/home/me/code/my-service
ALLOWED_ROOTS=/home/me/code:/srv/repos
```

> Only variables **declared as fields** in `app/core/config.py` are read.
> Adding an undeclared name to `.env` silently does nothing.

You can also switch projects at runtime from the explorer — click the project
pill, browse to a directory and scan it, no restart needed.

Orion now prefers a persisted snapshot on startup when one exists for the
configured `PROJECT_ROOT`, so restarts do not force an immediate rescan.

## Security

`/graph/browse` and `/graph/scan` read the local filesystem on behalf of an HTTP
client, which makes them the sharpest edge in the app. Two things fence them in:

- **Path allowlist.** Requested paths are resolved first and then checked for
  containment in `ALLOWED_ROOTS`, so neither `..` traversal nor a symlink
  pointing out of an allowed root can escape. Resolution has to happen before
  the check — the reverse order is trivially bypassable.
- **Explicit CORS origins.** `ALLOW_ORIGINS` is a real list rather than `*`.
  With a wildcard, any page in your browser could call these endpoints and
  enumerate your disk.

Orion still has **no authentication**, so treat it as a single-user local tool.
Do not expose it on a shared or public network.

## API

| Method | Endpoint                        | Description |
| ------ | ------------------------------- | ----------- |
| `GET`  | `/health`                       | Liveness check. |
| `GET`  | `/graph/stats`                  | Node/edge counts by type, hottest symbols, current project. |
| `GET`  | `/graph/search`                 | Ranked fuzzy symbol search. `?q=`, `&limit=`, `&types=`. |
| `GET`  | `/graph/symbol/{qualified_name}` | A symbol with its direct callers and callees. |
| `GET`  | `/graph/symbol/{qualified_name}/impact` | Transitive blast radius of changing a symbol. |
| `GET`  | `/graph/path`                   | Shortest call path. `?from_symbol=&to_symbol=`. |
| `GET`  | `/graph/browse`                 | Directory listing for the picker, fenced by `ALLOWED_ROOTS`. |
| `POST` | `/graph/scan`                   | Start a background scan; returns a `job_id`. |
| `GET`  | `/graph/scan/{job_id}`          | Poll scan progress. |
| `POST` | `/agent/proposals`              | Create a supervised edit proposal from exact text edits and return a diff. |
| `GET`  | `/agent/proposals/{proposal_id}` | Review a persisted edit proposal. |
| `POST` | `/agent/proposals/{proposal_id}/apply` | Apply an approved proposal and run validation. |

### Search ranking

Matching is tiered rather than a single blended score, because for code the
*kind* of match matters more than how many characters happen to line up. An
exact name should always beat a lucky subsequence buried in a long dotted path.

| Tier | Match | Example |
| ---- | ----- | ------- |
| 1 | exact name | `lookup` → `SymbolIndex.lookup` |
| 2 | exact qualified name | `app.b.lookup` → `app.b.lookup` |
| 3 | name prefix | `res` → `resolve` |
| 4 | camelCase / snake_case acronym | `cgb` → `CallGraphBuilder` |
| 5 | substring of name | `solve` → `resolve` |
| 6 | substring of qualified name | `resolver.res` → `app.resolver.resolve` |
| 7 | subsequence of qualified name | `asr` → `app.scanner.resolve` |

Ties break toward tighter matches, then shorter names, then alphabetically, so
results are stable between identical queries.

```bash
curl 'localhost:8000/graph/search?q=cgb'
curl 'localhost:8000/graph/search?q=scan&types=method&limit=5'
```

## How it works

`ProjectScanner.scan()` runs a pipeline, each stage enriching a shared index:

```
filesystem walk
  → project index (modules, files)
  → language / framework / git / dependency detection
  → symbol extraction        (classes, functions, methods, variables)
  → symbol index
  → import resolution        (which module does this import actually mean?)
  → call graph               (collect call sites, then resolve them to symbols)
  → knowledge graph          (nodes + declares/imports/calls edges)
```

Parsing uses Python's standard-library `ast` module — **not** Tree-sitter.
`tree-sitter` and `networkx` appear in `requirements.txt` but nothing imports
them; they can be dropped until something needs them.

Node IDs are namespaced strings — `symbol:app.mod.Class.method`,
`module:app.mod`, `file:app/mod.py` — and `KnowledgeGraph` keeps incoming and
outgoing adjacency lists so callers/callees are O(degree) rather than a scan.

`KnowledgeGraphQuery` sits on top and answers the structural questions:
`callers_of`, `callees_of`, `dependencies_of`, `impact_of`, `path_between`,
`symbols_in_module`, `imports_of_module`, `stats`.

### Layout

```
backend/
  app/
    api/          FastAPI routers (health, graph)
    core/         config, logging, path safety, shared graph state
    scanner/      the analysis pipeline
      call_graph/       call-site collection and resolution
      import_resolver/  import → module/symbol resolution
      knowledge_graph/  graph, builder, query, search
      source_detector/  source-root heuristics
  tests/          stdlib unittest suites
  frontend/
    index.html      the whole explorer, no build step
```

## Training dataset

After a scan, the backend exposes `GET /export` and can also generate a
fine-tuning-ready chat dataset directly from a saved export:

```bash
cd backend
python generate_dataset.py --graph graph_export.json --output orion_dataset_sft.jsonl
```

This writes the full dataset plus deterministic 90/10 train and validation
splits. Each JSONL record uses the standard `messages` array (system, user
with graph context, assistant answer), so it can be passed to an SFT validator
or uploaded to Microsoft Foundry/OpenAI. Use `--repo` to scan a repository
inline, or `--graph-dir` for multiple exports. `--paraphrase` is optional and
requires `anthropic` plus `ANTHROPIC_API_KEY`.

## Tests

The suites under `backend/tests/` need **no third-party packages** — the modules
they cover deliberately avoid them — so they run in a bare interpreter:

```bash
cd backend
python -m unittest discover -s tests -v
```

They cover search ranking, path-safety containment (including symlink escape),
and a guard on API route ordering. That last one exists because
`{qualified_name:path}` compiles to a regex that matches slashes: registered
before `/impact`, the catch-all swallows `/symbol/a.b.c/impact` and impact
analysis silently 404s. The specific route must stay above the catch-all.

## Roadmap

- **Interactive visual graph** — render the neighbourhood of a symbol as a real
  node/edge web with pan, zoom and click-to-expand, instead of side-by-side lists.
- **Persistent graph storage** — serialise to SQLite so restarts and large
  repositories do not force a rescan.
- **Multi-language support** — this means *introducing* Tree-sitter and a
  per-language extractor abstraction behind the current `ast` walkers, not
  extending an existing one. It is the largest item here, not an incremental step.
- **Retrieval + agent layer** — expose the graph as tools an LLM can call
  (`search_symbols`, `impact_of`, `path_between`, …) so the structural model
  becomes an interactive engineering assistant you can simply ask questions.
