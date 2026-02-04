import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import os

# --- 1. 뉴스 크롤링 함수 (이 부분이 정의되어 있어야 합니다) ---
def crawl_naver_news(base_keywords, include_words=None, exclude_words=None, pages=1):
    query_parts = []
    if isinstance(base_keywords, str): base_keywords = [base_keywords]
    query_parts.append(f"({' | '.join(base_keywords)})")
    
    if include_words: query_parts.append(" ".join([f"+{word}" for word in include_words]))
    if exclude_words: query_parts.append(" ".join([f"-{word}" for word in exclude_words]))
    
    query = " ".join(query_parts)
    base_url = "https://search.naver.com/search.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    results = []
    for page in range(pages):
        start_val = (page * 10) + 1
        params = {
            'where': 'news', 'query': query, 'sm': 'tab_opt', 'sort': 1,
            'pd': 2, 'nso': 'so:dd,p:2d,a:all', 'start': start_val
        }
        try:
            response = requests.get(base_url, headers=headers, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 네이버 뉴스 검색 결과에서 링크 추출
            all_links = soup.find_all("a", class_="news_tit")
            if not all_links:
                all_links = soup.find_all("a") # 클래스명이 바뀔 경우를 대비한 백업

            for link in all_links:
                text = link.get_text().strip()
                href = link.get('href')

                # 제목 길이 필터 (10자 이상 200자 이하)
                if 10 <= len(text) <= 200 and href and href.startswith("http"):
                    # 제외 키워드 필터링
                    if exclude_words and any(bad in text for bad in exclude_words): continue
                    # 중복 제거
                    if any(r['url'] == href for r in results): continue
                    if text in ["네이버뉴스", "관련뉴스"]: continue

                    results.append({'title': text, 'url': href})
            
            time.sleep(0.5)
        except Exception as e:
            print(f"크롤링 중 에러 발생: {e}")
            break
            
    return results

# --- 2. 데이터 분류 및 형식화 함수 ---
def format_news_feed(news_data):
    sector_investment = [] # <투자손익/금융시장>
    sector_industry = []   # <생보3사/보험업계>

    for item in news_data:
        # 섹터 분류 로직: '손익' 또는 '자산' 포함 여부
        if '손익' in item['title'] or '자산' in item['title']:
            if len(sector_investment) < 5:
                sector_investment.append(item)
        else:
            if len(sector_industry) < 5:
                sector_industry.append(item)
        
        if len(sector_investment) >= 5 and len(sector_industry) >= 5:
            break

    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    output = f"■News feed: {today_str}\n\n"
    
    output += "<생보3사/보험업계>\n\n"
    if not sector_industry:
        output += "해당하는 기사가 없습니다.\n\n"
    for a in sector_industry:
        output += f"{a['title']}\n{a['url']}\n\n"
    
    output += "<투자손익/금융시장>\n\n"
    if not sector_investment:
        output += "해당하는 기사가 없습니다.\n\n"
    for a in sector_investment:
        output += f"{a['title']}\n{a['url']}\n\n"
    
    return output

# --- 3. 텔레그램 전송 함수 ---
def send_telegram_message(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 텔레그램 토큰 또는 Chat ID가 설정되지 않았습니다.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ 텔레그램 메시지 전송 성공!")
        else:
            print(f"❌ 전송 실패: {response.text}")
    except Exception as e:
        print(f"❌ 텔레그램 전송 중 에러 발생: {e}")

# --- 4. 메인 실행부 ---
if __name__ == "__main__":
    KEYWORDS = ["한화생명", "삼성생명", "교보생명", "생보사", "보험사"]
    EXCLUDES = ["배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원"]
    
    # 함수 호출 (여기가 에러가 났던 지점입니다)
    raw_news = crawl_naver_news(KEYWORDS, exclude_words=EXCLUDES, pages=5)
    
    # 리포트 생성
    final_report = format_news_feed(raw_news)
    
    # 결과 출력 및 전송
    print(final_report)
    send_telegram_message(final_report)
    
    # 파일 저장 (백업용)
    with open("daily_news_report.txt", "w", encoding="utf-8") as f:
        f.write(final_report)
