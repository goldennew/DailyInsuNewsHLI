import requests
import os
import html
import difflib
import time
import sys # 프로그램 종료를 위해 추가
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
# 📅 휴일 체크 함수 (추가됨)
# ==========================================
def is_skip_day():
    """
    오늘이 주말(토,일)이거나 지정된 공휴일이면 True를 반환
    """
    now_date = datetime.now().date()
    
    # 1. 주말 체크 (0:월 ~ 4:금, 5:토, 6:일)
    if now_date.weekday() >= 5:
        return True, "주말(토/일)"

    # 2. 공휴일 리스트 (YYYY-MM-DD 형식으로 수동 추가 필요)
    # 필요한 날짜를 이곳에 추가하세요. (2025~2026년 예시)
    holidays = [
        "2026-01-01", 
        "2026-02-17", "2026-02-18", "2026-02-19", # 설날
        "2026-03-01", "2026-03-02", # 삼일절 및 대체공휴일
        "2026-05-05", "2026-05-24", "2026-05-25", 
        "2026-06-06", "2026-08-15", 
        "2026-09-24", "2026-09-25", "2026-09-26", # 추석
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
        
        params = {
            "query": query,
            "display": req_display,
            "start": start,
            "sort": "date"
        }

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
                        time_diff = now - pub_date
                        if time_diff > timedelta(hours=12):
                            continue
                except Exception as e:
                    pass

                raw_title = item['title']
                clean_title = html.unescape(raw_title).replace("<b>", "").replace("</b>", "")
                
                raw_desc = item['description']
                clean_desc = html.unescape(raw_desc).replace("<b>", "").replace("</b>", "")
                
                link = item['originallink'] if item['originallink'] else item['link']

                if any(ex_word in clean_title for ex_word in excludes):
                    continue

                if not any(key_word in clean_title for key_word in target_keywords):
                    continue
                
                results.append({
                    'title': clean_title, 
                    'url': link, 
                    'desc': clean_desc,
                    'category': category_tag 
                })
            
            time.sleep(0.3) 

        except Exception as e:
            print(f"⚠️ 에러: {e}")
            break
            
    print(f"   👉 [{category_tag}] 수집 완료: {len(results)}건")
    return results

def remove_duplicates_globally(all_news):
    unique_news = []
    seen_urls = set()
    seen_descriptions = []

    print("🧹 전체 중복 제거 작업 중... (Market: 60자 / Insurance: 12자)")

    for item in all_news:
        if item['url'] in seen_urls:
            continue
            
        category = item.get('category', 'general')
        
        if category == 'market':
            threshold = 60  
        else:
            threshold = 12 
            
        is_content_dup = False
        for exist_desc in seen_descriptions:
            matcher = difflib.SequenceMatcher(None, item['desc'], exist_desc)
            match = matcher.find_longest_match(0, len(item['desc']), 0, len(exist_desc))
            
            if match.size >= threshold: 
                is_content_dup = True
                break
        
        if is_content_dup:
            continue

        seen_urls.add(item['url'])
        seen_descriptions.append(item['desc'])
        unique_news.append(item)

    print(f"✅ 최종 리포트 포함 기사: {len(unique_news)}건")
    return unique_news

def format_news_report(news_data):
    sector_invest = []   
    sector_industry = [] 

    for item in news_data:
        title = item['title']
        invest_keywords = ['손익', '실적', '투자', 'IR', '뉴욕증시', '코스피', '마감', '시황', '주가', '증시']
        
        if any(k in title for k in invest_keywords):
            sector_invest.append(item)
        else:
            sector_industry.append(item)
    
    now = datetime.now()
    days_kr = ["월", "화", "수", "목", "금", "토", "일"]
    day_of_week = days_kr[now.weekday()]
    
    today_str = f"{now.strftime('%Y.%m.%d')}({day_of_week})"
    
    report = f"■ News feed: {today_str}\n"
    
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
        print("🔔 텔레그램 설정 없음 (콘솔 출력)")
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id, 
            'text': message, 
            'disable_web_page_preview': True
        }
        requests.post(url, data=data)
        print("🚀 텔레그램 전송 완료")
    except Exception as e:
        print(f"텔레그램 전송 실패: {e}")

if __name__ == "__main__":
    # ------------------------------------------------
    # 0. 휴일/주말 체크 (추가됨)
    # ------------------------------------------------
    should_skip, reason = is_skip_day()
    if should_skip:
        print(f"⛔ 오늘은 '{reason}'이므로 뉴스를 발송하지 않고 종료합니다.")
        sys.exit() # 프로그램 종료

    # ------------------------------------------------
    # 1. 키워드 그룹 정의
    # ------------------------------------------------
    KEYWORDS_INSURANCE = ["삼성생명", "한화생명", "교보생명", "생보사", "보험사"]
    KEYWORDS_MARKET = ["마감시황", "마감 시황", "뉴욕증시","코스피","FOMC","금통위","한은"] 
    EXCLUDES = ["부고", "배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원", "출시", "손해사정",
                "채널 경쟁", "비급여", "원리금","보장형","IRP","증여","윤리","특약","경찰차","자동차"]
    EXCLUDES2 = []

    if "YOUR_CLIENT_ID" in NAVER_CLIENT_ID: 
         print("⚠️ 설정 오류: 소스코드 상단의 API 키를 본인의 키로 변경해주세요.")
    else:
        # ------------------------------------------------
        # 2. 그룹별 분리 수집 실행
        # ------------------------------------------------
        
        news_insurance = crawl_naver_news_api(
            KEYWORDS_INSURANCE, 
            excludes=EXCLUDES, 
            display_limit=60, 
            category_tag='insurance'
        )
        
        news_market = crawl_naver_news_api(
            KEYWORDS_MARKET, 
            excludes=EXCLUDES2, 
            display_limit=20, 
            category_tag='market'
        )
        news_market = news_market[:3] 
        print(f"   ✂️ 시황 뉴스는 최신 3개만 남기고 잘랐습니다.")

        # ------------------------------------------------
        # 3. 결과 합치기 및 차등 중복 제거
        # ------------------------------------------------
        combined_list = news_insurance + news_market
        final_list = remove_duplicates_globally(combined_list)
        
        # ------------------------------------------------
        # 4. 리포트 작성 및 전송
        # ------------------------------------------------
        final_msg = format_news_report(final_list)
        
        print("-" * 30)
        print(final_msg)
        print("-" * 30)
        
        send_telegram(final_msg)
