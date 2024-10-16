import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

# Configure the Gemini API
GOOGLE_API_KEY = ""  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)

# Function to scrape a webpage and extract text
def scrape_webpage(url):
    response = requests.get(url)
    response.encoding = 'utf-8'  # Ensure correct encoding
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extract the main content
    article_text = ' '.join([p.get_text() for p in soup.find_all('p')])
    
    return article_text

# Function to summarize the article content using Gemini in a casual tone
def summarize_article_content(content):
    model = genai.GenerativeModel('gemini-pro')
    
    # Create the prompt with explicit instructions and an example in a casual tone
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

    response = model.generate_content(prompt)
    
    if response:
        summary_text = response.text.strip()

        # Print the assistant's response for debugging
        print("Assistant's response:")
        print(summary_text)
        print("\n---\n")
        
        # Parse the response based on the expected format
        try:
            # Use regular expressions to extract sections
            title_match = re.search(r'제목:\s*(.*)', summary_text)
            first_summary_match = re.search(r'첫 번째 요약 문장:\s*(.*)', summary_text)
            second_summary_match = re.search(r'두 번째 요약 문장:\s*(.*)', summary_text)
            hashtags_match = re.search(r'해시태그:\s*(.*)', summary_text)
            # Optional: Extract title ideas if needed
            # title_ideas_match = re.search(r'제목 아이디어:\s*(.*)', summary_text, re.DOTALL)

            headline = title_match.group(1).strip() if title_match else 'No headline found'
            first_summary = first_summary_match.group(1).strip() if first_summary_match else 'No first summary found'
            second_summary = second_summary_match.group(1).strip() if second_summary_match else 'No second summary found'
            summary = f"{first_summary}\n\n{second_summary}"
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

    else:
        return {
            'headline': "Failed to summarize.",
            'summary': "Failed to summarize.",
            'hashtags': []
        }

# Main function to process and summarize content from a list of articles (title, url)
def summarize_news_articles(articles):
    summarized_results = []
    
    for title, url in articles:
        print(f"Processing article: {title}")
        content = scrape_webpage(url.strip())
        
        # Truncate content if too long to avoid token limits (optional)
        content = content[:4000]  # Adjust based on model's input limit
        
        summary = summarize_article_content(content)
        
        summarized_results.append({
            'original_text': title,
            'headline': summary['headline'],
            'summary': summary['summary'],
            'hashtags': summary['hashtags'],
            'raw_content_length': len(content)
        })
    
    return summarized_results

# Selenium webdriver setup (automatically downloads Chrome driver)
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# Target URL
url = "https://www.mk.co.kr/news/ranking/"
driver.get(url)

# Wait for the page to fully load
time.sleep(3)

# Extract the top 10 news items
news_elements = driver.find_elements(By.CSS_SELECTOR, 'li.popular_top_node')[:5]

# Extract news titles and links
top_10_news = []
for news in news_elements:
    # Extract news title and link
    title = news.find_element(By.CSS_SELECTOR, 'h3.news_ttl').text
    link = news.find_element(By.CSS_SELECTOR, 'a').get_attribute('href')
    top_10_news.append((title, link))

# Close the browser
driver.quit()

# Now, process the news articles
summarized_results = summarize_news_articles(top_10_news)

# Output the results
for result in summarized_results:
    print("Original Text:", result['original_text'])
    print("Headline:", result['headline'])
    print("Summary:", result['summary'])
    print("Hashtags:", ' '.join(result['hashtags']))
    print("Raw content length:", result['raw_content_length'])
    print("\n")
