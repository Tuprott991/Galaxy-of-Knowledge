import os
import json

folder = "data/PMC_articles_json"

for filename in os.listdir(folder):
    if filename.endswith(".json"):
        filepath = os.path.join(folder, filename)
        file_id = os.path.splitext(filename)[0]  # lấy phần tên file (số)

        # đảm bảo là số
        try:
            file_id = int(file_id)
        except ValueError:
            continue

        # đọc file JSON
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # thêm key "ID"
        data["ID"] = file_id

        # ghi lại file JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

print("✅ Đã thêm key 'ID' cho tất cả file JSON.")
