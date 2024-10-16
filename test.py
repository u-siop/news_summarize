import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from dotenv import load_dotenv

# 환경 변수에서 OpenAI API 키 로드
load_dotenv()
# OpenAI API 설정

site_url = input("분석할 뉴스 사이트의 URL을 입력하세요 : (default : 연합뉴스) ")
if not site_url:
    site_url = "https://www.yna.co.kr/theme/mostviewed/index"

num_of_summary = input("요약할 뉴스의 갯수를 입력하세요 : (default : 10개) ")
if not num_of_summary:
    num_of_summary = 10
else:
    try:
        num_of_summary = int(num_of_summary)
    except ValueError:
        print("올바른 숫자를 입력하지 않아 기본값 10개로 설정합니다.")
        num_of_summary = 10

# 웹 페이지 요청 및 파싱
response = requests.get(site_url)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.text, 'html.parser')

# 후보 요소 추출 (예: 모든 a 태그와 헤딩 태그)
candidate_elements = soup.find_all(['a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

# 요소 정보를 저장할 리스트
elements_info = []

for idx, elem in enumerate(candidate_elements):
    # 요소의 텍스트와 HTML 가져오기
    text = elem.get_text(strip=True)
    html = str(elem)
    # 요소의 고유한 CSS Selector 생성
    css_selector = elem.name
    if elem.get('id'):
        css_selector += f"#{elem.get('id')}"
    if elem.get('class'):
        classes = '.'.join(elem.get('class'))
        css_selector += f".{classes}"
    elements_info.append({
        'index': idx,
        'text': text,
        'html': html,
        'css_selector': css_selector
    })

# GPT에 보낼 프롬프트 생성
def create_prompt(elements_info):
    prompt = "다음은 웹 페이지의 요소들입니다. 각 요소의 인덱스, 텍스트, HTML이 주어집니다.\n"
    prompt += "각 요소가 뉴스 헤드라인인지, 뉴스 링크인지, 또는 무시해야 하는지 판단하고, 뉴스 헤드라인과 링크에 해당하는 값을 출력해줘\n\n"
    prompt += f"상위 {num_of_summary}개의 뉴스만 들고와줘"
    prompt += "요소들:\n"
    for elem in elements_info:
        prompt += f"인덱스: {elem['index']}\n"
        prompt += f"텍스트: {elem['text']}\n"
        prompt += f"HTML: {elem['html']}\n\n"
    prompt += "출력 형식:\n"
    prompt += "뉴스 헤드라인:\n"
    prompt += "뉴스 링크:\n"

    prompt += "[예시] \n"
    prompt += "뉴스 헤드라인 : 최태원 SK회장 차녀, ‘예비신랑’과 인연 이것 때문이라는데…\n"
    prompt += "뉴스 링크 : https://www.mk.co.kr/news/society/11135856\n"

    return prompt

prompt = create_prompt(elements_info)

# OpenAI API 호출
try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 또는 사용 가능한 다른 모델
        messages=[
            {"role": "system", "content": "당신은 HTML 요소를 분석하여 뉴스 헤드라인과 링크를 구별하는 도우미입니다."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0
    )

    assistant_reply = response.choices[0].message.content.strip()

    print("\nGPT의 응답:")
    print(assistant_reply)

except Exception as e:
    print(f"OpenAI API 호출 중 오류 발생: {e}")
