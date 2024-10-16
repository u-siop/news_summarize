import requests
from bs4 import BeautifulSoup
import re
import os
from openai import OpenAI
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from dotenv import load_dotenv

# 환경 변수에서 API 키 로드
load_dotenv()

# OpenAI API 설정
client = OpenAI(
    api_key=""
)

# 웹 페이지에서 텍스트 추출 함수
def scrape_webpage(url):
    response = requests.get(url)
    response.encoding = 'utf-8'  # 인코딩 설정
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 본문 내용 추출
    article_text = ' '.join([p.get_text() for p in soup.find_all('p')])
    
    return article_text

# GPT 응답을 파싱하는 함수
def parse_assistant_response(response_text):
    lines = response_text.strip().split('\n')
    headline = ''
    summary_lines = []
    hashtags = ''
    title_ideas = []

    current_section = None

    for line in lines:
        line = line.strip()
        if line.startswith('제목:'):
            headline = line[len('제목:'):].strip()
            current_section = None
        elif line.startswith('요약 문장'):
            current_section = 'summary'
        elif line.startswith('해시태그:'):
            hashtags = line[len('해시태그:'):].strip()
            current_section = None
        elif line.startswith('제목 아이디어'):
            current_section = 'title_ideas'
        elif re.match(r'\d+\.', line):
            if current_section == 'title_ideas':
                title_ideas.append(line[line.find('.')+1:].strip())
        else:
            if current_section == 'summary':
                summary_lines.append(line)

    summary = '\n'.join(summary_lines).strip()

    hashtags_list = hashtags.split()

    return {
        'headline': headline,
        'summary': summary,
        'hashtags': hashtags_list,
        'title_ideas': title_ideas
    }

# 기사 내용을 요약하는 함수
def summarize_article_content(content):
    prompt = f"""아래 형식에 맞추어 한국어로 요약해줘

[형식]
제목: (제목 내용)
요약 문장 :
첫 번째 문장
두 번째 문장
해시태그: #태그1 #태그2 #태그3
제목 아이디어 :
1. 제목 아이디어 1
2. 제목 아이디어 2
3. 제목 아이디어 3
4. 제목 아이디어 4
5. 제목 아이디어 5

[요약하는 방법]
1. 요약 문장은 두 문장으로 하고, 각각 최소 15단어 이상, 최대 30단어로 작성
2. 각 문장의 종결어미 형식은 '-임', '-함', '-라고 함', '-다고 함', '-음', '-하는 중' 등등 명사로 종결
3. 반드시 두 문장으로 해당 내용을 요약하고, 각 문장은 새로운 줄에서 시작해야 함
4. 제목 아이디어를 3~5개 추가적으로 만들고, 35자 이내로 작성
5. 위의 [형식]을 정확히 따라 작성

[예시]
제목 : 제주서 40대, 끊어진 전선에 감전 사고
요약 문장 :
제주 서귀포시에서 40대 남성이 끊어진 전선에 감전되어 부상을 입은 사고가 발생함.
A씨는 발가락에 2도 화상을 입고 전신 통증을 호소하며 병원에서 치료 중임.
해시태그: #제주사고 #감전사고 #안전주의
제목 아이디어:
1. 제주 감전 사고, 40대 남성 부상
2. 끊어진 전선, 제주서 감전 사고 발생
3. 제주서 길 걷던 40대, 전선에 감전
4. 서귀포서 발생한 감전 사고, 원인은?
5. 제주 감전 사고로 40대 병원 치료 중

다음은 요약할 텍스트: {content}
"""

    try:
        # OpenAI API 호출
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",  # 필요에 따라 모델 선택
            messages=[
                {"role": "system", "content": "You are a helpful news journalist that summarizes text to short news contents for SNS."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        
        # 응답 내용 추출
        summary_text = response.choices[0].message.content.strip()

        # 응답 파싱
        try:
            parsed_response = parse_assistant_response(summary_text)
            headline = parsed_response['headline']
            summary = parsed_response['summary']
            hashtags = parsed_response['hashtags']
            title_ideas = parsed_response['title_ideas']
            return {
                'headline': headline,
                'summary': summary,
                'hashtags': hashtags,
                'title_ideas': title_ideas
            }
        except Exception as e:
            print(f"Error parsing the response: {e}")
            return {
                'headline': "Failed to parse headline.",
                'summary': "Failed to parse summary.",
                'hashtags': [],
                'title_ideas': []
            }

    except Exception as e:
        print(f"Error generating content: {e}")
        return {
            'headline': "Failed to summarize.",
            'summary': "Failed to summarize.",
            'hashtags': [],
            'title_ideas': []
        }

# 뉴스 기사 목록을 요약하는 함수
def summarize_news_articles(articles):
    summarized_results = []
    
    for title, url in articles:
        print(f"Processing article: {title}")
        content = scrape_webpage(url.strip())
        
        # 내용이 너무 길 경우 자르기
        content = content[:4000]  # 모델 입력 제한에 따라 조정
        
        summary = summarize_article_content(content)
        
        summarized_results.append({
            'original_title': title,
            'link': url,
            'headline': summary['headline'],
            'summary': summary['summary'],
            'hashtags': summary['hashtags'],
            'title_ideas': summary['title_ideas']
        })
    
    return summarized_results

# 메인 함수
def main():
    # Selenium webdriver 설정 (자동으로 Chrome 드라이버 설치)
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    # 목표 URL
    url = "https://www.yna.co.kr/theme/mostviewed/index"
    driver.get(url)

    # 페이지 로딩 대기
    time.sleep(3)

    # 상위 5개의 뉴스 추출
    news_elements = driver.find_elements(By.CSS_SELECTOR, 'div.item-box01')[:10]

    # 뉴스 제목과 링크 추출
    top_5_news = []
    for news in news_elements:
        # 제목 추출
        title_element = news.find_element(By.CSS_SELECTOR, 'strong.tit-news')
        title = title_element.text
        
        # 링크 추출
        link_element = news.find_element(By.CSS_SELECTOR, 'a.tit-wrap')
        link = link_element.get_attribute('href')
        
        top_5_news.append((title, link))

    # 브라우저 종료
    driver.quit()

    # 뉴스 기사 요약 처리
    summarized_results = summarize_news_articles(top_5_news)

    # 결과를 txt 파일로 저장
    with open('news_summary.txt', 'w', encoding='utf-8') as f:
        for result in summarized_results:
            f.write("원본 제목 : " + result['original_title'] + '\n')
            f.write("링크 : " + result['link'] + '\n')
            f.write("------------------------------------\n")
            f.write("헤드라인 : " + result['headline'] + '\n')
            f.write("요약 : " + result['summary'] + '\n')
            f.write(' '.join(result['hashtags']) + '\n')
            # 제목 아이디어 5가지 작성
            f.write("헤드라인 아이디어 :\n")
            for idea in result['title_ideas']:
                f.write(idea + '\n')
            f.write("\n\n")

    # 완료 메시지 출력
    print("요약 결과가 'news_summary.txt' 파일로 저장되었습니다.")

# main 함수 호출
if __name__ == '__main__':
    main()
