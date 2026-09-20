#!/usr/bin/env python3
"""Crawl Shopee policy pages from data/urls.csv including all text content and content illustration images.

Filters out site UI icons (logo, support request icon, contact guide icon, tracking pixels)
so that ONLY policy content illustrations/diagrams/screenshots remain.
"""

from __future__ import annotations

import csv
import re
import shutil
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

MANIFEST_FIELDS = ["doc_id", "file_path", "title", "source_url", "retrieved_at", "document_version", "license_or_permission"]

# Exact UI icon alt texts and URL patterns to filter out
UI_ICON_ALTS = {
    "logo",
    "gửi yêu cầu hỗ trợ",
    "hướng dẫn liên hệ shopee",
}

UI_ICON_URL_PATTERNS = {
    "cs-saas",
    "facebook.com",
    "f3064b122b6742c4b6fe6cd0830bf573",
    "ee6e7b32de75409796ed8ad1844392dc",
    "dd37a34565464ced95529006bd3e6c22",
}

def is_ui_icon(src: str, alt: str) -> bool:
    alt_clean = (alt or "").strip().lower()
    src_clean = (src or "").lower()
    
    if alt_clean in UI_ICON_ALTS:
        return True
        
    for pattern in UI_ICON_URL_PATTERNS:
        if pattern in src_clean:
            return True
            
    return False

def yaml_value(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'

def download_image(img_url: str, save_dir: Path, idx: int) -> Path | None:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(img_url, headers=headers, timeout=15)
        if res.status_code == 200 and len(res.content) > 100:
            parsed = urlparse(img_url)
            ext = Path(parsed.path).suffix.lower()
            if not ext or len(ext) > 5 or ext not in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"]:
                ext = ".png"
            filename = f"img_{idx:02d}{ext}"
            save_path = save_dir / filename
            save_path.write_bytes(res.content)
            return save_path
    except Exception as e:
        print(f"    Failed to download image {img_url}: {e}", flush=True)
    return None

def extract_structured_markdown(page, doc_id: str, images_dir: Path) -> tuple[str, int]:
    data = page.evaluate("""() => {
        const titleEl = document.querySelector('h1') || document.querySelector('.article-title') || document.querySelector('.help-center-article-title');
        const title = titleEl ? titleEl.innerText.trim() : document.title;
        
        let contentEl = document.querySelector('.article-content') || document.querySelector('.article-detail') || document.querySelector('main') || document.body;
        
        const imgs = Array.from(contentEl.querySelectorAll('img')).map(img => ({
            src: img.getAttribute('src') || img.getAttribute('data-src') || img.getAttribute('srcset') || '',
            alt: img.getAttribute('alt') || ''
        })).filter(item => item.src && !item.src.startsWith('data:'));

        const innerText = contentEl.innerText || '';

        return { title, innerText, imgs };
    }""")

    # Filter out UI icons, keep only content illustrations
    downloaded_images = []
    seen_urls = set()
    img_counter = 1
    
    raw_imgs = data.get("imgs", [])
    content_imgs = [i for i in raw_imgs if not is_ui_icon(i["src"], i.get("alt", ""))]

    if content_imgs:
        images_dir.mkdir(parents=True, exist_ok=True)
        for img_info in content_imgs:
            src = img_info["src"]
            alt = img_info.get("alt") or f"Hình ảnh minh họa {img_counter}"
            if src in seen_urls:
                continue
            seen_urls.add(src)
            
            full_url = urljoin(page.url, src)
            local_path = download_image(full_url, images_dir, img_counter)
            if local_path:
                rel_path = f"images/{doc_id}/{local_path.name}"
                downloaded_images.append({
                    "url": full_url,
                    "alt": alt,
                    "rel_path": rel_path,
                    "local_path": str(local_path)
                })
                img_counter += 1
    else:
        # Clean up directory if no illustration images remain
        if images_dir.exists():
            shutil.rmtree(images_dir, ignore_errors=True)

    # Format body text into markdown
    body_lines = []
    raw_text = data.get("innerText", "").strip()
    
    paragraphs = [p.strip() for p in raw_text.split("\n") if p.strip()]
    for p in paragraphs:
        if re.match(r"^\d+[\.\)]\s+[A-Z\u0110\u0102\u00C2\u00CA\u00D4\u01A0\u01AF]", p) or re.match(r"^[I|V|X]+\.\s+", p):
            body_lines.append(f"\n## {p}\n")
        elif re.match(r"^\d+\.\d+[\.\)]?\s+", p):
            body_lines.append(f"\n### {p}\n")
        elif p.startswith("•") or p.startswith("-") or p.startswith("*"):
            body_lines.append(f"- {p.lstrip('•-* ').strip()}")
        else:
            body_lines.append(p)

    # Append illustration image section only if content images exist
    if downloaded_images:
        body_lines.append("\n## Hình ảnh & Sơ đồ Minh họa\n")
        for img in downloaded_images:
            body_lines.append(f"![{img['alt']}]({img['rel_path']})")
            body_lines.append(f"*Nguồn ảnh: [{img['url']}]({img['url']})*\n")

    markdown_body = "\n\n".join(body_lines)
    return markdown_body, len(downloaded_images)

def main():
    root_dir = Path(__file__).resolve().parent.parent
    urls_file = root_dir / "data" / "urls.csv"
    output_dir = root_dir / "data" / "shopee"
    output_dir.mkdir(parents=True, exist_ok=True)
    sources_csv = output_dir / "sources.csv"

    if not urls_file.exists():
        print(f"Error: {urls_file} does not exist!", file=sys.stderr)
        return 1

    with urls_file.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    print(f"Starting crawl for {len(rows)} pages (filtering UI icons)...", flush=True)

    manifest_records = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        for idx, row in enumerate(rows, start=1):
            url = row["url"]
            doc_id = row["doc_id"]
            title = row["title"]
            print(f"\n[{idx}/{len(rows)}] Crawling doc_id='{doc_id}' -> {url}", flush=True)

            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2500)

                images_dir = output_dir / "images" / doc_id
                body_content, img_count = extract_structured_markdown(page, doc_id, images_dir)

                metadata = {
                    "doc_id": doc_id,
                    "title": title,
                    "source_url": url,
                    "retrieved_at": date.today().isoformat(),
                    "document_version": row.get("document_version") or "2026-v1",
                    "audience": row.get("audience") or "buyer",
                    "category": row.get("category") or "general",
                    "language": row.get("language") or "vi",
                    "license_or_permission": row.get("license_or_permission") or "public-source",
                    "image_count": str(img_count),
                }

                front_matter = "\n".join(f"{k}: {yaml_value(v)}" for k, v in metadata.items())
                full_md = f"---\n{front_matter}\n---\n\n# {title}\n\n{body_content}\n"

                file_path = output_dir / f"{doc_id}.md"
                file_path.write_text(full_md, encoding="utf-8")
                print(f"  -> Saved {file_path} ({len(full_md)} bytes, {img_count} illustration images)", flush=True)

                rel_file_path = f"data/shopee/{doc_id}.md"
                manifest_records[doc_id] = {
                    "doc_id": doc_id,
                    "file_path": rel_file_path,
                    "title": title,
                    "source_url": url,
                    "retrieved_at": metadata["retrieved_at"],
                    "document_version": metadata["document_version"],
                    "license_or_permission": metadata["license_or_permission"],
                }

            except Exception as error:
                print(f"  Failed crawling {url}: {error}", file=sys.stderr, flush=True)
            finally:
                page.close()

        browser.close()

    # Clean unused image directories
    images_base_dir = output_dir / "images"
    if images_base_dir.exists():
        for sub_dir in images_base_dir.iterdir():
            if sub_dir.is_dir() and not list(sub_dir.glob("*")):
                shutil.rmtree(sub_dir, ignore_errors=True)

    # Write sources.csv
    with sources_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        for doc_id in sorted(manifest_records.keys()):
            writer.writerow(manifest_records[doc_id])

    print(f"\nManifest saved to {sources_csv}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
