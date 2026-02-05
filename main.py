import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime
import random

def crawl_naver_news_robust(keywords, pages=2):
    # 1. 세션 객체 생성 (쿠키 유지를 위함)
    session = requests.Session()
    
    # 2. 최신 모바일 브라우저 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive'
    }

    # 3. 먼저 네이버 모바일 홈에 접속하여 기본 쿠키를 구움
    try:
        session.get("https://m.naver.com", headers=headers, timeout=10)
    except:
        pass

    results = []
    query = " ".join(keywords)
    print(f"🔎 네이버 뉴스 검색 시작: {query}")

    base_url = "https://m.search.naver.com/search.naver"

    for page in range(pages):
        # 검색 결과의 시작 번호 (모바일 기준 페이지당 약 15~20개 내외)
        start = (page * 15) + 1
        params = {
            'where': 'm_news',
            'query': query,
            'sm': 'mtb_pge',
            'sort': '1',      # 최신순
            'nso': 'so:dd,p:2d', # 최근 2일
            'start': start
        }

        # Referer를 네이버 검색 메인으로 설정하여 자연스러운 유입 연출
        headers['Referer'] = f"https://m.search.naver.com/search.naver?where=m_news&query={query}"

        try:
            # 0.5~2초 사이의 랜덤 지연 (자동화 탐지 방지)
            time.sleep(random.uniform(1.0, 2.5))
            
            response = session.get(base_url, headers=headers, params=params, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ 접속 실패 (상태코드: {response.status_code})")
                continue

            if "로봇" in response.text or "CAPTCHA" in response.text:
                print("🚨 네이버가 자동 수집을 감지했습니다. 다른 환경에서 테스트하거나 IP를 변경하세요.")
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 모바일 네이버 뉴스 리스트 컨테이너
            news_items = soup.select("li.bx") 

            found_in_page = 0
            for item in news_items:
                # 제목과 링크가 포함된 태그 찾기
                title_tag = item.select_one("a.news_tit")
                if not title_tag:
                    continue
                
                text = title_tag.get_text().strip()
                href = title_tag.get('href')

                # 필터링 조건 (제목 길이 및 URL 여부)
                if 10 < len(text) < 100 and href.startswith("http"):
                    if any(r['url'] == href for r in results): 
                        continue
                    
                    results.append({'title': text, 'url': href})
                    found_in_page += 1

            print(f"📄 {page+1}페이지: {found_in_page}건 수집 완료")
            
            # 검색 결과가 너무 적으면 중단
            if found_in_page == 0:
                break

        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            break

    return results

# ... (이후 format_news_report 및 send_telegram 함수는 기존과 동일하게 유지)

def format_news_report(news_data):
    sector_invest = []   # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    for item in news_data:
        title = item['title']
        if any(keyword in title for keyword in ['손익', '자산', '금융', '시장', '투자']):
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
    if not token or not chat_id: 
        print("Telegram 설정이 없습니다. 메시지를 전송하지 않습니다.")
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      data={'chat_id': chat_id, 'text': message, 'disable_web_page_preview': True})
    except: pass

if __name__ == "__main__":
    KEYWORDS = ["삼성생명", "한화생명", "교보생명"]
    news_list = crawl_naver_news_robust(KEYWORDS, pages=2)
    final_msg = format_news_report(news_list)
    print(final_msg)
    send_telegram(final_msg)
