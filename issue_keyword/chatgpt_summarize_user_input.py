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

# OpenAI API key 설정
client = OpenAI(

)

# 연합뉴스가 아닌 다른 랭킹 뉴스 사이트에서 제목과 링크를 뽑기 위한 ChatGPT API 프롬프트 생성 함수
def create_prompt(elements_info, num_of_summary):
    prompt = (
        "다음은 웹 페이지의 요소들입니다. 각 요소의 인덱스, 텍스트, HTML, 링크 URL이 주어집니다.\n"
        "각 요소가 뉴스 헤드라인인지, 뉴스 링크인지, 또는 무시해야 하는지 판단하고, "
        "뉴스 헤드라인과 링크에 해당하는 요소를 출력하세요.\n"
        f"상위 {num_of_summary}개의 뉴스만 제공하세요.\n\n"
        "요소들:\n"
    )

    for elem in elements_info:
        prompt += (
            f"인덱스: {elem['index']}\n"
            f"텍스트: {elem['text']}\n"
            f"HTML: {elem['html']}\n"
        )
        if elem.get('href'):
            prompt += f"링크: {elem['href']}\n"
        prompt += "\n\n"

    prompt += (
        "[출력 형식]\n"
        "제목: [제목 텍스트]\n링크: [링크 URL]\n\n"
        "[예시]\n"
        "제목: 최태원 SK회장 차녀, ‘예비신랑’과 인연 이것 때문이라는데…\n"
        "링크: https://www.mk.co.kr/news/society/11135856\n"
        "제목: 부산 중학생, 등 40㎝ 찢겼는데 '수술할 의사 없다'…부산서 대전까지 간 중학생\n"
        "링크: https://news.nate.com/view/20241010n09975?mid=n1006\n"
    )
    return prompt

# ChatGPT API로부터 받아온 제목과 링크를 파싱하는 함수
def parse_gpt_response(response_text):
    news_list = []
    lines = response_text.strip().split('\n')
    current_title = None
    current_link = None

    for line in lines:
        line = line.strip()
        if line.startswith("제목:") or re.match(r"^\d+\.\s*제목\s*:", line):
            line = re.sub(r"^\d+\.\s*", "", line)
            current_title = line.replace("제목:", "").strip()
        elif line.startswith("링크:"):
            current_link = line.replace("링크:", "").strip()

        if current_title and current_link:
            news_list.append({
                'title': current_title,
                'link': current_link
            })
            current_title = None
            current_link = None

    return news_list

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

        # 태그 밀도가 높을 수 있는 사이드, 배너, 광고 등을 수작업으로 제거하기 위한 ID 및 클래스 목록
        unwanted_ids = [
            'newsSidebar', 'newsMainBanner', 'rightSlideDiv_1', 'rightSlideDiv_2', 'rightSlideDiv_3',
        ]
        unwanted_classes = [
            'sidebar', 'rankingNews', 'photo_slide', 'ad290x330', 'socialAD', 'AdIbl', 'rankingEmotion',
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

        if len(article_text) < 200:
            paragraphs = soup.find_all('p')
            article_text = ' '.join([p.get_text(strip=True) for p in paragraphs])

        return article_text

    except Exception as e:
        print(f"웹페이지 스크래핑 중 오류 발생: {e}")
        return ""

# ChatGPT를 이용하여 뉴스 본문을 요약하고 파싱하는 함수
def parse_assistant_response(response_text):
    lines = response_text.strip().split('\n')
    headline = ''
    summary_lines = []
    hashtags = ''
    title_ideas = []
    representative_hashtags = []
    representative_hashtag_ideas = []

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
        elif line.startswith('대표해시태그:'):
            representative_hashtags = line[len('대표해시태그:'):].strip().split()
            current_section = None
        elif line.startswith('제목 아이디어'):
            current_section = 'title_ideas'
        elif line.startswith('대표해시태그 아이디어'):
            current_section = 'representative_hashtag_ideas'
        elif re.match(r'\d+\.', line):
            if current_section == 'title_ideas':
                title_ideas.append(line[line.find('.')+1:].strip())
            elif current_section == 'representative_hashtag_ideas':
                representative_hashtag_ideas.append(line[line.find('.')+1:].strip())
        else:
            if current_section == 'summary':
                summary_lines.append(line)

    summary = '\n'.join(summary_lines).strip()
    hashtags_list = hashtags.split()

    return {
        'headline': headline,
        'summary': summary,
        'hashtags': hashtags_list,
        'title_ideas': title_ideas,
        'representative_hashtags': representative_hashtags,
        'representative_hashtag_ideas': representative_hashtag_ideas
    }

# 스크랩해온 내용을 ChatGPT API에 넣어 요약하는 함수
def summarize_article_content(content):
    prompt = f"""아래 형식에 맞추어 한국어로 요약해줘

[형식]
제목: (제목 내용)
요약 문장:
첫 번째 문장
두 번째 문장
해시태그: #태그1 #태그2 #태그3
대표해시태그: #대표해시태그
제목 아이디어:
1. 제목 아이디어 1
2. 제목 아이디어 2
3. 제목 아이디어 3
4. 제목 아이디어 4
5. 제목 아이디어 5
대표해시태그 아이디어:
1. 대표해시태그 아이디어 1
2. 대표해시태그 아이디어 2
3. 대표해시태그 아이디어 3

[요약하는 방법]
1. 요약 문장은 두 문장으로 하고, 각각 최소 15단어 이상, 최대 30단어로 작성
2. 각 문장의 종결어미 형식: '-ㅁ', '-기' 등 명사형으로 종결하되 명사 그 자체로 종결할 수 있는 문장은 명사로 종결
3. 명사형 혹은 명사로 종결했을 때 마침표로 마무리
4. 반드시 두 문장으로 해당 내용을 요약하고, 각 문장은 새로운 줄에서 시작해야 함
5. 제목 아이디어를 3~5개 추가적으로 만들고, 35자 이내로 작성
6. 위의 [형식]을 정확히 따라 작성
7. 대표해시태그는 뉴스 전체를 대표할 수 있는 3어절 이내의 대표해시태그를 추가
8. 대표해시태그 아이디어를 3개, 3어절 이내, 각 어절은 띄어쓰기로 구별

[예시]
원본 제목 : “곳곳에 빈집, 이 동네 심상치 않네”…미분양 가구 5년 새 13배 폭증한 이곳
링크 : https://www.mk.co.kr/news/business/11139586
------------------------------------
제목: 광주 미분양 아파트 5년 만에 13배 증가
요약 문장:
광주 지역의 미분양 아파트 수가 5년 전보다 13배 증가하며 건설업계의 자금난이 심화되고 있음.
정부의 규제 완화와 공공공사 확대 등 정책적 지원이 필요하다고 전문가들은 강조함.
해시태그: #광주미분양 #건설업위기 #정책지원필요
대표해시태그: #광주 미분양 위기
제목 아이디어:
1. 광주 미분양 아파트 급증, 건설업계 위기
2. 5년 만에 13배 증가한 광주 미분양
3. 광주 미분양 사태, 건설업계 자금난 심화
4. 광주 미분양 문제, 정부 지원 절실
5. 광주 미분양 증가, 건설업계 대책 필요
대표해시태그 아이디어:
1. #건설업계 자금난
2. #정부지원 필요
3. #광주 미분양 사태

다음은 요약할 텍스트: {content}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": "You are a helpful news journalist that summarizes text to short news contents for SNS."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.3,
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
            'title_ideas': [],
            'representative_hashtags': [],
            'representative_hashtag_ideas': []
        }

def summarize_news_articles(news_items):
    summarized_results = []

    for item in news_items:
        title = item['title']
        link = item['link']

        print(f"Processing article: {title}")
        content = scrape_webpage(link.strip())

        if not content:
            print(f"내용을 가져올 수 없어 스킵합니다: {link}")
            continue

        content = content[:4000]

        summary = summarize_article_content(content)

        summarized_results.append({
            'original_title': title,
            'link': link,
            'headline': summary['headline'],
            'summary': summary['summary'],
            'hashtags': summary['hashtags'],
            'title_ideas': summary['title_ideas'],
            'representative_hashtags': summary['representative_hashtags'],
            'representative_hashtag_ideas': summary['representative_hashtag_ideas']
        })

    return summarized_results

def main():
    # 사용자 입력 받기
    site_url = input("분석할 뉴스 사이트의 URL을 입력하세요 : (default : 연합뉴스) ").strip()
    if not site_url:
        site_url = "https://www.yna.co.kr/theme/mostviewed/index"
        use_default = True
    else:
        use_default = False

    # 요약할 뉴스 개수 입력 받기
    while True:
        num_of_summary_input = input("요약할 뉴스의 갯수를 입력하세요 : (default : 10) ").strip()

        if not num_of_summary_input:
            num_of_summary = 10
            break

        try:
            num_of_summary = int(num_of_summary_input)

            if num_of_summary <= 0:
                print("1 이상의 숫자를 입력해주십시오.")
            elif num_of_summary > 30:
                print("한 번에 요약 가능한 뉴스의 개수는 최대 30개입니다.")
            else:
                break

        except ValueError:
            print("올바른 숫자를 입력하지 않았습니다. 다시 입력해주세요.")

    # Selenium을 이용하여 웹 페이지에서 뉴스 정보를 가져옴
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    except Exception as e:
        print(f"Selenium WebDriver 초기화 중 오류 발생: {e}")
        return

    if use_default:
        driver.get(site_url)
        time.sleep(3)

        try:
            news_elements = driver.find_elements(By.CSS_SELECTOR, 'div.item-box01')[:num_of_summary]
        except Exception as e:
            print(f"뉴스 요소 추출 중 오류 발생: {e}")
            driver.quit()
            return

        news_items = []
        for news in news_elements:
            try:
                title = news.find_element(By.CSS_SELECTOR, 'strong.tit-news').text
                link = news.find_element(By.CSS_SELECTOR, 'a.tit-wrap').get_attribute('href')
                news_items.append({'title': title, 'link': link})
            except Exception as e:
                print(f"뉴스 제목 또는 링크 추출 중 오류 발생: {e}")
                continue

    else:
        driver.get(site_url)
        time.sleep(3)

        try:
            candidate_elements = driver.find_elements(By.CSS_SELECTOR, 'a, h1, h2, h3, h4, h5, h6')
        except Exception as e:
            print(f"요소 추출 중 오류 발생: {e}")
            driver.quit()
            return

        elements_info = []
        base_url = site_url

        for idx, elem in enumerate(candidate_elements[:200]):
            try:
                text = elem.text.strip()
                html = elem.get_attribute('outerHTML')

                css_selector = elem.tag_name
                elem_id = elem.get_attribute('id')
                elem_class = elem.get_attribute('class')
                if elem_id:
                    css_selector += f"#{elem_id}"
                if elem_class:
                    classes = '.'.join(elem_class.split())
                    css_selector += f".{classes}"

                href = elem.get_attribute('href') if elem.tag_name == 'a' else ''
                if href:
                    href = urljoin(base_url, href)

                elements_info.append({
                    'index': idx,
                    'text': text,
                    'html': html,
                    'css_selector': css_selector,
                    'href': href
                })
            except Exception as e:
                print(f"요소 정보 추출 중 오류 발생: {e}")
                continue

        driver.quit()

        prompt = create_prompt(elements_info, num_of_summary)

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 HTML 요소를 분석하여 뉴스 헤드라인과 링크를 구별하는 도우미입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0
            )

            assistant_reply = response.choices[0].message.content.strip()
            news_items = parse_gpt_response(assistant_reply)

        except Exception as e:
            print(f"OpenAI API 호출 중 오류 발생: {e}")
            news_items = []

    if not news_items:
        print("뉴스 항목을 가져올 수 없어 종료합니다.")
        return

    summarized_results = summarize_news_articles(news_items)

    # 파일명에 현재 날짜와 시간을 포함하여 저장
    current_time = datetime.now().strftime("%Y%m%d_%H%M")
    file_name = f"issue_keyword_{current_time}.txt"

    try:
        with open(file_name, 'w', encoding='utf-8') as f:
            for result in summarized_results:
                f.write("원본 제목 : " + result['original_title'] + '\n')
                f.write("링크 : " + result['link'] + '\n')
                f.write("------------------------------------\n")
                f.write("헤드라인 : " + result['headline'] + '\n')
                f.write("요약 : " + result['summary'] + '\n')
                f.write(' '.join(result['hashtags']) + '\n')
                f.write("대표해시태그 : " + ' '.join(result['representative_hashtags']) + '\n')
                f.write("헤드라인 아이디어 :\n")
                for idea in result['title_ideas']:
                    f.write(idea + '\n')
                f.write("대표해시태그 아이디어 :\n")
                for idea in result['representative_hashtag_ideas']:
                    f.write(idea + '\n')
                f.write("\n\n")
    except Exception as e:
        print(f"파일 저장 중 오류 발생: {e}")
        return

    print(f"요약 결과가 '{file_name}' 파일로 저장되었습니다.")

if __name__ == "__main__":
    main()
