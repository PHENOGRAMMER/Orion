"""
Test the SymbolIndexBuilder.
"""

from app.scanner.scanner import ProjectScanner
from app.scanner.symbol_index_builder import SymbolIndexBuilder


def main() -> None:

    scanner = ProjectScanner()

    result, _ = scanner.scan(".")

    builder = SymbolIndexBuilder()

    index = builder.build(result)

    print("\n" + "=" * 80)
    print("Project Symbol Index")
    print("=" * 80)

    print(f"\nTotal Symbols : {len(index.qualified_symbols)}")

    print("\n" + "=" * 80)
    print("Qualified Symbols")
    print("=" * 80)

    for qualified_name in sorted(index.qualified_symbols):

        symbol = index.qualified_symbols[qualified_name]

        print(f"\n{qualified_name}")
        print(f"  Type   : {symbol.symbol_type}")
        print(f"  Module : {symbol.module}")
        print(f"  File   : {symbol.path}")
        print(f"  Line   : {symbol.line}")

    print("\n" + "=" * 80)
    print("Duplicate Symbol Names")
    print("=" * 80)

    duplicates = False

    for name in sorted(index.symbols):

        symbols = index.lookup(name)

        if len(symbols) <= 1:
            continue

        duplicates = True

        print(f"\n{name}")

        for symbol in symbols:

            print(f"  -> {symbol.qualified_name}")

    if not duplicates:

        print("\nNo duplicate symbol names detected.")

    print("\n" + "=" * 80)
    print("Lookup Example")
    print("=" * 80)

    #
    # Change this to any symbol that exists
    #

    lookup_name = "ProjectScanner"

    results = index.lookup(lookup_name)

    print(f"\nLookup('{lookup_name}')")

    if not results:

        print("  No results.")

    else:

        for symbol in results:

            print(f"  {symbol.qualified_name}")
            print(f"    {symbol.path}:{symbol.line}")


if __name__ == "__main__":
    main()