import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime

# --- 1. 크롤링 함수 (사용자께서 제공하신 코드 그대로 유지) ---
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

                # 사용자 필터: 10자 초과 100자 미만
                if 10 < len(text) < 100 and href and href.startswith("http"):
                    is_excluded = False
                    if exclude_words:
                        for bad_word in exclude_words:
                            if bad_word in text:
                                is_excluded = True
                                break
                    if is_excluded: continue

                    matched_keywords = []
                    for k in base_keywords:
                        if k in text:
                            matched_keywords.append(k)

                    if not matched_keywords: continue
                    if any(r['url'] == href for r in results): continue
                    if text in ["네이버뉴스", "관련뉴스"]: continue

                    results.append({
                        'title': text,
                        'url': href
                    })
                    found_in_page += 1
                    if found_in_page >= 15: break

            print(f"[{page+1}페이지] {found_in_page}건 수집 완료")
            if found_in_page == 0: break
            time.sleep(0.5)
        except Exception as e:
            print(f"에러 발생: {e}")
            break

    return results

# --- 2. 분류 및 출력 형식 정리 (요구사항 반영) ---
def format_news_report(news_data):
    sector_invest = [] # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    for item in news_data:
        title = item['title']
        # '손익' 또는 '자산'이 포함되면 투자 섹터로 분류
        if '손익' in title or '자산' in title:
            if len(sector_invest) < 5:
                sector_invest.append(item)
        else:
            if len(sector_industry) < 5:
                sector_industry.append(item)
        
        # 둘 다 5개씩 찼으면 종료
        if len(sector_invest) >= 5 and len(sector_industry) >= 5:
            break

    today = datetime.now().strftime("%Y-%m-%d")
    
    # [출력 형식 엄격 준수]
    report = f"■News feed: {today}\n"
    
    report += "<생보3사/보험업계>\n\n"
    for item in sector_industry:
        report += f"{item['title']}\n{item['url']}\n\n"
        
    report += "<투자손익/금융시장>\n\n"
    for item in sector_invest:
        report += f"{item['title']}\n{item['url']}\n\n"
        
    return report

# --- 3. 텔레그램 전송 함수 ---
def send_telegram_msg(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("❌ 환경변수가 설정되지 않았습니다.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    # 메시지가 너무 길면 잘릴 수 있으므로 주의 (현재 설정상 안전)
    payload = {'chat_id': chat_id, 'text': message}
    
    try:
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            print("✅ 텔레그램 메시지 전송 성공!")
        else:
            print(f"❌ 전송 실패: {res.text}")
    except Exception as e:
        print(f"❌ 에러: {e}")

# --- 4. 최종 실행 ---
if __name__ == "__main__":
    KEYWORDS = ["한화생명", "삼성생명", "교보생명", "생보사", "보험사"]
    EXCLUDES = ["배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원"]
    
    # 1. 크롤링 (사용자 코드 실행)
    news_list = crawl_naver_news_robust(KEYWORDS, exclude_words=EXCLUDES, pages=5)
    
    # 2. 형식 정리
    report_text = format_news_report(news_list)
    
    # 3. 출력 및 전송
    print("\n--- 생성된 리포트 ---")
    print(report_text)
    send_telegram_msg(report_text)
