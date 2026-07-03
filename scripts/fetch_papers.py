import urllib.request
import urllib.parse
import json
import xml.etree.ElementTree as ET
import os
import re
import time
from datetime import datetime
import google.generativeai as genai

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# ==========================================
# ★ 關鍵更新：自動偵測你的金鑰可以使用的模型
# ==========================================
target_model = "gemini-1.5-flash" # 預設兜底名稱
try:
    available_models = []
    # 呼叫 API 取得你帳號所有獲准使用的模型
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            available_models.append(m.name)
    
    print("✅ 你的 API 金鑰支援以下模型：")
    for m_name in available_models:
        print(f"  - {m_name}")
        
    # 自動挑選最適合的免費模型 (優先找 1.5-flash 家族，若無則找 pro)
    for m_name in available_models:
        if '1.5-flash' in m_name:
            target_model = m_name
            break
    else:
        for m_name in available_models:
            if 'pro' in m_name or 'flash' in m_name:
                target_model = m_name
                break
            
except Exception as e:
    print(f"⚠️ 無法獲取模型清單，將嘗試使用預設值。原因: {e}")

print(f"\n🚀 決定使用模型：{target_model}\n")
model = genai.GenerativeModel(target_model)
# ==========================================

JOURNAL_QUERIES = {
    "AJCN": '"The American journal of clinical nutrition"[Journal]',
    "IJBNPA": '"International journal of behavioral nutrition and physical activity"[Journal]',
    "JPGN": '"Journal of pediatric gastroenterology and nutrition"[Journal]',
    
    # ★ 新增的三本期刊
    "JNEB": '"Journal of nutrition education and behavior"[Journal]',
    "AdvNutr": '"Advances in nutrition (Bethesda, Md.)"[Journal]',
    "MCN": '"Maternal & child nutrition"[Journal]'
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
    
    response = model.generate_content(prompt)
    return response.text

def main():
    output_dir = "src/content/articles"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for journal_name, query in JOURNAL_QUERIES.items():
        print(f"*** 正在透過 PubMed 搜尋 {journal_name} ***")
        
        articles = fetch_pubmed_articles(query, count=3)
        print(f"伺服器回應：找到 {len(articles)} 篇文章\n")
        
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
                time.sleep(2)
                
            except Exception as e:
                print(f"❌ 處理時發生錯誤，原因: {str(e)}")
        print("*" * 40)

if __name__ == "__main__":
    main()
