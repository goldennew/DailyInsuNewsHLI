import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime

def crawl_naver_news_robust(base_keywords, include_words=None, exclude_words=None, pages=1):
    if isinstance(base_keywords, str): base_keywords = [base_keywords]
    
    # 깃허브 액션 서버임을 숨기기 위한 더 강력한 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.naver.com/'
    }

    query_parts = [f"({' | '.join(base_keywords)})"]
    if include_words: query_parts.append(" ".join([f"+{word}" for word in include_words]))
    if exclude_words: query_parts.append(" ".join([f"-{word}" for word in exclude_words]))
    query = " ".join(query_parts)

    results = []
    print(f"🔎 검색어: [{query}]")

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
            response = requests.get("https://search.naver.com/search.naver", headers=headers, params=params, timeout=10)
            
            # [디버그 1] 응답 코드 확인
            if response.status_code != 200:
                print(f"❌ 네이버 응답 에러 (Status Code: {response.status_code})")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # [디버그 2] 기사 제목 태그 직접 찾기 (선택자 단순화)
            # 네이버 뉴스 제목은 보통 'news_tit' 클래스를 가집니다.
            all_links = soup.find_all("a", class_="news_tit")
            
            if not all_links:
                # 클래스로 못 찾을 경우를 대비한 백업 (기존 방식)
                main_pack = soup.select_one("#main_pack")
                all_links = main_pack.find_all("a") if main_pack else []

            print(f"📡 {page+1}페이지에서 발견된 전체 링크 수: {len(all_links)}")

            found_in_page = 0
            for link in all_links:
                text = link.get_text().strip()
                href = link.get('href')

                # 필터링 조건
                if 10 < len(text) < 100 and href and href.startswith("http"):
                    # 제외 키워드 검사
                    if exclude_words and any(bad in text for bad in exclude_words): continue
                    
                    # 키워드 포함 검사
                    if not any(k in text for k in base_keywords): continue
                    
                    # 중복 검사
                    if any(r['url'] == href for r in results): continue

                    results.append({'title': text, 'url': href})
                    found_in_page += 1

            print(f"✅ {page+1}페이지 필터링 통과 기사: {found_in_page}건")
            if len(all_links) == 0: break
            time.sleep(1)

        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            break

    return results

def format_news_report(news_data):
    sector_invest = []
    sector_industry = []

    for item in news_data:
        title = item['title']
        if any(word in title for word in ['손익', '자산', '투자', '재무']):
            if len(sector_invest) < 5: sector_invest.append(item)
        else:
            if len(sector_industry) < 5: sector_industry.append(item)

    today = datetime.now().strftime("%Y-%m-%d")
    report = f"■News feed: {today}\n\n"
    
    report += "<생보3사/보험업계>\n\n"
    if not sector_industry: report += "(기사 없음)\n\n"
    for item in sector_industry: report += f"{item['title']}\n{item['url']}\n\n"
        
    report += "<투자손익/금융시장>\n\n"
    if not sector_invest: report += "(기사 없음)\n\n"
    for item in sector_invest: report += f"{item['title']}\n{item['url']}\n\n"
        
    return report

def send_telegram_msg(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      data={'chat_id': chat_id, 'text': message})
    except: pass

if __name__ == "__main__":
    KEYWORDS = ["한화생명", "삼성생명", "교보생명", "생보사", "보험사"]
    #EXCLUDES = ["배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원"]
    
    news_list = crawl_naver_news_robust(KEYWORDS, exclude_words=EXCLUDES, pages=5)
    print(f"📊 최종 수집된 기사 총합: {len(news_list)}건")
    
    report_text = format_news_report(news_list)
    print(report_text)
    send_telegram_msg(report_text)
