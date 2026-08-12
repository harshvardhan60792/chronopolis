"""Resolve Python import statements to in-repo file paths.

Only intra-repo edges become roads in the city. Third-party imports are kept
as an aggregate count per building (`ext_imports`) so the "how much does this
file lean on the outside world" signal is not lost.
"""

from __future__ import annotations

import os


class ModuleIndex:
    """Maps dotted module names -> repo-relative file paths.

    Handles both layouts found in the wild:
      * flat / src-less:      pkg/mod.py            -> "pkg.mod"
      * src-layout:           src/pkg/mod.py        -> "pkg.mod" and "src.pkg.mod"
    A package directory containing __init__.py also maps its own dotted name.
    """

    ROOT_PREFIXES = ("src/", "lib/", "python/")

    def __init__(self, py_paths: list[str]):
        self.by_module: dict[str, str] = {}
        self.packages: set[str] = set()
        self.paths = set(py_paths)

        for p in py_paths:
            for variant in self._name_variants(p):
                # first writer wins, and paths are pre-sorted => deterministic
                self.by_module.setdefault(variant, p)

        for p in py_paths:
            if p.endswith("/__init__.py") or p == "__init__.py":
                pkg_dir = p[: -len("__init__.py")].rstrip("/")
                for variant in self._dir_variants(pkg_dir):
                    self.packages.add(variant)
                    self.by_module.setdefault(variant, p)

    def _strip_roots(self, rel: str) -> list[str]:
        out = [rel]
        for pref in self.ROOT_PREFIXES:
            if rel.startswith(pref):
                out.append(rel[len(pref):])
        return out

    def _name_variants(self, rel: str) -> list[str]:
        names = []
        for r in self._strip_roots(rel):
            noext = r[:-3] if r.endswith(".py") else r
            if noext.endswith("/__init__"):
                noext = noext[: -len("/__init__")]
            if noext:
                names.append(noext.replace("/", "."))
        return names

    def _dir_variants(self, d: str) -> list[str]:
        if not d:
            return []
        return [r.replace("/", ".") for r in self._strip_roots(d) if r]

    def resolve(self, module: str, level: int, from_file: str) -> str | None:
        """Return the repo file implementing `module`, or None if external."""
        if level and level > 0:
            base = os.path.dirname(from_file)
            for _ in range(level - 1):
                base = os.path.dirname(base)
            dotted = base.replace("/", ".")
            module = f"{dotted}.{module}" if module and dotted else (module or dotted)
            if not module:
                return None
            hit = self.by_module.get(module)
            if hit:
                return hit
            # `from . import x` / `from .pkg import mod` -> try package __init__
            return self.by_module.get(module.rsplit(".", 1)[0])

        if not module:
            return None
        hit = self.by_module.get(module)
        if hit:
            return hit
        # `from a.b import c` where c is itself a module
        if "." in module:
            return self.by_module.get(module.rsplit(".", 1)[0])
        return None

    def resolve_symbol(self, module: str, level: int, symbol: str,
                       from_file: str) -> str | None:
        """`from pkg import mod` - the symbol may itself be a submodule."""
        if module or level:
            joined = f"{module}.{symbol}" if module else symbol
            hit = self.resolve(joined, level, from_file)
            if hit:
                return hit
        return None
