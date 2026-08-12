"""Per-file metrics.

Two tiers:
  * `generic_metrics` - works on any text file (LOC, SLOC, TODOs).
  * `python_metrics`  - AST-based: functions, classes, complexity, imports.

Complexity is a decision-point count, not McCabe from a control-flow graph.
It is within a few percent of McCabe on real code, needs no dependency, and is
what the building height is derived from. See docs/04-DECISIONS.md ADR-004.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field

TODO_MARKERS = ("TODO", "FIXME", "HACK", "XXX")

BRANCH_NODES = (
    ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
    ast.With, ast.AsyncWith, ast.Assert, ast.IfExp, ast.comprehension,
)


@dataclass
class FuncRec:
    name: str
    qualname: str
    lineno: int
    end_lineno: int
    complexity: int
    args: int
    is_async: bool
    is_method: bool


@dataclass
class PyResult:
    ok: bool
    functions: list[FuncRec] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    complexity: int = 1
    max_func_complexity: int = 0
    # (module, level, symbols) - symbols matter because `from . import x` and
    # `from pkg import mod` name a *module* in the symbol slot, not an object.
    imports: list[tuple[str, int, tuple[str, ...]]] = field(default_factory=list)
    import_symbols: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)   # dotted callee names, raw
    doc_lines: int = 0
    error: str | None = None


def generic_metrics(text: str) -> dict:
    lines = text.splitlines()
    loc = len(lines)
    sloc = 0
    todos = 0
    for ln in lines:
        s = ln.strip()
        if s:
            sloc += 1
        if any(m in ln for m in TODO_MARKERS):
            todos += 1
    longest = max((len(l) for l in lines), default=0)
    return {"loc": loc, "sloc": sloc, "todo": todos, "max_line": longest}


def _node_complexity(node: ast.AST) -> int:
    """Decision points inside `node`, not descending into nested functions."""
    score = 0
    stack = list(ast.iter_child_nodes(node))
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue  # nested defs are counted as their own units
        if isinstance(n, BRANCH_NODES):
            score += 1
        elif isinstance(n, ast.BoolOp):
            score += max(0, len(n.values) - 1)
        elif hasattr(ast, "Match") and isinstance(n, ast.Match):
            score += max(0, len(n.cases) - 1)
        stack.extend(ast.iter_child_nodes(n))
    return score


def python_metrics(text: str, path: str = "<src>") -> PyResult:
    try:
        tree = ast.parse(text, filename=path)
    except (SyntaxError, ValueError, RecursionError) as exc:
        return PyResult(ok=False, error=f"{type(exc).__name__}: {exc}")

    res = PyResult(ok=True)
    mod_doc = ast.get_docstring(tree)
    if mod_doc:
        res.doc_lines += mod_doc.count("\n") + 1

    def visit(node: ast.AST, prefix: str, in_class: bool) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qn = f"{prefix}{child.name}"
                cx = 1 + _node_complexity(child)
                a = child.args
                nargs = (len(a.posonlyargs) + len(a.args) + len(a.kwonlyargs)
                         + (1 if a.vararg else 0) + (1 if a.kwarg else 0))
                res.functions.append(FuncRec(
                    name=child.name, qualname=qn, lineno=child.lineno,
                    end_lineno=getattr(child, "end_lineno", child.lineno),
                    complexity=cx, args=nargs,
                    is_async=isinstance(child, ast.AsyncFunctionDef),
                    is_method=in_class,
                ))
                d = ast.get_docstring(child)
                if d:
                    res.doc_lines += d.count("\n") + 1
                visit(child, qn + ".", False)
            elif isinstance(child, ast.ClassDef):
                qn = f"{prefix}{child.name}"
                res.classes.append(qn)
                d = ast.get_docstring(child)
                if d:
                    res.doc_lines += d.count("\n") + 1
                visit(child, qn + ".", True)
            else:
                visit(child, prefix, in_class)

    visit(tree, "", False)

    # Module-level complexity: decision points not inside any def/class.
    res.complexity = 1 + _node_complexity(tree) + sum(f.complexity for f in res.functions)
    res.max_func_complexity = max((f.complexity for f in res.functions), default=0)

    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for alias in n.names:
                res.imports.append((alias.name, 0, ()))
        elif isinstance(n, ast.ImportFrom):
            syms = tuple(a.name for a in n.names)
            res.imports.append((n.module or "", n.level or 0, syms))
            res.import_symbols.extend(syms)
        elif isinstance(n, ast.Call):
            res.calls.append(_callee_name(n.func))

    res.calls = [c for c in res.calls if c]
    return res


def _callee_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _callee_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""
