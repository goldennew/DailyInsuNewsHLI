import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
import os

# --- 1. 뉴스 크롤링 함수 (강화형) ---
def crawl_naver_news(base_keywords, include_words=None, exclude_words=None, pages=5):
    query_parts = []
    if isinstance(base_keywords, str): base_keywords = [base_keywords]
    # 네이버 검색 연산자에 맞게 쿼리 재구성
    query = " ".join(base_keywords) 
    if include_words: query += " " + " ".join([f"+{word}" for word in include_words])
    if exclude_words: query += " " + " ".join([f"-{word}" for word in exclude_words])
    
    base_url = "https://search.naver.com/search.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Referer': 'https://www.naver.com'
    }

    results = []
    print(f"🔎 검색어 [{query}]로 크롤링을 시작합니다.")

    for page in range(pages):
        start_val = (page * 10) + 1
        params = {
            'where': 'news',
            'query': query,
            'sm': 'tab_opt',
            'sort': '1',        # 최신순
            'pd': '2',          # 48시간 이내
            'start': start_val
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 네이버 뉴스 기사 제목의 다양한 클래스 선택자 대응
            articles = soup.select("div.news_wrap.api_ani_send")
            if not articles:
                articles = soup.select("ul.list_news > li") # 대체 선택자

            found_count = 0
            for article in articles:
                title_tag = article.select_one("a.news_tit")
                if not title_tag: continue
                
                text = title_tag.get_text().strip()
                href = title_tag.get('href')

                # 필터링 로직
                # 1. 제목 길이 (10~200자)
                if not (10 <= len(text) <= 200): continue
                # 2. 제외 키워드
                if exclude_words and any(bad in text for bad in exclude_words): continue
                # 3. 중복 제거
                if any(r['url'] == href for r in results): continue

                results.append({'title': text, 'url': href})
                found_count += 1
            
            print(f"📄 {page+1}페이지에서 {found_count}개의 기사를 찾았습니다.")
            if found_count == 0: break # 더 이상 결과가 없으면 중단
            
            time.sleep(0.8) # 차단 방지용 지연
        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            break
            
    return results

# --- 2. 데이터 분류 및 형식화 (동일) ---
def format_news_feed(news_data):
    sector_investment = [] # <투자손익/금융시장>
    sector_industry = []   # <생보3사/보험업계>

    for item in news_data:
        # 분류 키워드
        if any(word in item['title'] for word in ['손익', '자산', '투자', '증시', '금리']):
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
        output += "(관련 기사가 없습니다)\n\n"
    for a in sector_industry:
        output += f"{a['title']}\n{a['url']}\n\n"
    
    output += "<투자손익/금융시장>\n\n"
    if not sector_investment:
        output += "(관련 기사가 없습니다)\n\n"
    for a in sector_investment:
        output += f"{a['title']}\n{a['url']}\n\n"
    
    return output

# --- 3. 텔레그램 전송 (동일) ---
def send_telegram_message(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # 링크가 포함되어 있으므로 disable_web_page_preview 옵션은 취향껏 조절 가능
    payload = {'chat_id': chat_id, 'text': message, 'disable_web_page_preview': False}
    requests.post(url, data=payload)

# --- 4. 메인 실행 ---
if __name__ == "__main__":
    KEYWORDS = ["한화생명", "삼성생명", "교보생명", "보험사"]
    EXCLUDES = ["배타적", "민원", "지식iN", "고객센터"]
    
    raw_news = crawl_naver_news(KEYWORDS, exclude_words=EXCLUDES, pages=5)
    final_report = format_news_feed(raw_news)
    
    print(final_report)
    send_telegram_message(final_report)
