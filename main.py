import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime
import random
from urllib.parse import quote

def crawl_naver_news_pc(keywords, pages=2):
    session = requests.Session()
    
    # 1. 일반적인 윈도우 PC 크롬 브라우저로 위장
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    # 2. 메인 페이지 방문하여 쿠키 획득 (PC 버전)
    try:
        session.get("https://www.naver.com", headers=headers, timeout=10)
        time.sleep(random.uniform(1.0, 2.0)) # 사람이 접속한 척 뜸 들이기
    except:
        pass

    results = []
    # 검색어를 URL 인코딩 (필수)
    query_str = " ".join(keywords)
    
    print(f"🔎 네이버 뉴스(PC) 검색 시작: {query_str}")

    # PC 버전 뉴스 검색 URL
    base_url = "https://search.naver.com/search.naver"

    for page in range(pages):
        start = (page * 10) + 1  # PC는 페이지당 10개씩 보여줍니다.
        
        params = {
            'where': 'news',
            'query': query_str,
            'sort': '1',       # 최신순
            'nso': 'so:dd,p:2d', # 최근 2일
            'start': start
        }

        try:
            # 봇 탐지 회피를 위한 랜덤 지연
            time.sleep(random.uniform(2.0, 4.0))
            
            response = session.get(base_url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ 접속 실패 (코드: {response.status_code})")
                continue

            # 차단 여부 확인
            if "captcha" in response.url or "로봇" in response.text:
                print("🚨 네이버가 현재 IP를 차단했습니다. (VPN을 끄거나 다른 네트워크에서 실행하세요)")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # PC 버전 뉴스 리스트 선택자
            # 구조: ul.list_news > li.bx > div.news_wrap
            news_items = soup.select("div.news_wrap")

            if not news_items:
                # 검색 결과가 없을 때
                print(f"ℹ️ {page+1}페이지: 기사 없음")
                break

            found_in_page = 0
            for item in news_items:
                # 제목 태그 (PC 버전: a.news_tit)
                title_tag = item.select_one("a.news_tit")
                if not title_tag: continue
                
                text = title_tag.get_text().strip()
                href = title_tag.get('href')

                # 필터링
                if 5 < len(text) < 120 and href and href.startswith("http"):
                    # 중복 제거
                    if any(r['url'] == href for r in results): continue
                    
                    results.append({'title': text, 'url': href})
                    found_in_page += 1

            print(f"📄 {page+1}페이지: {found_in_page}건 수집")
            
            if found_in_page == 0:
                break

        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            break

    return results

# 리포트 포맷팅 함수 (기존과 동일하지만, 안전을 위해 다시 포함)
def format_news_report(news_data):
    sector_invest = []   
    sector_industry = [] 

    for item in news_data:
        title = item['title']
        if any(keyword in title for keyword in ['손익', '자산', '금융', '시장', '투자', '금리']):
            if len(sector_invest) < 5: sector_invest.append(item)
        else:
            if len(sector_industry) < 5: sector_industry.append(item)
    
    today = datetime.now().strftime("%Y-%m-%d")
    report = f"■ News feed: {today}\n"
    
    report += "\n<생보3사/보험업계>\n"
    if not sector_industry: report += "(기사 없음)\n"
    for item in sector_industry:
        report += f"• {item['title']}\n{item['url']}\n\n"
        
    report += "<투자손익/금융시장>\n"
    if not sector_invest: report += "(기사 없음)\n"
    for item in sector_invest:
        report += f"• {item['title']}\n{item['url']}\n\n"
        
    return report

def send_telegram(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      data={'chat_id': chat_id, 'text': message, 'disable_web_page_preview': True})
    except: pass

if __name__ == "__main__":
    KEYWORDS = ["삼성생명", "한화생명", "교보생명"]
    
    # 함수 이름 변경됨 (PC 버전)
    news_list = crawl_naver_news_pc(KEYWORDS, pages=2)
    
    final_msg = format_news_report(news_list)
    print(final_msg)
    send_telegram(final_msg)
