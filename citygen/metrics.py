"""Per-file metrics.

Three tiers:
  * `generic_metrics` - works on any text file (LOC, SLOC, TODOs).
  * `python_metrics`  - AST-based: functions, classes, complexity, imports.
  * `js_metrics`      - regex-based: functions, classes, complexity, imports,
                        for JavaScript/TypeScript. Real parsing needs a real
                        parser; this is deliberately a heuristic (comments
                        and strings are not stripped, so a `// if (x)` in a
                        comment counts too) - good enough for the building
                        height/arcs signal, not a linter.

Complexity is a decision-point count, not McCabe from a control-flow graph.
It is within a few percent of McCabe on real code, needs no dependency, and is
what the building height is derived from. See docs/04-DECISIONS.md ADR-004.
"""

from __future__ import annotations

import ast
import re
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


@dataclass
class JsResult:
    functions: int = 0
    classes: int = 0
    complexity: int = 1
    # Raw import specifiers as written (e.g. "./foo", "../lib/bar", "react").
    # Resolving these to repo paths is resolve.py's job, same split as Python.
    imports: list[str] = field(default_factory=list)


# `function foo(` / `function*(` / anonymous `function(`.
_JS_FUNCTION_KEYWORD_RE = re.compile(r'\bfunction\s*\*?\s*[A-Za-z_$][\w$]*\s*\(|\bfunction\s*\*?\s*\(')
# `const foo = (...) =>` / `const foo = async x =>` - the two arrow shapes
# actually worth counting as a named unit. Bare inline arrows passed as
# callback arguments (`arr.map(x => x.id)`) are intentionally not counted -
# they are not "a function in this file" the way a top-level building wants.
_JS_ARROW_ASSIGN_RE = re.compile(
    r'\b(?:const|let|var)\s+[A-Za-z_$][\w$]*\s*=\s*(?:async\s+)?\(?[^=;{}\n]*\)?\s*=>'
)
_JS_CLASS_RE = re.compile(r'\bclass\s+[A-Za-z_$][\w$]*')
# Decision points: unambiguous keywords/operators only. Ternaries (`?:`) and
# `??` are skipped - too easily confused with TS optional chaining/typing
# for a regex to disambiguate safely.
_JS_DECISION_RE = re.compile(
    r'\b(?:if|for|while|catch|case)\b|&&|\|\|'
)

# import 'x'; import x from 'x'; import {a,b} from 'x'; import x, {a} from 'x'
_JS_IMPORT_RE = re.compile(r'''\bimport\s+(?:[\w${},\s*]+\s+from\s+)?['"]([^'"]+)['"]''')
# export {a} from 'x'; export * from 'x'
_JS_EXPORT_FROM_RE = re.compile(r'''\bexport\s+(?:[\w${},\s*]+|\*)\s+from\s+['"]([^'"]+)['"]''')
# require('x')
_JS_REQUIRE_RE = re.compile(r'''\brequire\(\s*['"]([^'"]+)['"]\s*\)''')
# import('x')  (dynamic import)
_JS_DYNAMIC_IMPORT_RE = re.compile(r'''\bimport\(\s*['"]([^'"]+)['"]\s*\)''')


def js_metrics(text: str) -> JsResult:
    functions = len(_JS_FUNCTION_KEYWORD_RE.findall(text)) + len(_JS_ARROW_ASSIGN_RE.findall(text))
    classes = len(_JS_CLASS_RE.findall(text))
    complexity = 1 + len(_JS_DECISION_RE.findall(text))
    imports = (
        _JS_IMPORT_RE.findall(text)
        + _JS_EXPORT_FROM_RE.findall(text)
        + _JS_REQUIRE_RE.findall(text)
        + _JS_DYNAMIC_IMPORT_RE.findall(text)
    )
    return JsResult(functions=functions, classes=classes, complexity=complexity, imports=imports)


@dataclass
class GoResult:
    functions: int = 0
    complexity: int = 1


# `func Name(` and `func (recv Type) Name(` - `func` is a reserved word in Go,
# so unlike the C-family below this is essentially unambiguous.
_GO_FUNC_RE = re.compile(r'\bfunc\s+(?:\([^)]*\)\s+)?[A-Za-z_]\w*\s*\(')
# Go has no `while` (folded into `for`) and no `catch` (folded into
# if err != nil, which a regex cannot see) - `select`/`case` cover its
# concurrency branching instead.
_GO_DECISION_RE = re.compile(r'\b(?:if|for|switch|select|case)\b|&&|\|\|')


def go_metrics(text: str) -> GoResult:
    functions = len(_GO_FUNC_RE.findall(text))
    complexity = 1 + len(_GO_DECISION_RE.findall(text))
    return GoResult(functions=functions, complexity=complexity)


# Decision-point counter shared by the C-family languages (Java, C#, C/C++,
# PHP, Kotlin, Swift, Rust). Deliberately complexity-only: unlike `function`
# in JS or `func` in Go, none of these languages has a reserved word marking
# a function/method declaration, so a regex cannot reliably count them
# without either missing most methods or matching every `if (...) {` too -
# better to leave functions at 0 (visibly "unknown") than ship a number that
# looks precise and is not. Decision keywords, by contrast, are reserved
# words in all of these languages, so counting them carries the same
# confidence as the Go/JS complexity counts.
_CURLY_DECISION_RE = re.compile(
    r'\b(?:if|for|while|switch|case|catch|match)\b|&&|\|\|'
)


def curly_complexity(text: str) -> int:
    return 1 + len(_CURLY_DECISION_RE.findall(text))


@dataclass
class RubyResult:
    functions: int = 0
    classes: int = 0
    complexity: int = 1
    # (spec, is_relative). `require_relative` is always a same-repo path;
    # plain `require` is usually a gem, but idiomatic Ruby also uses it for
    # intra-project files reachable via a lib/app load-path root, so it is
    # still worth an attempted resolution - same split resolve.py makes.
    imports: list[tuple[str, bool]] = field(default_factory=list)


# `def name`, `def self.name`, `def name?`/`name!`/`name=` - `def` is a
# reserved word, so (like Go's `func`) this is a reliable method count.
_RUBY_DEF_RE = re.compile(r'\bdef\s+(?:self\.)?[A-Za-z_]\w*[?!=]?')
_RUBY_CLASS_RE = re.compile(r'\b(?:class|module)\s+[A-Za-z_][\w:]*')
# Ruby has no braces, so `if`/`unless`/`while`/`until` etc. are themselves
# the block delimiters, not just a heuristic proxy for one.
_RUBY_DECISION_RE = re.compile(
    r'\b(?:if|elsif|unless|while|until|case|when|rescue|and|or)\b|&&|\|\|'
)
_RUBY_REQUIRE_RELATIVE_RE = re.compile(r'''\brequire_relative\s+['"]([^'"]+)['"]''')
# Deliberately after the relative regex and written so it cannot also match
# inside "require_relative" (no whitespace follows "require" there).
_RUBY_REQUIRE_RE = re.compile(r'''\brequire\s+['"]([^'"]+)['"]''')


def ruby_metrics(text: str) -> RubyResult:
    functions = len(_RUBY_DEF_RE.findall(text))
    classes = len(_RUBY_CLASS_RE.findall(text))
    complexity = 1 + len(_RUBY_DECISION_RE.findall(text))
    imports = [(m, True) for m in _RUBY_REQUIRE_RELATIVE_RE.findall(text)]
    imports += [(m, False) for m in _RUBY_REQUIRE_RE.findall(text)]
    return RubyResult(functions=functions, classes=classes, complexity=complexity, imports=imports)
