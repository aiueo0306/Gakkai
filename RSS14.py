from feedgen.feed import FeedGenerator
from datetime import datetime, timezone
from urllib.parse import urljoin
import os
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ORG_NAME = "日本神経学会"
BASE_URL = "https://www.neurology-jp.org/"
DEFAULT_LINK = "https://www.neurology-jp.org/"

def generate_rss(items, output_path):
    fg = FeedGenerator()
    fg.title(f"{ORG_NAME}トピックス")
    fg.link(href=DEFAULT_LINK)
    fg.description(f"{ORG_NAME}の最新トピック情報")
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


def extract_items(page):
    items = []
    max_items = 10

    # <dl class="news_list"> の中の dd を基準にループ
    rows = page.locator("dl.news_list > dd")
    count = rows.count()
    print(f"📦 発見した記事数: {count}")

    for i in range(min(count, max_items)):
        try:
            row = rows.nth(i)

            # 🔗 タイトルとリンク取得
            a_tag = row.locator("a").first
            title = a_tag.inner_text().strip()
            href = a_tag.get_attribute("href")
            full_link = urljoin(BASE_URL, href) if href else DEFAULT_LINK

            # 📅 対応する dt（日付）は「dd の直前の兄弟ノード」
            pub_date = datetime.now(timezone.utc)  # デフォルト
            try:
                dt_selector = f"dl.news_list > dt:nth-of-type({i + 1})"
                date_text = page.locator(dt_selector).inner_text().strip()
                pub_date = datetime.strptime(date_text, "%Y年%m月%d日").replace(tzinfo=timezone.utc)
            except:
                pass  # 日付がない場合は now() のまま or continue でも可

            # 📂 カテゴリや補足（任意）
            category = ""

            description = f"{category}{title}"
            items.append({
                "title": title,
                "link": full_link,
                "description": description,
                "pub_date": pub_date
            })
        except Exception as e:
            print(f"⚠ 行{i+1}の解析に失敗: {e}")
            continue

    return items

# ===== 実行ブロック =====
with sync_playwright() as p:
    print("▶ ブラウザを起動中...")
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()

    try:
        print("▶ ページにアクセス中...")
        page.goto(DEFAULT_LINK, timeout=30000)
        page.wait_for_load_state("load", timeout=30000)
    except PlaywrightTimeoutError:
        print("⚠ ページの読み込みに失敗しました。")
        browser.close()
        exit()

    print("▶ 記事を抽出しています...")
    items = extract_items(page)

    if not items:
        print("⚠ 抽出できた記事がありません。HTML構造が変わっている可能性があります。")

    rss_path = "rss_output/Feed14.xml"
    generate_rss(items, rss_path)
    browser.close()
