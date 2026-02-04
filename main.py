import os
import requests
# ... (기존 import와 crawl_naver_news, format_news_feed 함수는 그대로 유지) ...

def send_telegram_message(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("❌ 텔레그램 토큰 또는 Chat ID가 설정되지 않았습니다.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown' # 또는 'HTML'
    }
    
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("✅ 텔레몬 메시지 전송 성공!")
        else:
            print(f"❌ 전송 실패: {response.text}")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    KEYWORDS = ["한화생명", "삼성생명", "교보생명", "생보사", "보험사"]
    EXCLUDES = ["배타적", "상품", "간병", "사업비", "보험금", "연금보험", "민원"]
    
    raw_news = crawl_naver_news(KEYWORDS, exclude_words=EXCLUDES, pages=5)
    final_report = format_news_feed(raw_news)
    
    # 1. 터미널 출력
    print(final_report)
    
    # 2. 텔레그램 전송 (추가됨)
    send_telegram_message(final_report)
    
    # 3. 파일 저장
    with open("daily_news_report.txt", "w", encoding="utf-8") as f:
        f.write(final_report)
