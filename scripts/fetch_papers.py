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

# 動態挑選可用的新版 flash 模型(1.5 已淘汰;避開 image/tts/preview 等特殊版)
target_model = "gemini-2.5-flash"
try:
    available = {
        m.name.replace("models/", "")
        for m in genai.list_models()
        if 'generateContent' in m.supported_generation_methods
    }
    preferred = ("gemini-2.5-flash", "gemini-2.0-flash",
                 "gemini-2.5-flash-lite", "gemini-2.0-flash-lite")
    picked = next((n for n in preferred if n in available), None)
    if not picked:
        picked = next(
            (n for n in sorted(available)
             if 'flash' in n and not any(x in n for x in ('image', 'tts', 'preview', 'exp'))),
            None,
        )
    if picked:
        target_model = picked
except Exception as e:
    print(f"無法獲取模型清單，使用預設值 {target_model}。原因: {e}")

model = genai.GenerativeModel(target_model)

ALL_JOURNAL_QUERIES = {
    "PedObes": ('"Pediatric obesity"[Journal]', "兒童肥胖"),
    "ObesRev": ('"Obesity reviews"[Journal]', "兒童肥胖"),
    "IJO": ('"International journal of obesity"[Journal]', "兒童肥胖"),
    "IJBNPA": ('"International journal of behavioral nutrition and physical activity"[Journal]', "營養衛教介入"),
    "Appetite": ('"Appetite"[Journal]', "營養衛教介入"),
    "JNEB": ('"Journal of nutrition education and behavior"[Journal]', "營養衛教介入"),
    "PEC": ('"Patient education and counseling"[Journal]', "營養衛教介入"),
    "JMIRPed": ('"JMIR pediatrics and parenting"[Journal]', "營養衛教介入"),
    "PHN": ('"Public health nutrition"[Journal]', "社區營養"),
    "AJPM": ('"American journal of preventive medicine"[Journal]', "社區營養"),
    "MCN": ('"Maternal & child nutrition"[Journal]', "社區營養"),
    "EJE": ('"European journal of epidemiology"[Journal]', "營養流行病學"),
    "IJE": ('"International journal of epidemiology"[Journal]', "營養流行病學"),
    "AdvNutr": ('"Advances in nutrition (Bethesda, Md.)"[Journal]', "營養流行病學"),
    "ClinNutr": ('"Clinical nutrition (Edinburgh, Scotland)"[Journal]', "營養評估"),
    "AJCN": ('"The American journal of clinical nutrition"[Journal]', "營養評估"),
    "JPEN": ('"JPEN. Journal of parenteral and enteral nutrition"[Journal]', "營養評估"),
    "JPGN": ('"Journal of pediatric gastroenterology and nutrition"[Journal]', "營養評估"),
    # ── 擴充來源(2026-07,可自行增刪:格式 "簡稱": ('"期刊全名"[Journal]', "分類"))──
    "Obesity": ('"Obesity (Silver Spring, Md.)"[Journal]', "兒童肥胖"),
    "ChildObes": ('"Childhood obesity (Print)"[Journal]', "兒童肥胖"),
    "JAMAPed": ('"JAMA pediatrics"[Journal]', "兒童肥胖"),
    "Pediatrics": ('"Pediatrics"[Journal]', "兒童肥胖"),
    "JAND": ('"Journal of the Academy of Nutrition and Dietetics"[Journal]', "營養衛教介入"),
    "Nutrients": ('"Nutrients"[Journal]', "營養評估"),
    "JNutr": ('"The Journal of nutrition"[Journal]', "營養評估"),
    "EJCN": ('"European journal of clinical nutrition"[Journal]', "營養評估"),
    "BJN": ('"The British journal of nutrition"[Journal]', "營養流行病學"),
    "NutrRev": ('"Nutrition reviews"[Journal]', "營養流行病學"),
    "MatChildHJ": ('"Maternal and child health journal"[Journal]', "社區營養"),
    "BMCPH": ('"BMC public health"[Journal]', "社區營養"),
}

def get_today_batch():
    """把所有期刊平均分成 3 組,依當天輪一組(不論期刊總數多少都能運作)。"""
    keys = list(ALL_JOURNAL_QUERIES.keys())
    n = len(keys)
    batch_index = datetime.now().timetuple().tm_yday % 3
    # 平均切成 3 組
    active_keys = [k for i, k in enumerate(keys) if i % 3 == batch_index]
    cats = sorted({ALL_JOURNAL_QUERIES[k][1] for k in active_keys})
    print(f"今日任務：執行第 {batch_index + 1}/3 組期刊({len(active_keys)}/{n} 本;涵蓋 {', '.join(cats)})")
    return {k: ALL_JOURNAL_QUERIES[k] for k in active_keys}

def fetch_pubmed_articles(journal_query, count=3):
    articles = []
    try:
        encoded_query = urllib.parse.quote(journal_query)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={encoded_query}&retmode=json&retmax={count}&sort=date&reldate=365&datetype=pdat"
        
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
            
            # 抓取 DOI
            doi = ""
            for article_id in article.findall('.//ArticleId'):
                if article_id.get('IdType') == 'doi':
                    doi = article_id.text
                    break
            if not doi:
                for eloc in article.findall('.//ELocationID'):
                    if eloc.get('EIdType') == 'doi':
                        doi = eloc.text
                        break
            
            articles.append({
                "title": title,
                "summary": summary,
                "link": link,
                "pmid": pmid,
                "doi": doi
            })
    except Exception as e:
        print(f"PubMed 抓取失敗: {e}")
        
    return articles

def generate_article_analysis(title, summary):
    prompt = f"""
    你是一位專業的醫學與營養學研究助理。請閱讀以下醫學期刊文章的標題與摘要。

    文章標題: {title}
    文章摘要: {summary}

    請以「繁體中文」進行重點整理，並「嚴格以 JSON 格式」輸出，不要包含任何 Markdown 標記或說明文字。
    輸出的 JSON 必須包含以下三個欄位：
    1. "summary": 用 3 到 4 句話總結研究背景、方法、結果與結論。
    2. "gap": 說明這篇文獻填補了什麼研究空白，或是未來的研究限制。
    3. "tags": 根據文章內容萃取 3 到 5 個分類標籤（僅限繁體中文，如 "兒童肥胖", "社區介入", "腸胃道疾病", "飲食控制"），請以陣列 (Array) 呈現。
    """
    
    response = model.generate_content(prompt)
    return response.text

def main():
    output_dir = "src/content/articles"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    active_journals = get_today_batch()

    for journal_name, (query, category) in active_journals.items():
        print(f"*** 正在透過 PubMed 搜尋 {journal_name} ({category}) ***")
        
        articles = fetch_pubmed_articles(query, count=3)
        print(f"伺服器回應：找到 {len(articles)} 篇文章\n")
        time.sleep(2)
        
        for article in articles:
            title = article['title']
            summary = article['summary']
            link = article['link']
            pmid = article['pmid']
            doi = article['doi']
            
            if summary == "無摘要內容" or len(summary) < 20:
                continue
                
            date_str = datetime.now().strftime("%Y-%m-%d")
            
            if pmid:
                filename = f"{output_dir}/{pmid}.md"
            else:
                safe_title_file = re.sub(r'[\\/*?:"<>|]', "", title)[:50]
                filename = f"{output_dir}/{date_str}-{journal_name}-{safe_title_file}.md"
            
            if os.path.exists(filename):
                print(f"檔案已存在，跳過: {pmid or title[:20]}")
                continue
                
            print(f"處理中: {title[:50]}... (呼叫 AI 分析並萃取標籤...)")
            
            try:
                ai_response = generate_article_analysis(title, summary)
                
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if not json_match:
                    raise ValueError("AI 沒有回傳正確的 JSON 格式")
                
                data = json.loads(json_match.group(0))
                
                tags_list = data.get("tags", ["未分類"])
                tags_yaml = "[" + ", ".join([f'"{t}"' for t in tags_list]) + "]"
                
                safe_title_frontmatter = title.replace('"', "'")
                
                markdown_content = f"""---
title: "{safe_title_frontmatter}"
journal: "{journal_name}"
category: "{category}"
pubDate: "{date_str}"
link: "{link}"
doi: "{doi}"
tags: {tags_yaml}
---

### 重點摘要
{data.get('summary', '無摘要資料')}

### 研究縫隙 (Research Gap)
{data.get('gap', '無研究縫隙資料')}

### 原文資訊 (Original English)
**Title:** {title}
**Abstract:** {summary}
"""
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                
                print(f"[成功] 成功生成並標記標籤！")
                
                time.sleep(5)
                
            except Exception as e:
                print(f"[錯誤] 處理時發生錯誤，原因: {str(e)}")
        print("*" * 40)

if __name__ == "__main__":
    main()
