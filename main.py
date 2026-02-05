import requests
import os
import html
from datetime import datetime

# ==========================================
# 🔑 API 키 설정 (직접 입력하거나 환경변수 사용)
# ==========================================
NAVER_CLIENT_ID = "여기에_Client_ID_입력"     # 예: "AbCdEfGhIjKlMnOpQrSt"
NAVER_CLIENT_SECRET = "여기에_Client_Secret_입력" # 예: "aBcDeFgHiJ"

# 보안을 위해 환경변수가 설정되어 있다면 그것을 우선 사용
if os.environ.get("NAVER_CLIENT_ID"):
    NAVER_CLIENT_ID = os.environ.get("2cC4xeZPfKKs3BVY_onT")
    NAVER_CLIENT_SECRET = os.environ.get("Z6pPs8GyhV")

def crawl_naver_news_api(keywords, display=30):
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    # 여러 키워드 중 하나라도 포함되면 검색되도록 OR 연산자(|) 사용일 수도 있으나,
    # 정확도를 위해 키워드를 합쳐서 검색하거나 루프를 돌릴 수 있습니다.
    # 여기서는 검색 결과의 다양성을 위해 OR 연산자처럼 동작하도록 쿼리를 구성합니다.
    # 예: "삼성생명" OR "한화생명" (검색어 사이 | 는 OR 연산)
    query = " | ".join(keywords)
    print(f"🔎 API 검색 시작: {query}")

    params = {
        "query": query,
        "display": display,  # 가져올 뉴스 개수 (최대 100)
        "start": 1,
        "sort": "date"       # date: 최신순, sim: 정확도순
    }

    results = []

    try:
        response = requests.get(url, headers=headers, params=params)
        
        # API 키 오류 등 체크
        if response.status_code == 401:
            print("❌ 인증 실패: Client ID와 Secret을 확인해주세요.")
            return []
        if response.status_code != 200:
            print(f"❌ 에러 발생 (코드: {response.status_code})")
            return []

        data = response.json()
        items = data.get('items', [])

        if not items:
            print("ℹ️ 검색 결과가 없습니다.")
            return []

        for item in items:
            # API 결과는 HTML 태그(<b> 등)와 특수문자(&quot;)가 섞여 있어 제거 필요
            raw_title = item['title']
            clean_title = html.unescape(raw_title).replace("<b>", "").replace("</b>", "")
            link = item['originallink'] if item['originallink'] else item['link']

            # 필터링: 제목 길이 5~100자
            if 5 < len(clean_title) < 100:
                results.append({'title': clean_title, 'url': link})

        print(f"✅ {len(results)}건의 기사 정보를 가져왔습니다.")

    except Exception as e:
        print(f"⚠️ 시스템 에러: {e}")

    return results

def format_news_report(news_data):
    sector_invest = []   # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    # 중복 제거를 위한 세트 (API는 간혹 중복을 줄 수 있음)
    seen_urls = set()

    for item in news_data:
        if item['url'] in seen_urls: continue
        seen_urls.add(item['url'])

        title = item['title']
        
        # 키워드 분류 로직
        invest_keywords = ['손익', '자산', '금융', '시장', '투자', '금리', '실적', '주가']
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
        print("🔔 텔레그램 토큰이 없어 메시지를 보내지 않습니다. (출력만 함)")
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
    # 검색 키워드
    KEYWORDS = ["삼성생명", "한화생명", "교보생명"]
    
    # API 실행
    if NAVER_CLIENT_ID == "여기에_Client_ID_입력":
        print("⚠️ 주의: 소스코드 상단의 NAVER_CLIENT_ID를 먼저 설정해주세요!")
    else:
        news_list = crawl_naver_news_api(KEYWORDS, display=40)
        final_msg = format_news_report(news_list)
        
        print("-" * 30)
        print(final_msg)
        print("-" * 30)
        
        send_telegram(final_msg)
