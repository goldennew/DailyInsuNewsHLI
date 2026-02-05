import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime
import random
from urllib.parse import quote  # 한글 인코딩을 위해 추가

def crawl_naver_news_robust(keywords, pages=2):
    session = requests.Session()
    
    # 최신 모바일 브라우저 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    try:
        session.get("https://m.naver.com", headers=headers, timeout=10)
    except:
        pass

    results = []
    query = " ".join(keywords)
    # 한글 검색어를 URL 안전한 형식으로 변환
    encoded_query = quote(query)
    
    print(f"🔎 네이버 뉴스 검색 시작: {query}")

    base_url = "https://m.search.naver.com/search.naver"

    for page in range(pages):
        start = (page * 15) + 1
        params = {
            'where': 'm_news',
            'query': query, # params에 넣을 때는 requests가 알아서 인코딩하지만
            'sm': 'mtb_pge',
            'sort': '1',
            'nso': 'so:dd,p:2d',
            'start': start
        }

        # 헤더의 Referer에는 직접 인코딩된 문자열을 넣어줘야 에러가 나지 않습니다.
        headers['Referer'] = f"https://m.search.naver.com/search.naver?where=m_news&query={encoded_query}"

        try:
            time.sleep(random.uniform(1.5, 2.5))
            
            # 여기서 headers에 인코딩된 Referer가 포함되어 에러를 방지함
            response = session.get(base_url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ 접속 실패 (상태코드: {response.status_code})")
                continue

            if "로봇" in response.text or "CAPTCHA" in response.text:
                print("🚨 네이버 차단 감지: IP가 제한되었거나 봇으로 탐지되었습니다.")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            news_items = soup.select("li.bx") 

            found_in_page = 0
            for item in news_items:
                title_tag = item.select_one("a.news_tit")
                if not title_tag: continue
                
                text = title_tag.get_text().strip()
                href = title_tag.get('href')

                if 10 < len(text) < 100 and href.startswith("http"):
                    if any(r['url'] == href for r in results): continue
                    results.append({'title': text, 'url': href})
                    found_in_page += 1

            print(f"📄 {page+1}페이지: {found_in_page}건 수집 완료")
            if found_in_page == 0: break

        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            break

    return results

# ... (나머지 함수는 동일)
