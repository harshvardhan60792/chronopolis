import os
from dataclasses import dataclass
from typing import Any

_available = False
try:
    import tree_sitter
    _available = True
except ImportError:
    pass

def available() -> bool:
    """True if tree-sitter and the grammar bundle import cleanly."""
    return _available

def backend_name() -> str:
    """Return 'tree-sitter' or 'builtin'."""
    if os.environ.get("CITYGEN_PARSER") == "builtin":
        return "builtin"
    return "tree-sitter" if available() else "builtin"

def metrics_for(lang: str, text: str) -> Any | None:
    """None => caller falls back to the builtin regex/ast path."""
    if backend_name() == "builtin":
        return None
        
    # Python always uses builtin (ast)
    if lang == "Python":
        return None
        
    try:
        from .treesitter import get_metrics
        return get_metrics(lang, text)
    except Exception:
        # Fallback if any error occurs (e.g. grammar not found)
        return None
