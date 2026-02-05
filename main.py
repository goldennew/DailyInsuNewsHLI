import requests
import os
import html
from datetime import datetime

# ==========================================
# 🔑 API 키 설정
# ※ 중요: 기존 키가 노출되었으므로 네이버 개발자 센터에서 반드시 재발급 받으세요!
# ==========================================
NAVER_CLIENT_ID = "2cC4xeZPfKKs3BVY_onT"
NAVER_CLIENT_SECRET = "21DmUYrAdX"

# 환경변수가 있다면 우선 사용
if os.environ.get("NAVER_CLIENT_ID"):
    NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

def crawl_naver_news_api(keywords, excludes=[], display=60):
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    # API 요청용 쿼리 (OR 연산)
    query = " | ".join(keywords)
    print(f"🔎 API 검색 요청: {query}")
    if excludes:
        print(f"🚫 제외 단어 목록: {excludes}")

    params = {
        "query": query,
        "display": display,  # 필터링으로 걸러질 것을 대비해 넉넉하게 요청 (60개)
        "start": 1,
        "sort": "date"       # date: 최신순
    }

    results = []

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
            raw_title = item['title']
            # HTML 태그 제거 및 특수문자 복원
            clean_title = html.unescape(raw_title).replace("<b>", "").replace("</b>", "")
            link = item['originallink'] if item['originallink'] else item['link']

            # -----------------------------------------------------------
            # 🔍 [강화된 필터링 로직]
            # -----------------------------------------------------------
            
            # 1. 제외 키워드(excludes)가 제목에 포함되면 즉시 건너뛰기
            if any(ex_word in clean_title for ex_word in excludes):
                continue

            # 2. 검색 키워드(keywords)가 제목에 '실제로' 포함되어 있는지 확인
            #    (API는 본문 내용으로도 검색하므로, 제목에 키워드가 없는 경우가 있음)
            if not any(key_word in clean_title for key_word in keywords):
                continue
            
            # 3. 제목 길이 필터링 (너무 짧거나 긴 것 제외)
            if 5 < len(clean_title) < 100:
                results.append({'title': clean_title, 'url': link})

        print(f"✅ 필터링 후 남은 기사: {len(results)}건")

    except Exception as e:
        print(f"⚠️ 시스템 에러: {e}")

    return results

def format_news_report(news_data):
    sector_invest = []   # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    seen_urls = set()

    for item in news_data:
        if item['url'] in seen_urls: continue
        seen_urls.add(item['url'])

        title = item['title']
        
        # 섹터 분류 키워드
        invest_keywords = ['손익', '자산', '금융', '시장', '투자', '금리', '실적', '주가', '배당']
        
        if any(k in title for k in invest_keywords):
            if len(sector_invest) < 5: sector_invest.append(item)
        else:
            if len(sector_industry) < 5: sector_industry.append(item)
    
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
    
    if not token or not chat_id:
        print("🔔 텔레그램 토큰 없음 (출력만 함)")
        print(message)
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
    # 1. 검색하고 싶은 핵심 키워드
    KEYWORDS = ["삼성생명", "한화생명", "교보생명", "생보사", "보험사"]
    
    # 2. 제목에 포함되면 무조건 제외할 키워드 (광고, 부고, 인사 등)
    EXCLUDES = ["부고", "배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원",]

    # API 실행
    if "Client_ID" in NAVER_CLIENT_ID:
        print("⚠️ 설정 오류: 소스코드 상단의 API 키를 먼저 입력해주세요.")
    else:
        # 필터링 때문에 버려지는 기사가 많을 수 있으므로 display를 60으로 늘림
        news_list = crawl_naver_news_api(KEYWORDS, excludes=EXCLUDES, display=70)
        
        final_msg = format_news_report(news_list)
        
        # 콘솔 출력 확인용
        print("-" * 30)
        print(final_msg)
        print("-" * 30)
        
        send_telegram(final_msg)
