import os
import json

PMC_DIR = "data/PMC_articles_json"
LINKS_DIR = "data/pubmed_links_json"

def load_json_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def merge_unique(existing_list, new_list, current_pmid):
    """Thêm các item từ new_list vào existing_list mà không trùng PMID, và bỏ qua bài báo gốc"""
    existing_pmids = {item["PMID"] for item in existing_list}
    for item in new_list:
        pmid = item.get("PMID")
        if pmid and pmid != current_pmid and pmid not in existing_pmids:
            existing_list.append(item)
            existing_pmids.add(pmid)
    return existing_list

def main():
    json_files = [f for f in os.listdir(PMC_DIR) if f.endswith(".json")]
    for jf in json_files:
        pmc_path = os.path.join(PMC_DIR, jf)
        data = load_json_file(pmc_path)
        pmid = data.get("PMID")
        if not pmid:
            continue

        # Load cited_by và similar_to files nếu tồn tại
        cited_file = os.path.join(LINKS_DIR, f"{pmid}_cited.json")
        similar_file = os.path.join(LINKS_DIR, f"{pmid}_similar.json")

        cited_list = load_json_file(cited_file) if os.path.exists(cited_file) else []
        similar_list = load_json_file(similar_file) if os.path.exists(similar_file) else []

        # Khởi tạo các key nếu chưa tồn tại
        if "cited_by" not in data:
            data["cited_by"] = []
        if "similar_to" not in data:
            data["similar_to"] = []

        # Merge dữ liệu và loại trùng lặp, bỏ qua bài báo gốc
        data["cited_by"] = merge_unique(data["cited_by"], cited_list, pmid)
        data["similar_to"] = merge_unique(data["similar_to"], similar_list, pmid)

        # Lưu lại file JSON
        save_json_file(pmc_path, data)
        print(f"Updated {jf}: cited_by={len(data['cited_by'])}, similar_to={len(data['similar_to'])}")

if __name__ == "__main__":
    main()
