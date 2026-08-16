import tree_sitter
import tree_sitter_java

p = tree_sitter.Parser(tree_sitter.Language(tree_sitter_java.language()))
tree = p.parse(b"class A { void b() { switch (x) { case 1: break; } } }")

def traverse(n):
    print(n.type)
    for c in n.children:
        traverse(c)

traverse(tree.root_node)
