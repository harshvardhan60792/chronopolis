import pytest
import os
from citygen.parsers import backend_name
from citygen.parsers.treesitter import get_metrics

def test_backend_selection():
    # Make sure we're on tree-sitter when extras are installed
    if os.environ.get("CITYGEN_PARSER") != "builtin":
        assert backend_name() == "tree-sitter"
        
def test_java_functions_count():
    # 20 sampled files from gson (commit 556557)
    # Hand-counted functions (method_declaration + constructor_declaration)
    # Annotations typically have 0 functions since they have properties, not methods.
    
    samples = {
        "com/google/gson/stream/JsonScope.java": 1,
        "com/google/gson/JsonNull.java": 4,
        "com/google/gson/FieldNamingPolicy.java": 9,
        "com/google/gson/annotations/Since.java": 0,
        "com/google/gson/annotations/Expose.java": 0,
        "com/google/gson/ToNumberStrategy.java": 1,
        "com/google/gson/JsonParser.java": 7,
        "com/google/gson/JsonIOException.java": 3,
        "com/google/gson/internal/bind/TreeTypeAdapter.java": 14,
        "com/google/gson/JsonDeserializer.java": 1,
        "com/google/gson/internal/sql/SqlTimestampTypeAdapter.java": 4,
        "com/google/gson/internal/bind/ArrayTypeAdapter.java": 4,
        "com/google/gson/FieldNamingStrategy.java": 2,
        "com/google/gson/ToNumberPolicy.java": 5,
        "com/google/gson/TypeAdapter.java": 13,
        "com/google/gson/internal/bind/MapTypeAdapterFactory.java": 7,
        "com/google/gson/internal/sql/SqlTypesSupport.java": 3,
        "com/google/gson/internal/bind/TypeAdapters.java": 89,
        "com/google/gson/ReflectionAccessFilter.java": 9,
        "com/google/gson/stream/JsonWriter.java": 39,
    }
    
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".testrepos", "gson", "gson", "src", "main", "java")
    
    if not os.path.exists(base_dir):
        pytest.skip("gson test fixture not cloned")
        
    for path, expected_count in samples.items():
        full_path = os.path.join(base_dir, os.path.normpath(path))
        with open(full_path, "r", encoding="utf-8") as f:
            text = f.read()
            
        res = get_metrics("java", text)
        assert res is not None
        assert res.functions == expected_count, f"Mismatch in {path}: expected {expected_count}, got {res.functions}"

if __name__ == "__main__":
    pytest.main([__file__])
