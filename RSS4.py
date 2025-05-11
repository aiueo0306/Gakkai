from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BASE_URL = "https://www.chemotherapy.or.jp/"
DEFAULT_LINK1 = "https://www.chemotherapy.or.jp/modules/newslist/index.php?content_id=4"
DEFAULT_LINK2 = "https://www.chemotherapy.or.jp/modules/newslist/index.php?content_id=3"

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title("日本化学療法学会トピックス")
    fg.link(href=BASE_URL)
    fg.description("日本化学療法学会の最新トピック情報")
    fg.language("ja")
    fg.generator("python-feedgen")
    fg.docs("http://www.rssboard.org/rss-specification")
    fg.lastBuildDate(datetime.now(timezone.utc))

    for item in items:
        entry = fg.add_entry()
        entry.title(item['title'])
        entry.link(href=item['link'])
        entry.description(item['description'])
        guid_value = f"{item['link']}#{item['pub_date'].strftime('%Y%m%d')}"
        entry.guid(guid_value, permalink=False)
        entry.pubDate(item['pub_date'])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fg.rss_file(output_path)
    print(f"\n✅ RSSフィード生成完了！📄 保存先: {output_path}")


def extract_items1(page):
    items = []
    max_items = 10
    news_titles = page.locator(".news_title")
    count = news_titles.count()
    print(f"📦 [news_title] 発見した記事数: {count}")

    for i in range(min(count, max_items)):
        try:
            a_tag = news_titles.nth(i).locator("a")
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href) if href else DEFAULT_LINK1

            date_text = page.locator(".news_date").nth(i).inner_text().strip().split("New")[0].strip()
            pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)

            items.append({
                "title": title,
                "link": full_link,
                "description": title,
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ [news_blocks] 行{i+1}の解析に失敗: {e}")
            continue

    return items


def extract_items2(page):
    items = []
    max_items = 10
    title_blocks = page.locator(".title_news")
    count = title_blocks.count()
    print(f"📦 [important_news] 発見した記事数: {count}")

    for i in range(min(count, max_items)):
        try:
            a_tag = title_blocks.nth(i).locator("a")
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href) if href else DEFAULT_LINK2

            date_text = page.locator(".date_news").nth(i).inner_text().strip()
            pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)

            items.append({
                "title": title,
                "link": full_link,
                "description": title,
                "pub_date": pub_date
            })

        except Exception as e:
            print(f"⚠ [important_news] 行{i+1}の解析に失敗: {e}")
            continue

    return items


# ===== 実行ブロック =====
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()

    # --- 1ページ目 ---
    page1 = context.new_page()
    try:
        print("▶ [1ページ目] アクセス中...")
        page1.goto(DEFAULT_LINK1, timeout=30000)
        page1.wait_for_load_state("load", timeout=30000)
        items1 = extract_items1(page1)
        if not items1:
            print("⚠ [1ページ目] 抽出できた記事がありません。")
    except PlaywrightTimeoutError:
        print("⚠ [1ページ目] 読み込み失敗")
        items1 = []

    # --- 2ページ目 ---
    page2 = context.new_page()
    try:
        print("▶ [2ページ目] アクセス中...")
        page2.goto(DEFAULT_LINK2, timeout=30000)
        page2.wait_for_load_state("load", timeout=30000)
        items2 = extract_items2(page2)
        if not items2:
            print("⚠ [2ページ目] 抽出できた記事がありません。")
    except PlaywrightTimeoutError:
        print("⚠ [2ページ目] 読み込み失敗")
        items2 = []

    # --- 統合 + 並べ替え ---
    items = items1 + items2
    items.sort(key=lambda x: x["pub_date"], reverse=True)

    # --- RSS生成 ---
    rss_path = "rss_output/Feed4.xml"
    generate_rss(items, rss_path)

    browser.close()
