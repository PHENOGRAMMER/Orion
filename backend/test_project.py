"""
Generic project scanner test.

Usage
-----

python backend/test_project.py <project_path>

Example
-------

python backend/test_project.py ../HeartDisease
python backend/test_project.py .
"""

from pathlib import Path
import sys

from app.scanner.scanner import ProjectScanner


def main() -> None:

    if len(sys.argv) != 2:
        print("Usage:")
        print("python backend/test_project.py <project_path>")
        return

    project = Path(sys.argv[1]).resolve()

    if not project.exists():
        print(f"Project does not exist: {project}")
        return

    scanner = ProjectScanner()

    print("=" * 80)
    print("Scanning Project")
    print("=" * 80)
    print(project)

    scan_result, index = scanner.scan(project)

    #
    # Statistics
    #

    print("\n" + "=" * 80)
    print("Statistics")
    print("=" * 80)

    print(scan_result.statistics)

    #
    # Languages
    #

    print("\n" + "=" * 80)
    print("Languages")
    print("=" * 80)

    for language, count in sorted(
        scan_result.language_statistics.languages.items()
    ):
        print(f"{language:<20} {count}")

    #
    # Frameworks
    #

    print("\n" + "=" * 80)
    print("Frameworks")
    print("=" * 80)

    print(scan_result.framework_statistics)

    #
    # Git
    #

    print("\n" + "=" * 80)
    print("Git")
    print("=" * 80)

    print(scan_result.git_statistics)

    #
    # Source Roots
    #

    print("\n" + "=" * 80)
    print("Source Roots")
    print("=" * 80)

    for root in index.source_roots:

        print(f"\n{root.path}")

        print(f"  Score     : {root.score}")
        print(f"  Language  : {root.language}")

        if root.reason:
            print("  Reasons:")
            for reason in root.reason:
                print(f"    - {reason}")

    #
    # Module Index
    #

    print("\n" + "=" * 80)
    print("Module Index")
    print("=" * 80)

    if index.module_index:

        for module in sorted(index.module_index):

            print(f"{module:<45} -> {index.module_index[module]}")

    else:

        print("No Python modules detected.")

    #
    # Dependency Graph
    #

    print("\n" + "=" * 80)
    print("Dependency Graph")
    print("=" * 80)

    if scan_result.dependency_graph.nodes:

        for dependency in sorted(scan_result.dependency_graph.nodes):

            node = scan_result.dependency_graph.nodes[dependency]

            print(f"\n{node.file}")

            if node.imports:

                for imp in sorted(node.imports):
                    print(f"   -> {imp}")

            else:

                print("   (no imports)")

    else:

        print("No dependency information.")

    #
    # Symbol Summary
    #

    print("\n" + "=" * 80)
    print("Symbols")
    print("=" * 80)

    if scan_result.symbol_graph.files:

        for filename in sorted(scan_result.symbol_graph.files):

            symbols = scan_result.symbol_graph.files[filename]

            print(f"\n{filename}")

            print(f"  Imports   : {len(symbols.imports)}")
            print(f"  Classes   : {len(symbols.classes)}")
            print(f"  Functions : {len(symbols.functions)}")
            print(f"  Variables : {len(symbols.variables)}")

    else:

        print("No symbols extracted.")

    print("\n" + "=" * 80)
    print("Scan Completed")
    print("=" * 80)


if __name__ == "__main__":
    main()