import requests
from bs4 import BeautifulSoup
import anthropic
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from dotenv import load_dotenv

# .env 파일에서 환경 변수 로드
load_dotenv()

# Anthropic API 클라이언트 설정
client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY")
    )

# 웹페이지를 스크래핑하여 텍스트 추출하는 함수
def scrape_webpage(url):
    response = requests.get(url)
    response.encoding = 'utf-8'  # 올바른 인코딩 설정
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 주요 콘텐츠 추출
    article_text = ' '.join([p.get_text() for p in soup.find_all('p')])
    
    return article_text

# Claude API를 사용하여 기사 내용을 요약하는 함수
def summarize_article_content(content):
    # 캐주얼한 톤으로 명시적인 지침과 예시를 포함한 프롬프트 생성
    prompt = f"""아래 형식에 맞추어 한국어로 요약해줘

[형식]
제목: (제목 내용)
첫 번째 요약 문장: (첫 번째 요약 문장)
두 번째 요약 문장: (두 번째 요약 문장)
해시태그: #태그1 #태그2 #태그3
제목 아이디어:
1. 제목 아이디어 1
2. 제목 아이디어 2
3. 제목 아이디어 3
4. 제목 아이디어 4
5. 제목 아이디어 5

[요약하는 방법]
1. 첫 번째, 두 번째 요약 문장은 각각 최소 15단어 이상, 최대 30단어로 작성
2. 각 문장의 종결어미 형식은 '-임', '-함', '-라고 함', '-다고 함' '-음', '-하는 중' 등등 명사로 종결
3. 반드시 두 문장으로 해당 내용을 요약
4. 제목 아이디어를 3~5개 추가적으로 만들고, 35자 이내로 작성
5. 위의 [형식]을 정확히 따라 작성

다음은 요약할 텍스트: {content}
"""

    try:
        # Claude API에 프롬프트를 전송하여 요약 생성
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",  # 사용 가능한 최신 모델로 변경 가능
            system="You are a helpful news reporter that summarizes text to short news contents for the SNS.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            max_tokens=4096,
            temperature=0.3,
        )
        summary_text = response.content[0].text
        print(summary_text)

        # 예상되는 형식에 따라 응답을 파싱
        try:
            # 정규식을 사용하여 섹션 추출
            title_match = re.search(r'(?:제목|[[]제목[]]):\s*(.*)', summary_text, re.IGNORECASE)
            summary_match = re.search(r'(?:요약|[[]요약[]])(?:하는 방법)?\s*(.*?)(?:\s*해시태그:|\s*$)', summary_text, re.DOTALL | re.IGNORECASE)
            hashtags_match = re.search(r'(?:해시태그|[[]해시태그[]]):\s*(.*)', summary_text, re.IGNORECASE)

            headline = title_match.group(1).strip() if title_match else 'No headline found'
            summary_text = summary_match.group(1).strip() if summary_match else 'No summary found'
            # 요약을 문장별로 분리
            summary_sentences = [s.strip() for s in summary_text.strip().split('\n') if s.strip()]
            # 정확히 두 문장만 사용
            if len(summary_sentences) >= 2:
                summary = '\n\n'.join(summary_sentences[:2])
            else:
                summary = '\n\n'.join(summary_sentences)
            hashtags = hashtags_match.group(1).strip().split() if hashtags_match else []

            return {
                'headline': headline,
                'summary': summary,
                'hashtags': hashtags
            }
        except Exception as e:
            print(f"Error parsing the response: {e}")
            return {
                'headline': "Failed to parse headline.",
                'summary': "Failed to parse summary.",
                'hashtags': []
            }

    except Exception as e:
        print(f"Error generating content: {e}")
        return {
            'headline': "Failed to summarize.",
            'summary': "Failed to summarize.",
            'hashtags': []
        }

# 기사 목록을 받아 요약하는 메인 함수
def summarize_news_articles(articles):
    summarized_results = []
    
    for title, url in articles:
        content = scrape_webpage(url.strip())
        
        # 토큰 제한을 피하기 위해 콘텐츠를 자름 (필요에 따라 조정)
        content = content[:4000]  # 모델의 입력 제한에 따라 조정
        
        summary = summarize_article_content(content)
        
        summarized_results.append({
            'original_text': title,
            'headline': summary['headline'],
            'summary': summary['summary'],
            'hashtags': summary['hashtags']
        })
    
    return summarized_results

# Selenium 웹드라이버 설정 (자동으로 Chrome 드라이버 다운로드)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# 대상 URL
url = "https://www.mk.co.kr/news/ranking/"
driver.get(url)

# 페이지가 완전히 로드될 때까지 대기
time.sleep(3)

# 상위 5개 뉴스 아이템 추출
news_elements = driver.find_elements(By.CSS_SELECTOR, 'li.popular_top_node')[:1]

# 뉴스 제목과 링크 추출
top_5_news = []
for news in news_elements:
    # 뉴스 제목과 링크 추출
    title = news.find_element(By.CSS_SELECTOR, 'h3.news_ttl').text
    link = news.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
    top_5_news.append((title, link))

# 브라우저 종료
driver.quit()

# 뉴스 기사 처리
summarized_results = summarize_news_articles(top_5_news)

# 결과 출력
# 결과 출력
for result in summarized_results:
    print("Original Text:", result['original_text'])
    print("Headline:", result['headline'])
    print("Summary:", result['summary'])
    print("Hashtags:", ' '.join(result['hashtags']))
    print("Raw content length:", len(result.get('raw_content', '')))  # 원본 콘텐츠 길이 출력
    print("\n")