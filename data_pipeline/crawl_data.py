# import asyncio
# import json
# import re
# import os
# import csv
# from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
# from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy


# def extract_main_content_with_metadata(md_text: str):
#     lines = md_text.split("\n")
#     start_idx, end_idx = None, None

#     # Tìm Abstract
#     for i, line in enumerate(lines):
#         if re.search(r"#+\s*abstract", line, re.IGNORECASE):
#             start_idx = i
#             break

#     metadata_lines = lines[:start_idx] if start_idx is not None else []

#     # Tìm References
#     for i, line in enumerate(lines):
#         if start_idx is not None and re.search(r"#+\s*references", line, re.IGNORECASE):
#             end_idx_ref = len(lines) - 1
#             for j in range(i + 1, len(lines)):
#                 if re.match(r"#+\s+", lines[j]) or re.match(r"^\*\s+", lines[j]) or re.match(r"^-{3,}$", lines[j]):
#                     end_idx_ref = j - 1
#                     break
#             end_idx = end_idx_ref
#             break

#     if start_idx is not None:
#         main_lines = lines[start_idx:end_idx + 1] if end_idx is not None else lines[start_idx:]
#     else:
#         main_lines = lines

#     metadata_text = "\n".join(metadata_lines).strip()
#     main_text = "\n".join(main_lines).strip()
#     return metadata_text, main_text


# def parse_references(raw_text: str):
#     refs = []
#     for line in raw_text.split("\n"):
#         line = line.strip()
#         if not line:
#             continue
#         m = re.match(r"^\*?\s*(\d+)\.\s*(.*)", line)
#         if m:
#             refs.append({"id": int(m.group(1)), "text": m.group(2)})
#         elif line.startswith("* "):
#             refs.append({"text": line[2:].strip()})
#         else:
#             if refs:
#                 refs[-1]["text"] += " " + line
#             else:
#                 refs.append({"text": line})
#     return refs


# def parse_metadata(metadata_text: str):
#     """
#     Trích xuất:
#     - Authors: list các dict { "name": ..., "link": ... }
#       Chỉ lấy link chứa [Author] (%5BAuthor%5D)
#     - PMCID: ví dụ 'PMC4136787'
#     - PMID: ví dụ '25133741'
#     """
#     authors = []
#     seen = set()

#     # Tìm tất cả Markdown link [Tên](link)
#     matches = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", metadata_text)

#     for name, link in matches:
#         if "pubmed.ncbi.nlm.nih.gov" in link and "%5BAuthor%5D" in link:
#             key = (name, link)
#             if key not in seen:
#                 authors.append({"name": name, "link": link})
#                 seen.add(key)

#     # tìm PMCID
#     pmc_id_match = re.search(r"PMCID:\s*(PMC\d+)", metadata_text)
#     pmc_id = pmc_id_match.group(1) if pmc_id_match else None

#     # tìm PMID
#     pmid_match = re.search(r"PMID:\s*\[?(\d+)\]?", metadata_text)
#     pmid = pmid_match.group(1) if pmid_match else None

#     return {"Authors": authors, "ID": pmc_id, "PMID": pmid}





# def build_nested_structure(md_text: str):
#     root = {}
#     stack = [(0, root)]

#     for line in md_text.split("\n"):
#         m = re.match(r"^(#+)\s+(.*)", line)
#         if m:
#             level = len(m.group(1))
#             title = m.group(2).strip().lower()
#             while stack and stack[-1][0] >= level:
#                 stack.pop()
#             parent = stack[-1][1]
#             parent[title] = {}
#             stack.append((level, parent[title]))
#         else:
#             if stack:
#                 node = stack[-1][1]
#                 node.setdefault("_content", []).append(line)

#     def clean(node):
#         for k, v in list(node.items()):
#             if isinstance(v, dict):
#                 clean(v)
#             elif isinstance(v, list):
#                 node[k] = "\n".join(v).strip()
#         if "references" in node and "_content" in node["references"]:
#             node["references"] = parse_references(node["references"]["_content"])

#     clean(root)
#     return root


# async def crawl_all_from_csv(csv_file, output_dir):
#     rows = []
#     with open(csv_file, newline="", encoding="utf-8-sig") as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             if row.get("Title") and row.get("Link"):
#                 rows.append(row)

#     total = len(rows)
#     print(f"📝 Tổng {total} bài báo cần crawl.\n", flush=True)

#     browser_cfg = BrowserConfig(headless=True)
#     async with AsyncWebCrawler(
#         crawler_strategy=AsyncPlaywrightCrawlerStrategy(browser_config=browser_cfg)
#     ) as crawler:

#         for idx, row in enumerate(rows, start=1):
#             title, link = row["Title"], row["Link"]
#             print(f"⏳ Crawling {idx}/{total}: {title}", flush=True)

#             success = False
#             for attempt in range(1, 4):
#                 try:
#                     result = await crawler.arun(url=link, config=CrawlerRunConfig())
#                     if result.success:
#                         md = result.markdown
#                         md_text = md.raw_markdown if hasattr(md, "raw_markdown") else md

#                         metadata_text, main_text = extract_main_content_with_metadata(md_text)
#                         sections = build_nested_structure(main_text)

#                         meta_info = parse_metadata(metadata_text)
#                         pmc_id = meta_info.get("ID", f"PMC_{idx}")
#                         pmid = meta_info.get("PMID", None)  # <-- thêm PMID
#                         authors = meta_info.get("Authors", [])

#                         os.makedirs(output_dir, exist_ok=True)
#                         output_file = os.path.join(output_dir, f"{idx}.json")
#                         with open(output_file, "w", encoding="utf-8") as f:
#                             json.dump({
#                                 "PMCID": pmc_id,
#                                 "PMID": pmid,            # <-- lưu PMID
#                                 "title": title,
#                                 "link": link,
#                                 "authors": authors,
#                                 "sections": sections
#                             }, f, ensure_ascii=False, indent=2)

#                         print(f"✅ Saved {idx}/{total}: {output_file}\n", flush=True)
#                         success = True
#                         break
#                     else:
#                         print(f"⚠️ Attempt {attempt}: Error crawling {link}: {result.error_message}", flush=True)
#                 except Exception as e:
#                     print(f"⚠️ Attempt {attempt}: Exception crawling {link}: {e}", flush=True)

#                 await asyncio.sleep(2)

#             if not success:
#                 print(f"❌ Failed to crawl {link} sau 3 lần thử\n", flush=True)

#             await asyncio.sleep(2)


# if __name__ == "__main__":
#     csv_file = "SB_publication_PMC.csv"
#     output_dir = "data\\PMC_articles_json"
#     print("DEBUG")
#     asyncio.run(crawl_all_from_csv(csv_file, output_dir))


# import asyncio
# import json
# import re
# import os
# import csv
# from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
# from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy


def extract_main_content_with_metadata(md_text: str):
    lines = md_text.split("\n")
    start_idx, end_idx = None, None

    # Tìm Abstract
    for i, line in enumerate(lines):
        if re.search(r"#+\s*abstract", line, re.IGNORECASE):
            start_idx = i
            break

    metadata_lines = lines[:start_idx] if start_idx is not None else []

    # Tìm References
    for i, line in enumerate(lines):
        if start_idx is not None and re.search(r"#+\s*references", line, re.IGNORECASE):
            end_idx_ref = len(lines) - 1
            for j in range(i + 1, len(lines)):
                if re.match(r"#+\s+", lines[j]) or re.match(r"^\*\s+", lines[j]) or re.match(r"^-{3,}$", lines[j]):
                    end_idx_ref = j - 1
                    break
            end_idx = end_idx_ref
            break

    if start_idx is not None:
        main_lines = lines[start_idx:end_idx + 1] if end_idx is not None else lines[start_idx:]
    else:
        main_lines = lines

    metadata_text = "\n".join(metadata_lines).strip()
    main_text = "\n".join(main_lines).strip()
    return metadata_text, main_text


def parse_references(raw_text: str):
    refs = []
    for line in raw_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^\*?\s*(\d+)\.\s*(.*)", line)
        if m:
            refs.append({"id": int(m.group(1)), "text": m.group(2)})
        elif line.startswith("* "):
            refs.append({"text": line[2:].strip()})
        else:
            if refs:
                refs[-1]["text"] += " " + line
            else:
                refs.append({"text": line})
    return refs


def parse_metadata(metadata_text: str):
    """
    Trích xuất:
    - Authors
    - PMCID
    - PMID
    - published_date
    """
    authors = []
    seen = set()
    matches = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", metadata_text)
    for name, link in matches:
        if "pubmed.ncbi.nlm.nih.gov" in link and "%5BAuthor%5D" in link:
            key = (name, link)
            if key not in seen:
                authors.append({"name": name, "link": link})
                seen.add(key)

    # PMCID
    pmc_id_match = re.search(r"PMCID:\s*(PMC\d+)", metadata_text)
    pmc_id = pmc_id_match.group(1) if pmc_id_match else None

    # PMID
    pmid_match = re.search(r"PMID:\s*\[?(\d+)\]?", metadata_text)
    pmid = pmid_match.group(1) if pmid_match else None

    # published_date (ví dụ: 2014 Aug 18)
    pub_date_match = re.search(r"\.\s*(\d{4}\s\w{3}\s\d{1,2})\s*;", metadata_text)
    published_date = pub_date_match.group(1) if pub_date_match else None

    return {"Authors": authors, "ID": pmc_id, "PMID": pmid, "published_date": published_date}






def build_nested_structure(md_text: str):
    root = {}
    stack = [(0, root)]

    for line in md_text.split("\n"):
        m = re.match(r"^(#+)\s+(.*)", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip().lower()
            while stack and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1]
            parent[title] = {}
            stack.append((level, parent[title]))
        else:
            if stack:
                node = stack[-1][1]
                node.setdefault("_content", []).append(line)

    def clean(node):
        for k, v in list(node.items()):
            if isinstance(v, dict):
                clean(v)
            elif isinstance(v, list):
                node[k] = "\n".join(v).strip()
        if "references" in node and "_content" in node["references"]:
            node["references"] = parse_references(node["references"]["_content"])

    clean(root)
    return root


# async def crawl_one(row, idx, output_dir, crawler):
#     title, link = row["Title"], row["Link"]
#     print(f"⏳ Crawling {idx}: {title}", flush=True)

#     for attempt in range(1, 4):
#         try:
#             result = await crawler.arun(url=link, config=CrawlerRunConfig())
#             if result.success:
#                 md_text = getattr(result.markdown, "raw_markdown", result.markdown)
#                 metadata_text, main_text = extract_main_content_with_metadata(md_text)
#                 sections = build_nested_structure(main_text)
#                 meta_info = parse_metadata(metadata_text)
#                 pmc_id = meta_info.get("ID", f"PMC_{idx}")
#                 pmid = meta_info.get("PMID", None)
#                 authors = meta_info.get("Authors", [])
#                 published_date = meta_info.get("published_date")

#                 os.makedirs(output_dir, exist_ok=True)
#                 output_file = os.path.join(output_dir, f"{idx}.json")
#                 with open(output_file, "w", encoding="utf-8") as f:
#                     json.dump({
#                         "PMCID": pmc_id,
#                         "PMID": pmid,
#                         "title": title,
#                         "link": link,
#                         "authors": authors,
#                         "published_date": published_date,
#                         "sections": sections
#                     }, f, ensure_ascii=False, indent=2)

#                 print(f"✅ Saved {idx}: {output_file}\n", flush=True)
#                 return True
#             else:
#                 print(f"⚠️ Attempt {attempt}: Error crawling {link}: {result.error_message}", flush=True)
#         except Exception as e:
#             print(f"⚠️ Attempt {attempt}: Exception crawling {link}: {e}", flush=True)
#         await asyncio.sleep(2)
#     print(f"❌ Failed to crawl {link} sau 3 lần thử\n", flush=True)
#     return False

# async def crawl_all_from_csv(csv_file, output_dir, max_concurrent=5):
#     rows = []
#     with open(csv_file, newline="", encoding="utf-8-sig") as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             if row.get("Title") and row.get("Link"):
#                 rows.append(row)

#     total = len(rows)
#     print(f"📝 Tổng {total} bài báo cần crawl.\n", flush=True)

#     browser_cfg = BrowserConfig(headless=True)
#     async with AsyncWebCrawler(
#         crawler_strategy=AsyncPlaywrightCrawlerStrategy(browser_config=browser_cfg)
#     ) as crawler:

#         semaphore = asyncio.Semaphore(max_concurrent)

#         async def sem_task(row, idx):
#             async with semaphore:
#                 await crawl_one(row, idx, output_dir, crawler)

#         tasks = [sem_task(row, idx+1) for idx, row in enumerate(rows)]
#         await asyncio.gather(*tasks)



# if __name__ == "__main__":
#     csv_file = "SB_publication_PMC.csv"
#     output_dir = "data\\PMC_articles_json"
#     print("DEBUG")
#     asyncio.run(crawl_all_from_csv(csv_file, output_dir))


import asyncio
import json
import re
import os
import csv
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy

# Hàm trích xuất metadata, thêm published_date
def parse_metadata(metadata_text: str):
    authors = []
    seen = set()

    # Tìm tất cả Markdown link [Tên](link)
    matches = re.findall(r"\[([^\]]+)\]\((https?://[^\)]+)\)", metadata_text)
    for name, link in matches:
        if "pubmed.ncbi.nlm.nih.gov" in link and "%5BAuthor%5D" in link:
            key = (name, link)
            if key not in seen:
                authors.append({"name": name, "link": link})
                seen.add(key)

    # PMCID
    pmc_id_match = re.search(r"PMCID:\s*(PMC\d+)", metadata_text)
    pmc_id = pmc_id_match.group(1) if pmc_id_match else None

    # PMID
    pmid_match = re.search(r"PMID:\s*\[?(\d+)\]?", metadata_text)
    pmid = pmid_match.group(1) if pmid_match else None

    # Published date, ví dụ: ". 2014 Aug 18;"
    pub_date_match = re.search(r"\.\s*(\d{4}\s+[A-Za-z]{3}\s+\d{1,2})\s*;", metadata_text)
    published_date = pub_date_match.group(1) if pub_date_match else None

    return {"Authors": authors, "ID": pmc_id, "PMID": pmid, "published_date": published_date}


async def crawl_single(row, idx, total, crawler, output_dir):
    title, link = row["Title"], row["Link"]
    print(f"⏳ Crawling {idx}/{total}: {title}", flush=True)
    success = False
    for attempt in range(1, 4):
        try:
            result = await crawler.arun(url=link, config=CrawlerRunConfig())
            if result.success:
                md = result.markdown
                md_text = md.raw_markdown if hasattr(md, "raw_markdown") else md

                # Tách metadata và nội dung chính
                metadata_text, main_text = extract_main_content_with_metadata(md_text)
                sections = build_nested_structure(main_text)

                meta_info = parse_metadata(metadata_text)
                pmc_id = meta_info.get("ID", f"PMC_{idx}")
                pmid = meta_info.get("PMID", None)
                authors = meta_info.get("Authors", [])
                published_date = meta_info.get("published_date", None)

                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, f"{idx}.json")

                # Nếu file tồn tại, load trước để merge, không ghi đè
                if os.path.exists(output_file):
                    with open(output_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {}

                data.update({
                    "PMCID": pmc_id,
                    "PMID": pmid,
                    "title": title,
                    "link": link,
                    "authors": authors,
                    "sections": sections,
                    "published_date": published_date
                })

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✅ Saved {idx}/{total}: {output_file}\n", flush=True)
                success = True
                break
            else:
                print(f"⚠️ Attempt {attempt}: Error crawling {link}: {result.error_message}", flush=True)
        except Exception as e:
            print(f"⚠️ Attempt {attempt}: Exception crawling {link}: {e}", flush=True)
        await asyncio.sleep(2)

    if not success:
        print(f"❌ Failed to crawl {link} sau 3 lần thử\n", flush=True)


async def crawl_all_from_csv(csv_file, output_dir, concurrency=5):
    rows = []
    with open(csv_file, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("Title") and row.get("Link"):
                rows.append(row)

    total = len(rows)
    print(f"📝 Tổng {total} bài báo cần crawl.\n", flush=True)

    browser_cfg = BrowserConfig(headless=True)
    async with AsyncWebCrawler(
        crawler_strategy=AsyncPlaywrightCrawlerStrategy(browser_config=browser_cfg)
    ) as crawler:

        sem = asyncio.Semaphore(concurrency)  # Giới hạn số task chạy đồng thời

        async def sem_task(row, idx):
            async with sem:
                await crawl_single(row, idx, total, crawler, output_dir)

        tasks = [asyncio.create_task(sem_task(row, idx)) for idx, row in enumerate(rows, start=1)]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    csv_file = "SB_publication_PMC.csv"
    output_dir = "data\\PMC_articles_json"
    asyncio.run(crawl_all_from_csv(csv_file, output_dir, concurrency=5))
