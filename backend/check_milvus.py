"""Check Milvus tool_usage collection."""
import json
from pymilvus import MilvusClient

client = MilvusClient(uri="http://localhost:19530")

# Schema
fields_desc = client.describe_collection("tool_usage")
print("=== Schema ===")
for f in fields_desc["fields"]:
    print(f"  {f['name']}: {f['type']}")

# Stats
stats = client.get_collection_stats("tool_usage")
print(f"\n=== Stats ===")
print(f"Total rows: {stats.get('row_count')}")

# All records
res = client.query(
    collection_name="tool_usage",
    filter="success == True",
    output_fields=["question", "tool_name", "tool_params", "username", "created_at"],
    limit=50,
)

print(f"\n=== All Records ({len(res)} rows) ===")
for i, r in enumerate(res):
    print(f"\n--- Record {i+1} ---")
    print(f"  Question: {r['question'][:80]}")
    print(f"  Tool:     {r['tool_name']}")
    print(f"  Params:   {r['tool_params'][:150]}")
    print(f"  User:     {r['username']}")
    print(f"  Time:     {r['created_at']}")
