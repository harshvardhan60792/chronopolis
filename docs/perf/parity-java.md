# Parser Parity Diff: java on .testrepos/gson/gson

## Summary
- **Files**: 210
- **Complexity correlation**: r = 0.9167
- **Mean Absolute Difference (MAD)**:
  - Functions: 14.57
  - Classes: 3.00
  - Complexity: 7.45
  - Imports: 10.51

## Top 20 Largest Divergences
| File | fn (ts-b) | cl (ts-b) | cx (ts-b) | im (ts-b) |
|---|---|---|---|---|
| `src/main/java/com/google/gson/Gson.java` | 40-0 | 2-0 | 49-225 | 28-0 |
| `src/main/java/com/google/gson/stream/JsonReader.java` | 47-0 | 1-0 | 245-422 | 10-0 |
| `src/test/java/com/google/gson/stream/JsonReaderTest.java` | 162-0 | 1-0 | 21-42 | 19-0 |
| `src/test/java/com/google/gson/functional/DefaultTypeAdaptersTest.java` | 101-0 | 6-0 | 10-20 | 62-0 |
| `src/main/java/com/google/gson/GsonBuilder.java` | 40-0 | 1-0 | 38-111 | 36-0 |
| `src/test/java/com/google/gson/functional/JsonAdapterAnnotationOnClassesTest.java` | 67-0 | 30-0 | 4-22 | 24-0 |
| `src/test/java/com/google/gson/functional/JsonAdapterAnnotationOnFieldsTest.java` | 71-0 | 32-0 | 3-12 | 24-0 |
| `src/main/java/com/google/gson/internal/bind/TypeAdapters.java` | 89-0 | 5-0 | 101-99 | 38-0 |
| `src/test/java/com/google/gson/functional/PrimitiveTest.java` | 108-0 | 2-0 | 1-6 | 17-0 |
| `src/test/java/com/google/gson/functional/ObjectTest.java` | 59-0 | 21-0 | 7-12 | 38-0 |
| `src/test/java/com/google/gson/functional/MapTest.java` | 67-0 | 8-0 | 5-12 | 36-0 |
| `src/main/java/com/google/gson/internal/bind/ReflectiveTypeAdapterFactory.java` | 34-0 | 6-0 | 60-89 | 39-0 |
| `src/test/java/com/google/gson/GsonTest.java` | 49-0 | 11-0 | 9-32 | 15-0 |
| `src/test/java/com/google/gson/functional/Java17RecordTest.java` | 34-0 | 24-0 | 2-13 | 26-0 |
| `src/test/java/com/google/gson/functional/ReflectionAccessFilterTest.java` | 34-0 | 10-0 | 8-31 | 27-0 |
| `src/main/java/com/google/gson/JsonElement.java` | 23-0 | 1-0 | 6-68 | 6-0 |
| `src/main/java/com/google/gson/stream/JsonWriter.java` | 39-0 | 1-0 | 64-94 | 21-0 |
| `src/main/java/com/google/gson/JsonArray.java` | 33-0 | 1-0 | 12-58 | 7-0 |
| `src/test/java/com/google/gson/common/TestTypes.java` | 47-0 | 22-0 | 18-19 | 12-0 |
| `src/test/java/com/google/gson/functional/CollectionTest.java` | 40-0 | 7-0 | 11-14 | 30-0 |