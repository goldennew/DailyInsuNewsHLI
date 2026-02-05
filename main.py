import requests
import os
import html
import difflib
import time
from datetime import datetime

# ==========================================
# 🔑 API 키 설정
# ==========================================
NAVER_CLIENT_ID = "2cC4xeZPfKKs3BVY_onT"
NAVER_CLIENT_SECRET = "21DmUYrAdX"

if os.environ.get("NAVER_CLIENT_ID"):
    NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

def crawl_naver_news_api(target_keywords, excludes=[], display_limit=50):
    """
    특정 키워드 그룹에 대해서만 뉴스를 수집하는 함수
    """
    url = "https://openapi.naver.com/v1/search/news.json"
    
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    
    # 해당 그룹의 키워드로 쿼리 생성
    query = " | ".join(target_keywords)
    print(f"🔎 검색 시작: [{query}] (최대 {display_limit}건)")

    results = []
    
    # display_limit 만큼 가져오기 위해 반복 계산 (API 1회 최대 100개)
    loop_count = (display_limit // 100) + 1 if display_limit % 100 != 0 else (display_limit // 100)
    
    for i in range(loop_count):
        # 이번 턴에 요청할 개수 계산
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
                raw_title = item['title']
                clean_title = html.unescape(raw_title).replace("<b>", "").replace("</b>", "")
                
                raw_desc = item['description']
                clean_desc = html.unescape(raw_desc).replace("<b>", "").replace("</b>", "")
                
                link = item['originallink'] if item['originallink'] else item['link']

                # 1. 제외 키워드(광고, 부고 등) 체크
                if any(ex_word in clean_title for ex_word in excludes):
                    continue

                # 2. 필수 키워드 체크 (검색한 그룹의 키워드가 제목에 있는지)
                if not any(key_word in clean_title for key_word in target_keywords):
                    continue
                
                # (개별 그룹 수집 단계에서는 일단 다 모읍니다. 중복 제거는 합친 후에 합니다.)
                results.append({'title': clean_title, 'url': link, 'desc': clean_desc})
            
            time.sleep(0.3) # API 호출 간 예의

        except Exception as e:
            print(f"⚠️ 에러: {e}")
            break
            
    print(f"   👉 [{query[:15]}...] 그룹 수집 완료: {len(results)}건")
    return results

def remove_duplicates_globally(all_news):
    """
    합쳐진 전체 뉴스 리스트에서 중복(URL 및 내용)을 제거
    """
    unique_news = []
    seen_urls = set()
    seen_descriptions = []

    print("🧹 전체 중복 제거 및 정제 작업 시작...")

    for item in all_news:
        # 1. URL 중복 체크 (완전 동일 기사)
        if item['url'] in seen_urls:
            continue
            
        # 2. 본문 내용 유사도 체크 (30자 이상 겹치면 중복 처리)
        is_content_dup = False
        for exist_desc in seen_descriptions:
            matcher = difflib.SequenceMatcher(None, item['desc'], exist_desc)
            match = matcher.find_longest_match(0, len(item['desc']), 0, len(exist_desc))
            
            if match.size >= 30: # 30자 이상 겹치면 중복
                is_content_dup = True
                break
        
        if is_content_dup:
            continue

        # 중복이 아니면 등록
        seen_urls.add(item['url'])
        seen_descriptions.append(item['desc'])
        unique_news.append(item)

    print(f"✅ 최종 유효 기사: {len(unique_news)}건")
    return unique_news

def format_news_report(news_data):
    sector_invest = []   # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    for item in news_data:
        title = item['title']
        
        # 분류 키워드 (제목에 이 단어가 있으면 '투자/시장' 섹터로 분류)
        invest_keywords = ['손익', '실적', '투자', 'IR', '뉴욕증시', '코스피', '마감', '시황', '주가', '증시']
        
        if any(k in title for k in invest_keywords):
            sector_invest.append(item)
        else:
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
    # 1. 키워드 그룹 정의 (별도 검색을 위해 분리)
    # ------------------------------------------------
    # 그룹 A: 보험사 관련 (여기서 50개 수집)
    KEYWORDS_INSURANCE = ["삼성생명", "한화생명", "교보생명", "생보사", "보험사"]
    
    # 그룹 B: 시황 관련 (여기서 50개 수집)
    KEYWORDS_MARKET = ["마감시황", "마감 시황"]
    
    # 공통 제외어
    EXCLUDES = ["부고", "배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원", "출시", "손해사정", "채널 경쟁", "비급여", "인사", "동정"]

    if "API_ID" in NAVER_CLIENT_ID:
        print("⚠️ 설정 오류: 소스코드 상단의 API 키를 먼저 입력해주세요.")
    else:
        # ------------------------------------------------
        # 2. 그룹별 분리 수집 실행
        # ------------------------------------------------
        # A. 보험 뉴스 60개 수집
        news_insurance = crawl_naver_news_api(KEYWORDS_INSURANCE, excludes=EXCLUDES, display_limit=60)
        
        # B. 시황 뉴스 60개 수집
        news_market = crawl_naver_news_api(KEYWORDS_MARKET, excludes=EXCLUDES, display_limit=60)
        
        # ------------------------------------------------
        # 3. 결과 합치기 및 전체 중복 제거
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
