from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Selenium 웹드라이버 설정 (자동으로 크롬 드라이버 다운로드)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# 요청할 URL
url = "https://news.naver.com/main/ranking/popularDay.naver"
driver.get(url)

# 페이지가 모두 로드될 때까지 잠시 대기
time.sleep(3)

# 상위 10개의 뉴스 항목 추출 (랭킹 뉴스는 'li.popular_news_node' 태그 안에 포함되어 있음)
news_elements = driver.find_elements(By.CSS_SELECTOR, 'rankingnews_box')[:5]

print(news_elements)

# 뉴스 제목과 링크 추출
top_10_news = []
for news in news_elements:
    # 뉴스 제목과 링크 추출
    title = news.find_element(By.CSS_SELECTOR, 'a').text
    link = news.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
    top_10_news.append((title, link))

# 결과 출력
for idx, (title, link) in enumerate(top_10_news):
    print(f"{idx+1}. {title}: {link}")

# 브라우저 닫기
driver.quit()
