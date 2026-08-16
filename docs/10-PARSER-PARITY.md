# Parser Parity Report

This document compares the new tree-sitter based parsing against the existing heuristic (regex/ast) parsing for Python and Java.

## Java

**Verdict**: `tree-sitter: adopt`

### Fixture Pass Rate
- **Tree-sitter**: 19/20 (95%)
- **Regex (Builtin)**: 0/20 (0%)

The builtin regex for Java deliberately does not attempt to count functions or classes (always returns 0) because identifying Java methods via regex without massive over-counting is impossible. The one fixture where tree-sitter did not perfectly match the hand-counted expectation was `13_switch_statement.java`, because tree-sitter found a decision node we had under-counted in our expectation (it correctly caught it).

### Real Repo Divergence (Gson)
When run against `.testrepos/gson/gson` (210 files):
- **Complexity correlation**: r = 0.9167
- **Mean Absolute Difference (MAD)**:
  - Functions: 14.57
  - Classes: 3.00
  - Complexity: 7.45
  - Imports: 10.51

### Where Regex is Wrong
Regex cannot handle nested structures or strings gracefully. For example, in a string literal containing code-like text:
```java
class A { String s = "if (x) { function_shaped() }"; }
```
The regex incorrectly counts `if` inside the string literal as a decision point (complexity). 

Additionally, because regex does not parse syntax trees, it cannot count functions or classes at all in Java, meaning these metrics are completely blind in the regex backend.

### Where Tree-sitter is Wrong or Worse
Tree-sitter doesn't natively treat anonymous classes as standalone "classes" unless explicitly captured by `object_creation_expression` and disambiguated. In our basic query, we use `class_declaration`, so a `Runnable r = new Runnable() {}` does not increment the class count. However, this is largely a design choice of what constitutes a "building" in the city, rather than a failure of the parser.

## Python

**Verdict**: `tree-sitter: adopt`

### Fixture Pass Rate
- **Tree-sitter**: 19/20 (95%)
- **AST (Builtin)**: 11/20 (55%)

### Real Repo Divergence (Citygen)
When run against `citygen` itself (34 files):
- **Complexity correlation**: r = 0.9871
- **Mean Absolute Difference (MAD)**:
  - Functions: 0.00
  - Classes: 0.00
  - Complexity: 10.53
  - Imports: 0.32

The agreement on functions and classes is exact.

### Where AST/Regex is Wrong
The `ast` module fails entirely on files containing syntax errors. When given:
```python
class A:
    def b():
        if c:
            d()
        synt@x err0r
```
The `ast` parser crashes and returns the default fallback (0 functions, 0 classes). 

### Where Tree-sitter is Wrong or Worse
Tree-sitter is significantly better at recovering from syntax errors. In the syntax error case, tree-sitter correctly extracts the `class A`, `def b()`, and the `if` decision point, accurately portraying the file's structure prior to the syntax error.
One area where tree-sitter initially fell behind was comprehensions, which require explicit capturing (`list_comprehension`, etc.) to match the AST's implicit visitation, but we added those.
Currently, the AST parser over-counts `match` statements by counting `len(cases) - 1` plus the `Match` node itself, leading to slight numeric differences in complexity, but they correlate at > 0.98.
