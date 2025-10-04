import os
import json
import requests
from bs4 import BeautifulSoup
from time import sleep

DATA_DIR = "data/PMC_articles_json"
OUTPUT_DIR = "data/pubmed_links_json"
os.makedirs(OUTPUT_DIR, exist_ok=True)

LINK_TEMPLATES = {
    "similar": "https://pubmed.ncbi.nlm.nih.gov/?linkname=pubmed_pubmed&from_uid={pmid}&page={page}",
    "cited": "https://pubmed.ncbi.nlm.nih.gov/?linkname=pubmed_pubmed_citedin&from_uid={pmid}&page={page}"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9"
}

def fetch_url(url, retries=3, delay=3):
    """Fetch URL với retry và delay giữa các lần thử"""
    for attempt in range(1, retries+1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                return resp.text
            else:
                print(f"Attempt {attempt}: Status {resp.status_code} for {url}")
        except Exception as e:
            print(f"Attempt {attempt} failed for {url}: {e}")
        sleep(delay)
    return None

def get_total_pages(soup):
    el = soup.select_one(".of-total-pages")
    if el:
        try:
            return int(el.get_text(strip=True).replace("of ", ""))
        except:
            return 1
    return 1

def parse_page(soup):
    results = []
    chunk_div = soup.select_one("div.search-results-chunk")
    if chunk_div and chunk_div.has_attr("data-chunk-ids"):
        pmids = chunk_div["data-chunk-ids"].split(",")
        for pmid in pmids:
            a_tag = soup.select_one(f"a.docsum-title[data-article-id='{pmid}']")
            if a_tag:
                title = a_tag.get_text(strip=True)
                link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
                results.append({"PMID": pmid, "link": link, "title": title})
    return results

def crawl_pubmed_links(pmid, link_type):
    template = LINK_TEMPLATES[link_type]
    all_results = []

    # Fetch page 1 trước để lấy tổng số trang
    url = template.format(pmid=pmid, page=1)
    html = fetch_url(url)
    if not html:
        print(f"Error fetching first page: {url}")
        return all_results

    soup = BeautifulSoup(html, "html.parser")
    total_pages = get_total_pages(soup)
    print(f"PMID {pmid} ({link_type}): total pages = {total_pages}")

    # Crawl từng page
    for page in range(1, total_pages+1):
        url = template.format(pmid=pmid, page=page)
        html = fetch_url(url)
        if not html:
            print(f"Failed to fetch page {page} for PMID {pmid}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        results = parse_page(soup)
        if results:
            all_results.extend(results)
            print(f"Page {page}: {len(results)} items")
        else:
            print(f"Page {page}: no results found")

        sleep(1)  # tránh spam server

    return all_results

def main():
    json_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
    for jf in json_files:
        with open(os.path.join(DATA_DIR, jf), "r", encoding="utf-8") as f:
            data = json.load(f)

        pmid = data.get("PMID")
        if not pmid:
            continue

        for link_type in ["similar", "cited"]:
            results = crawl_pubmed_links(pmid, link_type)
            if results:
                output_file = os.path.join(OUTPUT_DIR, f"{pmid}_{link_type}.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)
                print(f"Saved {len(results)} items to {output_file}")

if __name__ == "__main__":
    main()
