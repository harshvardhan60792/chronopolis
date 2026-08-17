import os
import time
from dataclasses import dataclass
from typing import Any

import tree_sitter

@dataclass
class Result:
    functions: int = 0
    classes: int = 0
    complexity: int = 1
    max_fn_complexity: int = 0
    imports: list[Any] = None
    calls: list[str] = None
    def_names: list[str] = None

    def __post_init__(self):
        if self.imports is None:
            self.imports = []
        if self.calls is None:
            self.calls = []
        if self.def_names is None:
            self.def_names = []

_PARSERS = {}
_QUERIES = {}

def get_language(lang_name: str) -> tree_sitter.Language | None:
    ts_name_map = {
        "python": "tree_sitter_python",
        "java": "tree_sitter_java",
        "csharp": "tree_sitter_c_sharp",
        "cpp": "tree_sitter_cpp",
        "c": "tree_sitter_c",
        "javascript": "tree_sitter_javascript",
        "typescript": "tree_sitter_typescript",
        "go": "tree_sitter_go",
        "ruby": "tree_sitter_ruby",
        "php": "tree_sitter_php",
        "kotlin": "tree_sitter_kotlin",
        "swift": "tree_sitter_swift",
        "rust": "tree_sitter_rust",
    }
    
    module_name = ts_name_map.get(lang_name.lower())
    if not module_name:
        return None
        
    try:
        import importlib
        mod = importlib.import_module(module_name)
        return tree_sitter.Language(mod.language())
    except Exception:
        return None

def get_parser(lang_name: str) -> tree_sitter.Parser | None:
    if lang_name in _PARSERS:
        return _PARSERS[lang_name]
        
    lang = get_language(lang_name)
    if not lang:
        return None
        
    parser = tree_sitter.Parser(lang)
    _PARSERS[lang_name] = parser
    return parser

def get_query(lang_name: str, lang: tree_sitter.Language) -> tree_sitter.Query | None:
    if lang_name in _QUERIES:
        return _QUERIES[lang_name]
        
    queries_dir = os.path.join(os.path.dirname(__file__), "queries")
    query_file = os.path.join(queries_dir, f"{lang_name.lower()}.scm")
    if not os.path.exists(query_file):
        return None
        
    with open(query_file, "r", encoding="utf-8") as f:
        query_text = f.read()
        
    try:
        query = tree_sitter.Query(lang, query_text)
        _QUERIES[lang_name] = query
        return query
    except Exception as e:
        print(f"Query load error for {lang_name}: {e}")
        return None

def get_metrics(lang_name: str, text: str) -> Result | None:
    lang = get_language(lang_name)
    if not lang:
        return None
        
    parser = get_parser(lang_name)
    if not parser:
        return None
        
    query = get_query(lang_name, lang)
    if not query:
        return None
        
    try:
        # Avoid crashing on syntax errors, tree-sitter recovers
        tree = parser.parse(text.encode("utf-8"))
    except Exception:
        return None
        
    cursor = tree_sitter.QueryCursor(query)
    captures = cursor.captures(tree.root_node)
    
    functions = 0
    classes = 0
    complexity = 1
    
    # Map from node ID to its complexity
    func_complexity = {}
    imports = []
    calls = []
    def_names = []
    
    # First pass: functions, classes, imports, calls
    for capture_name, nodes in captures.items():
        if capture_name == "function":
            functions += len(nodes)
            for node in nodes:
                func_complexity[node.id] = 1
                name_node = node.child_by_field_name("name") or node.child_by_field_name("declarator")
                if name_node:
                    def_names.append(name_node.text.decode("utf-8", errors="replace"))
        elif capture_name == "class":
            classes += len(nodes)
            for node in nodes:
                name_node = node.child_by_field_name("name")
                if name_node:
                    def_names.append(name_node.text.decode("utf-8", errors="replace"))
        elif capture_name == "import":
            for node in nodes:
                imports.append(node.text.decode("utf-8", errors="replace").strip("\"'"))
        elif capture_name == "call":
            for node in nodes:
                callee_node = node.child_by_field_name("function") or node.child_by_field_name("name") or node.child_by_field_name("type")
                if callee_node:
                    calls.append(callee_node.text.decode("utf-8", errors="replace"))
                else:
                    if node.children:
                        calls.append(node.children[0].text.decode("utf-8", errors="replace"))
                
    # Second pass: decision points (complexity)
    for capture_name, nodes in captures.items():
        if capture_name == "decision":
            complexity += len(nodes)
            for node in nodes:
                curr = node
                while curr is not None:
                    if curr.id in func_complexity:
                        func_complexity[curr.id] += 1
                        break
                    curr = curr.parent
            
    max_fn_cx = max(func_complexity.values()) if func_complexity else 0
    
    return Result(
        functions=functions,
        classes=classes,
        complexity=complexity,
        max_fn_complexity=max_fn_cx,
        imports=imports,
        calls=calls,
        def_names=def_names
    )
