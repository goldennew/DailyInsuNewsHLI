import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime

# --- 1. 크롤링 함수 (제공해주신 코드 그대로 유지) ---
def crawl_naver_news_robust(base_keywords, include_words=None, exclude_words=None, pages=1):
    if isinstance(base_keywords, str): base_keywords = [base_keywords]
    if isinstance(include_words, str): include_words = [include_words]
    if isinstance(exclude_words, str): exclude_words = [exclude_words]

    print(f"🕒 조회 기준: 현재 시간({datetime.now().strftime('%Y-%m-%d %H:%M')})으로부터 48시간 이내")

    query_parts = []
    if base_keywords:
        if len(base_keywords) > 1:
            query_parts.append(f"({' | '.join(base_keywords)})")
        else:
            query_parts.append(base_keywords[0])

    if include_words: query_parts.append(" ".join([f"+{word}" for word in include_words]))
    if exclude_words: query_parts.append(" ".join([f"-{word}" for word in exclude_words]))

    query = " ".join(query_parts)
    base_url = "https://search.naver.com/search.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    results = []
    print(f"--- 검색어: [{query}] 크롤링 시작 ---")

    for page in range(pages):
        start_val = (page * 10) + 1
        params = {
            'where': 'news',
            'query': query,
            'sm': 'tab_opt',
            'sort': 1,
            'pd': 2,
            'nso': 'so:dd,p:2d,a:all',
            'start': start_val
        }

        try:
            response = requests.get(base_url, headers=headers, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            main_pack = soup.select_one("#main_pack")
            if not main_pack: main_pack = soup.body

            all_links = main_pack.find_all("a")
            found_in_page = 0

            for link in all_links:
                text = link.get_text().strip()
                href = link.get('href')

                # 필터: 제목 길이 10자 이상 200자 이하 (요청사항 반영)
                if 10 <= len(text) <= 200 and href and href.startswith("http"):
                    if exclude_words and any(bad_word in text for bad_word in exclude_words):
                        continue

                    if not any(k in text for k in base_keywords):
                        continue

                    if any(r['url'] == href for r in results): continue
                    if text in ["네이버뉴스", "관련뉴스"]: continue

                    results.append({'title': text, 'url': href})
                    found_in_page += 1
                    if found_in_page >= 15: break

            print(f"[{page+1}페이지] {found_in_page}건 수집 완료")
            if found_in_page == 0: break
            time.sleep(0.5)
        except Exception as e:
            print(f"에러 발생: {e}")
            break

    return results

# --- 2. 분류 및 텔레그램 메시지 형식화 (추가된 부분) ---
def format_and_classify(news_data):
    sector_invest = []  # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    for item in news_data:
        title = item['title']
        # '손익' 또는 '자산' 포함 여부로 분류
        if '손익' in title or '자산' in title:
            if len(sector_invest) < 5:
                sector_invest.append(item)
        else:
            if len(sector_industry) < 5:
                sector_industry.append(item)
        
        if len(sector_invest) >= 5 and len(sector_industry) >= 5:
            break

    today = datetime.now().strftime("%Y년 %m월 %d일")
    
    # 메시지 생성
    msg = f"■News feed: {today}\n"
    
    msg += "<생보3사/보험업계>\n\n"
    if not sector_industry: msg += "(해당 기사 없음)\n\n"
    for item in sector_industry:
        msg += f"{item['title']}\n{item['url']}\n\n"
        
    msg += "<투자손익/금융시장>\n\n"
    if not sector_invest: msg += "(해당 기사 없음)\n\n"
    for item in sector_invest:
        msg += f"{item['title']}\n{item['url']}\n\n"
        
    return msg

# --- 3. 텔레그램 전송 함수 (추가된 부분) ---
def send_telegram(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("❌ 텔레그램 환경변수 설정 확인 필요")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    
    try:
        res = requests.post(url, data=payload)
        if res.status_code == 200: print("✅ 텔레그램 전송 완료")
        else: print(f"❌ 전송 실패: {res.text}")
    except Exception as e:
        print(f"❌ 전송 에러: {e}")

# --- 4. 실행부 ---
if __name__ == "__main__":
    KEYWORDS = ["한화생명", "삼성생명", "교보생명", "생보사", "보험사"]
    EXCLUDES = ["배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원"]
    
    # 크롤링 실행
    news_data = crawl_naver_news_robust(KEYWORDS, exclude_words=EXCLUDES, pages=5)
    
    # 분류 및 메시지 생성
    final_report = format_and_classify(news_data)
    
    # 결과 출력 및 텔레그램 전송
    print(final_report)
    send_telegram(final_report)
