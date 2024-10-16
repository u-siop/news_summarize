from selenium import webdriver
from selenium.webdriver.common.by import By
import time

# Selenium 웹드라이버 설정 (ChromeDriverManager를 사용하여 자동 설치)
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Chrome WebDriver 설정
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# 네이버 랭킹 뉴스 페이지 URL
url = "https://news.naver.com/main/ranking/popularDay.naver"

# 페이지 열기
driver.get(url)

# 페이지가 모두 로드될 때까지 잠시 대기
time.sleep(3)  # 필요에 따라 조절 가능

# 언론사별 랭킹 뉴스 목록 찾기
news_boxes = driver.find_elements(By.CSS_SELECTOR, '.rankingnews_box')

# 뉴스 정보 추출
for box in news_boxes:
    # 언론사 이름
    media_name = box.find_element(By.CSS_SELECTOR, '.rankingnews_name').text.strip()
    print(f"언론사: {media_name}")
    
    # 개별 뉴스 제목과 링크 추출
    news_list = box.find_elements(By.CSS_SELECTOR, '.rankingnews_list li')
    
    for news in news_list:
        # 뉴스 제목
        title = news.find_element(By.CSS_SELECTOR, '.list_title').text.strip()
        # 뉴스 링크
        link = news.find_element(By.CSS_SELECTOR, '.list_title').get_attribute('href')
        # 뉴스 시간
        time_text = news.find_element(By.CSS_SELECTOR, '.list_time').text.strip()
        print(f"- {title} ({time_text}): {link}")
    
    print('-' * 40)  # 구분선

# 브라우저 닫기
driver.quit()
