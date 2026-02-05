import requests
import os
import html
import difflib
import time
from datetime import datetime

# ==========================================
# 🔑 API 키 설정
# ==========================================
# (보안을 위해 마스킹 처리했습니다. 본인의 키를 입력하세요)
NAVER_CLIENT_ID = "2cC4xeZPfKKs3BVY_onT"
NAVER_CLIENT_SECRET = "21DmUYrAdX"

if os.environ.get("NAVER_CLIENT_ID"):
    NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

def crawl_naver_news_api(target_keywords, excludes=[], display_limit=50, category_tag='general'):
    """
    category_tag: 'insurance' 또는 'market' 등 기사의 성격을 구분하는 태그 추가
    """
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
                raw_title = item['title']
                clean_title = html.unescape(raw_title).replace("<b>", "").replace("</b>", "")
                
                raw_desc = item['description']
                clean_desc = html.unescape(raw_desc).replace("<b>", "").replace("</b>", "")
                
                link = item['originallink'] if item['originallink'] else item['link']

                # 1. 제외 키워드 체크
                if any(ex_word in clean_title for ex_word in excludes):
                    continue

                # 2. 필수 키워드 체크 (제목 기준)
                if not any(key_word in clean_title for key_word in target_keywords):
                    continue
                
                # [수정] 결과에 카테고리 태그 추가
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
    """
    category별로 다른 글자 수 제한을 적용하여 중복 제거
    - Market: 30자 이상 겹치면 중복
    - Insurance: 15자 이상 겹치면 중복
    """
    unique_news = []
    seen_urls = set()
    seen_descriptions = []

    print("🧹 전체 중복 제거 작업 중... (Market: 30자 / Insurance: 15자)")

    for item in all_news:
        # 1. URL 중복 체크
        if item['url'] in seen_urls:
            continue
            
        # 2. 본문 내용 유사도 체크
        category = item.get('category', 'general')
        
        # [핵심 로직 변경] 카테고리에 따라 기준 글자 수(threshold) 다르게 설정
        if category == 'market':
            threshold = 60  # 시황은 상투적인 문구가 많으므로 30자까지 허용
        else:
            threshold = 12  # 보험은 15자만 겹쳐도 중복으로 처리
            
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
    sector_invest = []   # <투자손익/금융시장>
    sector_industry = [] # <생보3사/보험업계>

    for item in news_data:
        title = item['title']
        
        # 투자/시장 섹터로 보낼 키워드
        invest_keywords = ['손익', '실적', 'IR', '뉴욕증시', '코스피', '마감', '시황', '주가', '증시']
        
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
    # 1. 키워드 그룹 정의
    # ------------------------------------------------
    KEYWORDS_INSURANCE = ["삼성생명", "한화생명", "교보생명", "생보사", "보험사"]
    
    # [Tip] 시황 뉴스가 잘 안 잡히면 아래 키워드를 "증시", "코스피" 등으로 조금 더 넓히는 것도 좋습니다.
    KEYWORDS_MARKET = ["마감시황", "마감 시황", "뉴욕증시","코스피"] 
    
    EXCLUDES = ["부고", "배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원", "출시", "손해사정", "채널 경쟁", "비급여", "원리금","보장형","IRP"]
    EXCLUDES2 = []

    if "YOUR_CLIENT_ID" in NAVER_CLIENT_ID: # 마스킹된 부분 체크
         print("⚠️ 설정 오류: 소스코드 상단의 API 키를 본인의 키로 변경해주세요.")
    else:
        # ------------------------------------------------
        # 2. 그룹별 분리 수집 실행 (category_tag 추가)
        # ------------------------------------------------
        
        # A. 보험 뉴스 (태그: insurance)
        news_insurance = crawl_naver_news_api(
            KEYWORDS_INSURANCE, 
            excludes=EXCLUDES, 
            display_limit=60, 
            category_tag='insurance'
        )
        
        # B. 시황 뉴스 (태그: market) -> 최신 3개만 자르기
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
