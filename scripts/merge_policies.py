import json
import os

def load_policies():
    with open("config/policies.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_policies(data):
    with open("config/policies.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def merge_and_deduplicate():
    data = load_policies()
    policies = data.get("政策", [])
    
    # 用 (省份, 城市, 政策名称) 作为去重键
    seen = set()
    unique = []
    for p in policies:
        key = (p.get("省份", ""), p.get("城市", ""), p.get("政策名称", ""))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    
    data["政策"] = unique
    save_policies(data)
    print(f"✅ 去重完成，共 {len(unique)} 条政策")

if __name__ == "__main__":
    merge_and_deduplicate()
