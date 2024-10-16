import requests
import re
from urllib.parse import urljoin
from datetime import datetime
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI

# OpenAI API 키 설정
client = OpenAI(
    
)

# 구텐베르크 알고리즘을 사용하기 위한 텍스트 밀도 계산 함수
def calculate_text_density(html_element):
    text_length = len(html_element.get_text(strip=True))
    tag_length = len(str(html_element))
    return text_length / max(tag_length, 1)

# 텍스트 밀도를 이용하여 뉴스 본문만을 스크랩하여 반환하는 함수
def scrape_webpage(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        html = response.text

        soup = BeautifulSoup(html, 'html.parser')

        # 태그 밀도가 높을 수 있는 사이드, 배너, 광고 등을 제거하기 위한 ID 및 클래스 목록
        unwanted_ids = [
            'newsSidebar', 'newsMainBanner', 'rightSlideDiv_1', 'rightSlideDiv_2', 'rightSlideDiv_3',
        ]
        unwanted_classes = [
            'sidebar', 'rankingNews', 'photo_slide', 'ad290x330', 'socialAD', 'AdIbl', 'rankingEmotion', 'user-aside',
            'ofhe_head', 'ofhe_body', 'outside_area_inner', 'outside_area', '_OUTSIDE_AREA', '_GRID_TEMPLATE_COLUMN_ASIDE', '_OUTSIDE_AREA_INNER',
        ]

        for unwanted_id in unwanted_ids:
            for tag in soup.find_all(id=unwanted_id):
                tag.decompose()

        for unwanted_class in unwanted_classes:
            for tag in soup.find_all(class_=unwanted_class):
                tag.decompose()

        candidate_blocks = soup.find_all(['div', 'article', 'section'])

        blocks_with_density = []
        for block in candidate_blocks:
            density = calculate_text_density(block)
            blocks_with_density.append((density, block))

        blocks_with_density.sort(key=lambda x: x[0], reverse=True)

        article_text = ""
        for density, block in blocks_with_density:
            if density > 0.1:
                for unwanted in block(['script', 'style', 'figure', 'iframe', 'br', 'noscript']):
                    unwanted.decompose()
                text = block.get_text(separator=' ', strip=True)
                if len(text) > len(article_text):
                    article_text = text
            else:
                break

        if len(article_text) < 700:
            paragraphs = soup.find_all('p')
            article_text = ' '.join([p.get_text(strip=True) for p in paragraphs])

        return article_text

    except Exception as e:
        print(f"웹페이지 스크래핑 중 오류 발생: {e}")
        return ""

# ChatGPT를 이용하여 뉴스 본문을 요약하고 파싱하는 함수
def parse_assistant_response(response_text):
    import re
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
        elif line.startswith('요약 문장:'):
            # '요약 문장:' 뒤에 내용이 바로 오는 경우 처리
            summary_content = line[len('요약 문장:'):].strip()
            if summary_content:
                summary_lines.append(summary_content)
            current_section = 'summary'
        elif line.startswith('해시태그:'):
            hashtags = line[len('해시태그:'):].strip()
            current_section = None
        elif line.startswith('제목 아이디어:'):
            current_section = 'title_ideas'
        elif re.match(r'^\d+\.', line):
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

# 스크랩해온 내용을 ChatGPT API에 넣어 요약하는 함수
def summarize_article_content(content):
    prompt = f"""아래 형식에 맞추어 한국어로 요약해줘

[형식]
제목: (제목 내용)
요약 문장:
(요약 내용)

해시태그: #태그1 #태그2 #태그3 #태그4 #태그5
제목 아이디어:
1. 제목 아이디어 1
2. 제목 아이디어 2
3. 제목 아이디어 3
4. 제목 아이디어 4
5. 제목 아이디어 5

[요약하는 방법]
1. 요약 내용은 총 3문단으로 나눠서 요약해줘
2. 각 문단은 3~5문장으로 구성해줘
3. 각 문장의 종결어미 형식: '-ㅁ', '-기' 등 명사형으로 종결하되 명사 그 자체로 종결할 수 있는 문장은 명사로 종결
4. 명사형 혹은 명사로 종결했을 때 마침표로 마무리
5. 각 문단은 줄바꿈 두 개로 구별, 각 문장은 줄바꿈으로 구별
6. 각 문단마다 문맥상 적절한 이모지를 추가
7. 내용을 담을 수 있는 해시태그를 5개  만들고 각각 3~4어절 이내의 해시태그를 만들고, 각 어절마다 띄어쓰기하기
8. 제목 아이디어를 5개 추가적으로 만들고, 35자 이내로 작성
9. 위의 [형식]을 정확히 따라 작성

다음은 요약할 텍스트: {content}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a helpful news letter artist that summarizes texts to midterm news contents for SNS."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.15,
        )

        summary_text = response.choices[0].message.content.strip()

        parsed_response = parse_assistant_response(summary_text)
        return parsed_response

    except Exception as e:
        print(f"요약 생성 중 오류 발생: {e}")
        return {
            'headline': "Failed to summarize.",
            'summary': "Failed to summarize.",
            'hashtags': [],
            'title_ideas': []
        }

def main():
    # 사용자 입력 받기
    site_url = input("분석할 뉴스 사이트의 URL을 입력하세요 : ").strip()

    # Selenium을 이용하여 웹 페이지에서 뉴스 정보를 가져옴
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    except Exception as e:
        print(f"Selenium WebDriver 초기화 중 오류 발생: {e}")
        return

    driver.get(site_url)
    time.sleep(3)

    driver.quit()

    news_context = scrape_webpage(site_url)
    print(f"Processing article: {site_url}")

    if not news_context:
        print(f"내용을 가져올 수 없어 스킵합니다: {site_url}")
        return

    news_context = news_context[:4000]

    summarized_result = summarize_article_content(news_context)

    # 파일명에 현재 날짜와 시간을 포함하여 저장
    current_time = datetime.now().strftime("%Y%m%d_%H%M")
    file_name = f"issue_briefing_{current_time}.txt"

    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write("헤드라인 : " + summarized_result['headline'] + '\n')
            f.write("요약 : " + summarized_result['summary'] + '\n')
            f.write("해시태그 : " + ' '.join(summarized_result['hashtags']) + '\n')
            f.write("제목 아이디어 :\n")
            for idea in summarized_result['title_ideas']:
                f.write(idea + '\n')
            f.write("\n\n")
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")
        return

    print(f"요약 결과가 '{file_name}' 파일로 저장되었습니다.")

if __name__ == "__main__":
    main()