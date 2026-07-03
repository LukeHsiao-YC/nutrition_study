import feedparser
import google.generativeai as genai
from google.colab import userdata  # 導入 Colab 讀取金鑰的工具
import os
import re
from datetime import datetime

# 從 Colab Secrets 安全取得金鑰
api_key = userdata.get('GEMINI_API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

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
    response = model.generate_content(prompt)
    return response.text

# 開始抓取與測試
for journal_name, feed_url in JOURNAL_FEEDS.items():
    print(f"--- 正在抓取 {journal_name} ---")
    feed = feedparser.parse(feed_url)
    
    # 在 Colab 先測試最新的 1 篇就好
    for entry in feed.entries[:1]:
        title = entry.title
        link = entry.link
        summary = entry.get("summary", entry.get("description", "無摘要內容"))
        
        if summary == "無摘要內容" or len(summary) < 20:
            continue
            
        print(f"最新文章標題: {title}")
        ai_content = generate_article_analysis(title, summary, link)
        print(ai_content)
