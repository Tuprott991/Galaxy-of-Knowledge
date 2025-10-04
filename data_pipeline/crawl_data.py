import asyncio
import json
import re
import os
import csv
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy




def extract_main_content(md_text: str) -> str:
    lines = md_text.split("\n")
    start_idx, end_idx = None, None

    for i, line in enumerate(lines):
        if start_idx is None and re.search(r"#+\s*abstract", line, re.IGNORECASE):
            start_idx = i
            break

    for i, line in enumerate(lines):
        if start_idx is not None and re.search(r"#+\s*references", line, re.IGNORECASE):
            end_idx_ref = len(lines) - 1
            for j in range(i + 1, len(lines)):
                if re.match(r"#+\s+", lines[j]) or re.match(r"^\*\s+", lines[j]) or re.match(r"^-{3,}$", lines[j]):
                    end_idx_ref = j - 1
                    break
            end_idx = end_idx_ref
            break

    if start_idx is not None and end_idx is not None:
        return "\n".join(lines[start_idx:end_idx + 1])
    else:
        return md_text

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


async def crawl_all_from_csv(csv_file, output_dir):
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

        for idx, row in enumerate(rows, start=1):
            title, link = row["Title"], row["Link"]
            print(f"⏳ Crawling {idx}/{total}: {title}", flush=True)

            success = False
            for attempt in range(1, 4):
                try:
                    result = await crawler.arun(url=link, config=CrawlerRunConfig())
                    if result.success:
                        md = result.markdown
                        md_text = md.raw_markdown if hasattr(md, "raw_markdown") else md

                        md_filtered = extract_main_content(md_text)
                        sections = build_nested_structure(md_filtered)

                        os.makedirs(output_dir, exist_ok=True)
                        output_file = os.path.join(output_dir, f"{idx}.json")  # tên file là số
                        with open(output_file, "w", encoding="utf-8") as f:
                            json.dump({"title": title, "sections": sections}, f, ensure_ascii=False, indent=2)

                        print(f"✅ Saved {idx}/{total}: {output_file}\n", flush=True)
                        success = True
                        break
                    else:
                        print(f"⚠️ Attempt {attempt}: Error crawling {link}: {result.error_message}", flush=True)
                except Exception as e:
                    print(f"⚠️ Attempt {attempt}: Exception crawling {link}: {e}", flush=True)

                await asyncio.sleep(2)  # delay giữa các retry

            if not success:
                print(f"❌ Failed to crawl {link} sau 3 lần thử\n", flush=True)

            await asyncio.sleep(2)  # delay giữa các bài báo



if __name__ == "__main__":
    csv_file = "SB_publication_PMC.csv"
    output_dir = "PMC_articles_json"
    print("DEBUG")
    asyncio.run(crawl_all_from_csv(csv_file, output_dir))
