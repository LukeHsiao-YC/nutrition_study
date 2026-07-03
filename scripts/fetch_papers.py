import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import os
import re
import time  # ★ 新增：用來控制程式的執行速度
from datetime import datetime
from google import genai

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

JOURNAL_QUERIES = {
    "AJCN": '"The American journal of clinical nutrition"[Journal]',
    "IJBNPA": '"International journal of behavioral nutrition and physical activity"[Journal]',
    "JPGN": '"Journal of pediatric gastroenterology and nutrition"[Journal]'
}

def fetch_pubmed_articles(journal_query, count=3):
    articles = []
    try:
        encoded_query = urllib.parse.quote(journal_query)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmode=json&retmax={count}&sort=date"
        
        req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            search_data = json.loads(response.read().decode())
        
        id_list = search_data['esearchresult'].get('idlist', [])
        if not id_list:
            return articles
            
        ids_str = ",".join(id_list)
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={ids_str}&retmode=xml"
        
        req_fetch = urllib.request.Request(fetch_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_fetch) as response:
            xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        for article in root.findall('.//PubmedArticle'):
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else "無標題"
            
            abstract_texts = article.findall('.//AbstractText')
            summary = " ".join([elem.text for elem in abstract_texts if elem.text]) if abstract_texts else "無摘要內容"
            
            pmid_elem = article.find('.//PMID')
            pmid = pmid_elem.text if pmid_elem is not None else ""
            link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""
            
            articles.append({
                "title": title,
                "summary": summary,
                "link": link
            })
    except Exception as e:
        print(f"PubMed 抓取失敗: {e}")
        
    return articles

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
    
    # ★ 更新：改用 gemini-2.0-flash，完美契合新版 SDK
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    return response.text

def main():
    output_dir = "src/content/articles"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for journal_name, query in JOURNAL_QUERIES.items():
        print(f"--- 正在透過 PubMed 搜尋 {journal_name} ---")
        
        articles = fetch_pubmed_articles(query, count=3)
        print(f"伺服器回應：找到 {len(articles)} 篇文章\n")
        
        # ★ 新增：每次與 PubMed 溝通完，強制休息 2 秒，避免被封鎖 429
        time.sleep(2)
        
        for article in articles:
            title = article['title']
            summary = article['summary']
            link = article['link']
            
            if summary == "無摘要內容" or len(summary) < 20:
                print(f"跳過無摘要文章: {title[:30]}...")
                continue
                
            print(f"處理中: {title[:50]}... (呼叫 AI 分析...)")
            
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
                
                print(f"✅ 成功生成 Markdown 檔案！")
                
                # ★ 新增：每次呼叫完 AI，也休息 2 秒，確保 API 穩定
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ 處理時發生錯誤，原因: {str(e)}")
        print("-" * 40)

if __name__ == "__main__":
    main()
