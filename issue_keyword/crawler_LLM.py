from newspaper import Article
from transformers import pipeline
from keybert import KeyBERT
import torch

# 1. 뉴스 링크에서 본문 추출
def extract_article_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.title, article.text
    except Exception as e:
        print(f"Error in extracting article: {e}")
        return None, None

# 2. KoAlpaca 모델을 사용하여 요약 생성 (두 줄 요약, GPU 사용)
def summarize_article(text):
    # 장치 설정 (GPU 사용이 가능한 경우 GPU 사용)
    device = 0 if torch.cuda.is_available() else -1

    # GPU 메모리 캐시 비우기 (CUDA Out of Memory 방지)
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # 더 작은 모델로 변경 (12.8B -> 5.8B) 및 배치 크기 설정
    summarizer = pipeline("summarization", model="meta-llama/Llama-3.2-3B", device=device, batch_size=1)
    
    # 본문이 너무 길 경우 일부만 요약하도록 제한 (입력 길이 256으로 축소)
    max_input_length = 256  # 기존 512에서 256으로 줄이기
    if len(text) > max_input_length:
        text = text[:max_input_length]  # 본문 길이 제한
    
    # max_new_tokens로 요약 생성
    summary = summarizer(text, max_new_tokens=60, min_length=40, do_sample=False)
    
    # 요약문이 두 줄로 나올 수 있도록 정제
    summary_text = summary[0]['summary_text']
    lines = summary_text.split('. ')  # 문장을 기준으로 분할
    two_line_summary = '. '.join(lines[:2]) + '.'  # 앞의 두 문장만 사용
    
    return two_line_summary

# 3. 키워드 추출하여 해시태그 생성 (더 알맞은 해시태그로 변경)
def extract_keywords(text):
    kw_model = KeyBERT()
    
    # 불필요한 단어를 걸러내고 핵심 키워드를 뽑아냄
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 1), stop_words='english', top_n=5)
    hashtags = ['#' + keyword[0].replace(' ', '') for keyword in keywords]
    
    return hashtags

# 4. 결과를 output.txt로 저장
def save_output(title, summary, hashtags):
    try:
        with open("output.txt", "w", encoding="utf-8") as f:
            f.write(f"헤드라인: {title}\n")
            f.write(f"요약: {summary}\n")
            f.write(f"해시태그: {' '.join(hashtags)}\n")
        print("결과가 output.txt 파일에 저장되었습니다.")
    except Exception as e:
        print(f"Error in saving output: {e}")

# 메인 함수
def process_news_link(url):
    # 1. 뉴스 본문 추출
    title, text = extract_article_text(url)
    
    if title and text:
        # 2. 본문 요약
        summary = summarize_article(text)
        
        # 3. 키워드 추출하여 해시태그 생성
        hashtags = extract_keywords(text)
        
        # 4. 결과 저장
        save_output(title, summary, hashtags)
    else:
        print("기사를 가져오는데 실패했습니다.")

# 뉴스 URL 입력
news_url = "https://n.news.naver.com/article/437/0000412615?cds=news_media_pc&type=editn"
process_news_link(news_url)
