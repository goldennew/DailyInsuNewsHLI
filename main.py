import requests
import os
import html
import difflib  # 텍스트 비교를 위한 모듈
from datetime import datetime

# ==========================================
# 🔑 API 키 설정
# ==========================================
NAVER_CLIENT_ID = "2cC4xeZPfKKs3BVY_onT"
NAVER_CLIENT_SECRET = "21DmUYrAdX"

if os.environ.get("NAVER_CLIENT_ID"):
    NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

def crawl_naver_news_api(keywords, excludes=[], display=60):
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    query = " | ".join(keywords)
    print(f"🔎 API 검색 요청: {query}")

    params = {
        "query": query,
        "display": display,
        "start": 1,
        "sort": "date"
    }

    results = []
    # 중복 검사를 위해 수집된 기사들의 본문(description)을 저장할 리스트
    collected_descriptions = []

    try:
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code != 200:
            print(f"❌ API 호출 에러 (코드: {response.status_code})")
            return []

        data = response.json()
        items = data.get('items', [])

        if not items:
            print("ℹ️ 검색 결과가 없습니다.")
            return []

        for item in items:
            # 1. 제목 및 본문 정제
            raw_title = item['title']
            clean_title = html.unescape(raw_title).replace("<b>", "").replace("</b>", "")
            
            raw_desc = item['description']
            clean_desc = html.unescape(raw_desc).replace("<b>", "").replace("</b>", "")
            
            link = item['originallink'] if item['originallink'] else item['link']

            # -----------------------------------------------------------
            # 🔍 [필터링 및 중복 제거 로직]
            # -----------------------------------------------------------
            
            # 1. 제외 키워드 체크
            if any(ex_word in clean_title for ex_word in excludes):
                continue

            # 2. 필수 키워드 체크 (제목 기준)
            if not any(key_word in clean_title for key_word in keywords):
                continue
            
            # 3. [요청 사항] 본문 내용 10자 이상 일치 시 중복 제거
            is_duplicate_content = False
            for exist_desc in collected_descriptions:
                # 두 텍스트 사이의 가장 긴 일치 구간 찾기
                matcher = difflib.SequenceMatcher(None, clean_desc, exist_desc)
                match = matcher.find_longest_match(0, len(clean_desc), 0, len(exist_desc))
                
                # 일치하는 구간의 길이가 10자 이상이면 중복으로 판단
                if match.size >= 10:
                    is_duplicate_content = True
                    break
            
            if is_duplicate_content:
                continue

            # 중복이 아니면 결과에 추가하고, 본문 비교 리스트에도 등록
            results.append({'title': clean_title, 'url': link, 'desc': clean_desc})
            collected_descriptions.append(clean_desc)

        print(f"✅ 중복 제거 후 남은 기사: {len(results)}건")

    except Exception as e:
        print(f"⚠️ 시스템 에러: {e}")

    return results

def format_news_report(news_data):
    sector_invest = []   # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    # URL 기준 2차 중복 제거 (혹시 모를 상황 대비)
    seen_urls = set()

    for item in news_data:
        if item['url'] in seen_urls: continue
        seen_urls.add(item['url'])

        title = item['title']
        
        # 키워드 분류
        invest_keywords = ['손익', '실적', '투자', 'IR', '뉴욕증시', '코스피']
        
        if any(k in title for k in invest_keywords):
            # [요청 사항] 개수 제한(len < 5) 조건 제거
            sector_invest.append(item)
        else:
            # [요청 사항] 개수 제한(len < 5) 조건 제거
            sector_industry.append(item)
    
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
    
    # 메시지가 너무 길 경우 텔레그램 전송 실패를 방지하기 위해 나누어 보낼 수도 있으나,
    # 여기서는 일단 한 번에 보냅니다. (텔레그램은 한 번에 약 4096자까지 전송 가능)
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
    KEYWORDS = ["삼성생명", "한화생명", "교보생명", "생보사", "보험사","마감시황", "마감 시황"]
    EXCLUDES = ["부고", "배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원", "출시","손해사정","채널 경쟁","비급여"]

    # API 실행
    if "API_ID" in NAVER_CLIENT_ID:
        print("⚠️ 설정 오류: 소스코드 상단의 API 키를 먼저 입력해주세요.")
    else:
        # display를 넉넉하게 100개로 설정
        news_list = crawl_naver_news_api(KEYWORDS, excludes=EXCLUDES, display=100)
        final_msg = format_news_report(news_list)
        
        print("-" * 30)
        print(final_msg)
        print("-" * 30)
        
        send_telegram(final_msg)
