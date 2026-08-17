import sys
import tree_sitter
import importlib
import os

sys.path.append(os.path.abspath('citygen/parsers'))
# just a quick way to test tree-sitter C#
try:
    mod = importlib.import_module('tree_sitter_c_sharp')
    lang = tree_sitter.Language(mod.language())
    parser = tree_sitter.Parser(lang)
    tree = parser.parse(b"class A { void M() { foo(1); new A(); } }")
    print(tree.root_node.sexp())
except Exception as e:
    print(e)
