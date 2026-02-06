import requests
import os
import html
import difflib
import time
import sys
from datetime import datetime, timedelta

# ==========================================
# 🔑 API 키 설정
# ==========================================
NAVER_CLIENT_ID = "2cC4xeZPfKKs3BVY_onT"
NAVER_CLIENT_SECRET = "21DmUYrAdX"

if os.environ.get("NAVER_CLIENT_ID"):
    NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

# ==========================================
# 📅 휴일 체크 함수
# ==========================================
def is_skip_day():
    now_date = datetime.now().date()
    
    if now_date.weekday() >= 5:
        return True, "주말(토/일)"

    holidays = [
        "2026-01-01", 
        "2026-02-17", "2026-02-18", "2026-02-19",
        "2026-03-01", "2026-03-02",
        "2026-05-05", "2026-05-24", "2026-05-25", 
        "2026-06-06", "2026-08-15", 
        "2026-09-24", "2026-09-25", "2026-09-26",
        "2026-10-03", "2026-10-09", "2026-12-25"
    ]
    
    if str(now_date) in holidays:
        return True, "지정 공휴일"

    return False, ""

def crawl_naver_news_api(target_keywords, excludes=[], display_limit=50, category_tag='general'):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    query = " | ".join(target_keywords)
    print(f"🔎 [{category_tag}] 검색 시작: {query} (요청 {display_limit}건)")

    results = []
    loop_count = (display_limit // 100) + 1 if display_limit % 100 != 0 else (display_limit // 100)
    
    for i in range(loop_count):
        req_display = 100 if display_limit > 100 else display_limit
        display_limit -= req_display
        start = (i * 100) + 1
        
        params = {"query": query, "display": req_display, "start": start, "sort": "date"}

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                print(f"❌ API 호출 에러: {response.status_code}")
                break

            items = response.json().get('items', [])
            if not items: break

            for item in items:
                pub_date_str = item['pubDate']
                try:
                    pub_date = datetime.strptime(pub_date_str, "%a, %d %b %Y %H:%M:%S %z")
                    if category_tag == 'market':
                        now = datetime.now(pub_date.tzinfo)
                        if (now - pub_date) > timedelta(hours=12):
                            continue
                except:
                    pass

                raw_title = item['title']
                clean_title = html.unescape(raw_title).replace("<b>", "").replace("</b>", "")
                
                raw_desc = item['description']
                clean_desc = html.unescape(raw_desc).replace("<b>", "").replace("</b>", "")
                
                link = item['originallink'] if item['originallink'] else item['link']

                if any(ex_word in clean_title for ex_word in excludes): continue
                if not any(key_word in clean_title for key_word in target_keywords): continue
                
                results.append({'title': clean_title, 'url': link, 'desc': clean_desc, 'category': category_tag})
            time.sleep(0.3) 
        except Exception as e:
            print(f"⚠️ 에러: {e}")
            break
            
    return results

def remove_duplicates_globally(all_news):
    unique_news = []
    seen_urls = set()
    seen_descriptions = []

    print("🧹 중복 제거 중...")

    for item in all_news:
        if item['url'] in seen_urls: continue
            
        category = item.get('category', 'general')
        threshold = 60 if category == 'market' else 12
            
        is_content_dup = False
        for exist_desc in seen_descriptions:
            matcher = difflib.SequenceMatcher(None, item['desc'], exist_desc)
            if matcher.find_longest_match(0, len(item['desc']), 0, len(exist_desc)).size >= threshold: 
                is_content_dup = True
                break
        
        if is_content_dup: continue

        seen_urls.add(item['url'])
        seen_descriptions.append(item['desc'])
        unique_news.append(item)

    return unique_news

# ==========================================
# 🛠️ 수정된 부분: 특수문자(<, >) 처리
# ==========================================
def format_news_report(news_data):
    sector_invest = []   
    sector_industry = [] 

    for item in news_data:
        title = item['title']
        # 기사 제목의 <, > 도 안전하게 변환
        safe_title = html.escape(title)
        item['safe_title'] = safe_title
        
        invest_keywords = ['손익', '실적', '투자', 'IR', '뉴욕증시', '코스피', '마감', '시황', '주가', '증시']
        
        if any(k in title for k in invest_keywords):
            sector_invest.append(item)
        else:
            sector_industry.append(item)
    
    now = datetime.now()
    days_kr = ["월", "화", "수", "목", "금", "토", "일"]
    today_str = f"{now.strftime('%Y.%m.%d')}({days_kr[now.weekday()]})"
    
    report = f"<b>■ News feed: {today_str}</b>\n\n"
    
    # 🚨 여기가 문제였음! < > 를 &lt; &gt; 로 변경
    report += "<b>&lt;생보3사/보험업계&gt;</b>\n" 
    if not sector_industry: report += "(기사 없음)\n"
    for item in sector_industry:
        report += f"• <a href='{item['url']}'>{item['safe_title']}</a>\n"
        
    # 🚨 여기도 변경
    report += "\n<b>&lt;투자손익/금융시장&gt;</b>\n"
    if not sector_invest: report += "(기사 없음)\n"
    for item in sector_invest:
        report += f"• <a href='{item['url']}'>{item['safe_title']}</a>\n"
        
    return report

def send_telegram(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("🔔 텔레그램 설정 없음")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id, 
            'text': message, 
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            print("🚀 텔레그램 전송 완료")
        else:
            print(f"❌ 전송 실패 (Code: {response.status_code})")
            print(f"👉 원인: {response.text}")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

if __name__ == "__main__":
    should_skip, reason = is_skip_day()
    if should_skip:
        print(f"⛔ 오늘은 '{reason}'이므로 종료합니다.")
        sys.exit()

    KEYWORDS_INSURANCE = ["삼성생명", "한화생명", "교보생명", "생보사", "보험사"]
    KEYWORDS_MARKET = ["마감시황", "마감 시황", "뉴욕증시","코스피","FOMC","금통위","한은"] 
    EXCLUDES = ["부고", "배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원", "출시", "손해사정",
                "채널 경쟁", "비급여", "원리금", "보장형", "IRP", "증여", "자동차", "특약", "윤리","소비자"]
    
    if "YOUR_CLIENT_ID" in NAVER_CLIENT_ID: 
         print("⚠️ API 키를 설정해주세요.")
    else:
        news_insurance = crawl_naver_news_api(KEYWORDS_INSURANCE, excludes=EXCLUDES, display_limit=60, category_tag='insurance')
        news_market = crawl_naver_news_api(KEYWORDS_MARKET, excludes=[], display_limit=20, category_tag='market')
        news_market = news_market[:3] 

        final_list = remove_duplicates_globally(news_insurance + news_market)
        final_msg = format_news_report(final_list)
        
        print("-" * 30)
        print(final_msg)
        print("-" * 30)
        
        send_telegram(final_msg)
        
