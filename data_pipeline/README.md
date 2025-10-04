# NASA HACKATHON - PubMed Crawler

This folder contains an async crawler (`crawl_data.py`) that reads PubMed-style links from `SB_publication_PMC.csv`, fetches the pages using `crawl4ai` with a headless browser, extracts content from Abstract to References, parses the Markdown headings, and saves each article into a separate JSON file named `1.json`, `2.json`, etc. Each JSON file contains:

```json
{
  "title": "Article title",
  "sections": { ... } 
}
````

## Prerequisites

* Python 3.9+ (3.10 or 3.11 recommended)
* Windows PowerShell (commands below assume PowerShell)

## Setup

1. (Optional) Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```
3. Install Playwright browsers (required by crawl4ai):

   ```powershell
   python -m playwright install --with-deps
   ```

## Usage

1. Ensure `SB_publication_PMC.csv` is present in this folder and has `Title` and `Link` columns.
2. Run the crawler:

   ```powershell
   python crawl_data.py
   ```
3. Output will be saved into the folder `PMC_articles_json` as numbered JSON files: `1.json`, `2.json`, etc.

## Notes

* Each JSON file contains the `title` and the structured `sections` of the article.
* The crawler fetches pages sequentially and includes retries on errors.
* If you encounter `ModuleNotFoundError: No module named 'crawl4ai'`, ensure you are in the correct environment and re-run:

  ```powershell
  pip install -r requirements.txt
  ```
* If Playwright complains about missing browsers, rerun:

  ```powershell
  python -m playwright install --with-deps
  ```