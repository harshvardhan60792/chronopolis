import sys
import tree_sitter
import importlib
import os

try:
    mod = importlib.import_module('tree_sitter_java')
    lang = tree_sitter.Language(mod.language())
    parser = tree_sitter.Parser(lang)
    tree = parser.parse(b"class A { void M() { foo(1); new A(); } }")
    print("Java:", tree.root_node.sexp())

    mod = importlib.import_module('tree_sitter_python')
    lang = tree_sitter.Language(mod.language())
    parser = tree_sitter.Parser(lang)
    tree = parser.parse(b"def f():\n  foo(1)\n  A()")
    print("Python:", tree.root_node.sexp())

    mod = importlib.import_module('tree_sitter_cpp')
    lang = tree_sitter.Language(mod.language())
    parser = tree_sitter.Parser(lang)
    tree = parser.parse(b"void M() { foo(1); new A(); }")
    print("Cpp:", tree.root_node.sexp())

except Exception as e:
    print(e)
