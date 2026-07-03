import feedparser
import os
import re
from datetime import datetime
from google import genai

# ★ 關鍵更新：偽裝成一般 Chrome 瀏覽器，避免被醫學期刊的防火牆阻擋
feedparser.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

JOURNAL_FEEDS = {
    "AJCN": "https://ajcn.nutrition.org/rss", 
    "IJBNPA": "https://ijbnpa.biomedcentral.com/articles/most-recent/rss.xml",
    "JPGN": "https://journals.lww.com/jpgn/_layouts/15/OAKS.Journals/feed.aspx?FeedType=CurrentIssue"
}

def generate_article_analysis(title, summary, link):
    prompt = f"""
    你是一位專業的醫學與營養學研究助理。請閱讀以下醫學期刊文章的標題與摘要，並用「繁體中文」輸出指定格式的重點整理。

    文章標題: {title}
    文章摘要: {summary}
    文章連結: {link}

    請輸出以下內容，並嚴格使用 Markdown 格式：
    
    ### 重點摘要
    請用 3 到 4 句話總結這項研究的背景、方法、結果與結論。

    ### 研究縫隙 (Research Gap)
    請推敲這篇文獻填補了什麼過去研究未知的空白，或是未來還可以進一步研究的限制。

    ### 關鍵字
    請列出 5 個最重要的關鍵字，格式必須是「繁體中文 (英文)」。
    """
    
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=prompt
    )
    return response.text

def main():
    output_dir = "src/content/articles"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for journal_name, feed_url in JOURNAL_FEEDS.items():
        print(f"--- 正在嘗試抓取 {journal_name} ---")
        feed = feedparser.parse(feed_url)
        
        # ★ 新增檢查機制：印出到底抓到幾篇，若被擋下會跳出警告
        entries_count = len(feed.entries)
        print(f"伺服器回應：找到 {entries_count} 篇文章")
        
        if entries_count == 0:
            print(f"⚠️ 警告：無法從 {journal_name} 獲取資料，可能是防火牆阻擋或網址失效。\n")
            continue
        
        for entry in feed.entries[:3]:
            title = entry.title
            link = entry.link
            
            summary = entry.get("summary", entry.get("description", "無摘要內容"))
            
            if summary == "無摘要內容" or len(summary) < 20:
                print(f"跳過無摘要文章: {title}")
                continue
                
            print(f"處理中: {title} (呼叫 AI 分析...)")
            
            try:
                ai_content = generate_article_analysis(title, summary, link)
                
                safe_title = re.sub(r'[\\/*?:"<>|]', "", title)[:50]
                date_str = datetime.now().strftime("%Y-%m-%d")
                filename = f"{output_dir}/{date_str}-{journal_name}-{safe_title}.md"
                
                if os.path.exists(filename):
                    print(f"檔案已存在，跳過: {filename}")
                    continue
                
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(f"---\n")
                    f.write(f"title: \"{title}\"\n")
                    f.write(f"journal: \"{journal_name}\"\n")
                    f.write(f"pubDate: \"{date_str}\"\n")
                    f.write(f"link: \"{link}\"\n")
                    f.write(f"---\n\n")
                    f.write(ai_content)
                
                print(f"✅ 成功生成: {filename}")
                
            except Exception as e:
                print(f"❌ 處理時發生錯誤: {title}，原因: {str(e)}")
        print("\n") # 換行讓版面乾淨一點

if __name__ == "__main__":
    main()
