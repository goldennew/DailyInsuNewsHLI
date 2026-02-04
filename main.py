import requests
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime, timedelta

def parse_naver_time(time_str):
    """네이버의 'n시간 전', '1일 전' 등 텍스트를 datetime 객체로 변환"""
    now = datetime.now()
    try:
        if '분 전' in time_str:
            minutes = int(time_str.replace('분 전', '').strip())
            return now - timedelta(minutes=minutes)
        elif '시간 전' in time_str:
            hours = int(time_str.replace('시간 전', '').strip())
            return now - timedelta(hours=hours)
        elif '일 전' in time_str:
            days = int(time_str.replace('일 전', '').strip())
            return now - timedelta(days=days)
        elif '.' in time_str: # 예: 2026.02.04.
            return datetime.strptime(time_str.strip('. '), '%Y.%m.%d')
        return now # 매칭되지 않으면 현재 시간으로 반환
    except:
        return now

def crawl_naver_news_robust(keywords, pages=3):
    base_url = "https://m.search.naver.com/search.naver"
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
        'Accept-Language': 'ko-kr',
        'Referer': 'https://m.naver.com/'
    }

    results = []
    query = " ".join(keywords)
    
    # --- 필터 기준 설정 (현재로부터 36시간 전) ---
    limit_time = datetime.now() - timedelta(hours=36)
    print(f"🔎 검색 시작: {query}")
    print(f"⏰ 필터 기준: {limit_time.strftime('%Y-%m-%d %H:%M')} 이후 기사만 수집")

    for page in range(pages):
        start = (page * 15) + 1
        params = {
            'where': 'm_news',
            'query': query,
            'sm': 'mtb_opt',
            'sort': '1', # 최신순
            'nso': 'so:dd,p:2d', # 네이버 옵션은 2일로 넉넉하게 설정
            'start': start
        }

        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=15)
            if response.status_code != 200: continue

            soup = BeautifulSoup(response.text, 'html.parser')
            news_items = soup.select("div.news_wrap") or soup.select("li.bx")

            found_in_page = 0
            for item in news_items:
                title_tag = item.select_one("a.news_tit") or item.select_one("div.api_txt_lines.tit")
                time_tag = item.select_one("span.sub_txt") # 시간 정보가 담긴 태그
                
                if not title_tag: continue
                
                text = title_tag.get_text().strip()
                href = title_tag.get('href') if title_tag.has_attr('href') else title_tag.parent.get('href')
                raw_time = time_tag.get_text().strip() if time_tag else "알 수 없음"

                # 1. 시간 필터링 (36시간 이내 여부)
                article_time = parse_naver_time(raw_time)
                if article_time < limit_time:
                    # 36시간보다 오래된 기사라면 건너뜁니다.
                    continue

                # 2. 제목 길이 필터 (10~100자)
                if 10 < len(text) < 100 and href and href.startswith("http"):
                    if any(r['url'] == href for r in results): continue
                    
                    results.append({'title': text, 'url': href, 'time': raw_time})
                    found_in_page += 1

            print(f"📄 {page+1}페이지: {found_in_page}건 수집 완료")
            if found_in_page == 0 and page > 0: break # 더 이상 최신 기사가 없으면 종료
            
            time.sleep(1.0)

        except Exception as e:
            print(f"⚠️ 에러 발생: {e}")
            break

    return results

def format_news_report(news_data):
    sector_invest = []   # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    for item in news_data:
        title = item['title']
        if '손익' in title or '자산' in title:
            if len(sector_invest) < 5: sector_invest.append(item)
        else:
            if len(sector_industry) < 5: sector_industry.append(item)
    
    today = datetime.now().strftime("%Y-%m-%d")
    report = f"■News feed: {today}\n"
    
    report += "\n<생보3사/보험업계>\n\n"
    if not sector_industry: report += "(36시간 이내 관련 기사 없음)\n\n"
    for item in sector_industry:
        report += f"{item['title']}\n{item['url']}\n\n"
        
    report += "<투자손익/금융시장>\n\n"
    if not sector_invest: report += "(36시간 이내 관련 기사 없음)\n\n"
    for item in sector_invest:
        report += f"{item['title']}\n{item['url']}\n\n"
        
    return report

def send_telegram(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id: return
    try:
        # 메시지가 너무 길면 텔레그램에서 거부할 수 있으므로 4000자로 자름
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                      data={'chat_id': chat_id, 'text': message[:4000], 'disable_web_page_preview': True})
    except: pass

if __name__ == "__main__":
    KEYWORDS = ["삼성생명", "한화생명", "교보생명", "보험사"]
    news_list = crawl_naver_news_robust(KEYWORDS, pages=3)
    final_msg = format_news_report(news_list)
    
    print(final_msg)
    send_telegram(final_msg)
