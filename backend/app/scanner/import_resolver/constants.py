"""
Constants used by the Import Resolver.
"""

from __future__ import annotations

#
# Symbol kinds
#

CLASS_SYMBOL = "class"

FUNCTION_SYMBOL = "function"

METHOD_SYMBOL = "method"

VARIABLE_SYMBOL = "variable"

MODULE_SYMBOL = "module"

UNKNOWN_SYMBOL = "unknown"

#
# Resolver settings
#

RESOLVE_RELATIVE_IMPORTS = True

RESOLVE_BUILTIN_MODULES = False

RESOLVE_THIRD_PARTY_MODULES = False

#
# Future caching
#

ENABLE_CACHE = True

#
# Supported package initializers
#

PACKAGE_INIT_FILES = {
    "__init__.py",
}

#
# Module separators
#

MODULE_SEPARATOR = "."