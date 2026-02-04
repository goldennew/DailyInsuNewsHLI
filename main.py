import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime

def crawl_naver_news_robust(keywords, pages=3):
    # 깃허브 IP 차단을 피하기 위해 모바일 주소를 사용합니다.
    base_url = "https://m.search.naver.com/search.naver"
    
    # 더 실제 브라우저 같은 헤더 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ko-kr',
        'Referer': 'https://m.naver.com/'
    }

    results = []
    # 검색어를 하나로 합쳐서 간단하게 만듭니다.
    query = " ".join(keywords)
    print(f"🔎 모바일 네이버 뉴스 검색 시작: {query}")

    for page in range(pages):
        start = (page * 15) + 1
        params = {
            'where': 'm_news',
            'query': query,
            'sm': 'mtb_opt',
            'sort': '1', # 최신순
            'nso': 'so:dd,p:2d' # 최근 2일
        }

        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=15)
            
            # [디버깅] 만약 차단당했다면 로그에 기록됨
            if response.status_code != 200:
                print(f"❌ 접속 실패 (상태코드: {response.status_code})")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 모바일 네이버 뉴스 제목 태그 추출
            # 모바일은 api_txt_lines tit 또는 news_tit 클래스를 주로 사용합니다.
            news_items = soup.select("div.news_wrap")
            if not news_items:
                # 다른 구조일 경우 대비
                news_items = soup.select("li.bx")

            found_in_page = 0
            for item in news_items:
                title_tag = item.select_one("a.news_tit") or item.select_one("div.api_txt_lines.tit")
                if not title_tag: continue
                
                text = title_tag.get_text().strip()
                href = title_tag.get('href') if title_tag.has_attr('href') else title_tag.parent.get('href')

                # 필터링: 제목 길이 10~100자 (사용자 요청)
                if 10 < len(text) < 100 and href and href.startswith("http"):
                    # 중복 확인
                    if any(r['url'] == href for r in results): continue
                    
                    results.append({'title': text, 'url': href})
                    found_in_page += 1

            print(f"📄 {page+1}페이지: {found_in_page}건 발견")
            if found_in_page == 0:
                # 기사가 전혀 없다면 구조가 바뀌었거나 차단된 것이므로 로그 출력
                if "로봇" in response.text or "CAPTCHA" in response.text:
                    print("🚨 네이버가 자동 수집을 감지하여 차단했습니다.")
                break
            
            time.sleep(1.5) # 차단 방지를 위해 조금 더 천천히

        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            break

    return results

def format_news_report(news_data):
    sector_invest = []   # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    for item in news_data:
        title = item['title']
        # '손익' 또는 '자산' 포함 여부로 섹터 분류
        if '손익' in title or '자산' in title:
            if len(sector_invest) < 5: sector_invest.append(item)
        else:
            if len(sector_industry) < 5: sector_industry.append(item)
    
    today = datetime.now().strftime("%Y-%m-%d")
    report = f"■News feed: {today}\n"
    
    report += "\n<생보3사/보험업계>\n\n"
    if not sector_industry: report += "(기사 없음)\n\n"
    for item in sector_industry:
        report += f"{item['title']}\n{item['url']}\n\n"
        
    report += "<투자손익/금융시장>\n\n"
    if not sector_invest: report += "(기사 없음)\n\n"
    for item in sector_invest:
        report += f"{item['title']}\n{item['url']}\n\n"
        
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
    # 검색 키워드를 너무 복잡하게 섞지 말고 핵심 위주로 배치
    KEYWORDS = ["삼성생명", "한화생명", "교보생명", "보험사"]
    
    # 수집 시작
    news_list = crawl_naver_news_robust(KEYWORDS, pages=3)
    
    # 리포트 생성
    final_msg = format_news_report(news_list)
    
    # 출력 및 전송
    print(final_msg)
    send_telegram(final_msg)
