import requests
import os
import html
import difflib
import time
from datetime import datetime

# ==========================================
# 🔑 API 키 설정
# ==========================================
NAVER_CLIENT_ID = "2cC4xeZPfKKs3BVY_onT"
NAVER_CLIENT_SECRET = "21DmUYrAdX"

if os.environ.get("NAVER_CLIENT_ID"):
    NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

def crawl_naver_news_api(target_keywords, excludes=[], display_limit=50):
    """
    특정 키워드 그룹에 대해서만 뉴스를 수집하는 함수
    """
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    # 해당 그룹의 키워드로 쿼리 생성
    query = " | ".join(target_keywords)
    print(f"🔎 검색 시작: [{query}] (요청 {display_limit}건)")

    results = []
    
    # API 호출 횟수 계산 (1회 최대 100개)
    loop_count = (display_limit // 100) + 1 if display_limit % 100 != 0 else (display_limit // 100)
    
    for i in range(loop_count):
        req_display = 100 if display_limit > 100 else display_limit
        display_limit -= req_display
        
        start = (i * 100) + 1
        
        params = {
            "query": query,
            "display": req_display,
            "start": start,
            "sort": "date"
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                print(f"❌ API 호출 에러: {response.status_code}")
                break

            items = response.json().get('items', [])
            if not items: break

            for item in items:
                raw_title = item['title']
                clean_title = html.unescape(raw_title).replace("<b>", "").replace("</b>", "")
                
                raw_desc = item['description']
                clean_desc = html.unescape(raw_desc).replace("<b>", "").replace("</b>", "")
                
                link = item['originallink'] if item['originallink'] else item['link']

                # 1. 제외 키워드 체크
                if any(ex_word in clean_title for ex_word in excludes):
                    continue

                # 2. 필수 키워드 체크 (제목 기준)
                if not any(key_word in clean_title for key_word in target_keywords):
                    continue
                
                results.append({'title': clean_title, 'url': link, 'desc': clean_desc})
            
            time.sleep(0.3) 

        except Exception as e:
            print(f"⚠️ 에러: {e}")
            break
            
    print(f"   👉 수집 완료: {len(results)}건")
    return results

def remove_duplicates_globally(all_news):
    """
    합쳐진 전체 뉴스 리스트에서 중복(URL 및 내용)을 제거
    """
    unique_news = []
    seen_urls = set()
    seen_descriptions = []

    print("🧹 전체 중복 제거 및 정제 작업 중...")

    for item in all_news:
        # URL 중복 체크
        if item['url'] in seen_urls:
            continue
            
        # 본문 내용 유사도 체크 (30자 이상 겹치면 중복 처리)
        is_content_dup = False
        for exist_desc in seen_descriptions:
            matcher = difflib.SequenceMatcher(None, item['desc'], exist_desc)
            match = matcher.find_longest_match(0, len(item['desc']), 0, len(exist_desc))
            
            if match.size >= 10: 
                is_content_dup = True
