# 프로그램 실행 명세서

## 1. .exe 파일이 있을 경우
해당 프로그램 실행

해당 input 값에 원하는 값 입력
Default 값으로 실행하기 원한다면, 엔터 두 번
User input
분석할 뉴스 사이트 ( default : 연합뉴스 )
예시 )
연합뉴스 (https://www.yna.co.kr/theme/mostviewed/index)
매일경제 (https://www.mk.co.kr/news/ranking/all/) 
네이트 뉴스(https://news.nate.com/rank/interest?sc=all&p=day&date=20241015)
한경뉴스 (https://www.hankyung.com/ranking) 
네이버뉴스(https://news.naver.com/main/ranking/popularDay.naver)


분석할 뉴스 개수     ( default : 10 )
( minimum : 1개, maximum 30개 )
chatgpt_summarize_user_input.exe 파일이 있는 폴더에 news_summary_현재시간.txt 파일 생성


## 2. .exe 파일이 유실 되었을 경우
python 설치가 필요한 경우
https://www.python.org/downloads/ 



Python 설치 후
Win + r
Cmd 


Cmd 창에 pip install 후 엔터

pip install 이 안 되는 경우, 해당 링크 참조 https://balabala.tistory.com/76 
pip install requests beautifulsoup4 selenium webdriver-manager openai pyinstaller
Cmd에 해당 위 명령어 복사 실행

Chatgpt_summarize_user_input.py 파일이 있는 폴더에서 해당 빨간 부분 클릭후, 경로 복사
Cd 경로, 엔터

경로 바뀌었는지 한 번 더 확인 
pyinstaller --onefile chatgpt_summarize_user_input.py  복사 후, 붙여넣기

엄청난 양의 코드 끝에 “dist” 폴더에 chatgpt_summarize_user_input.exe 파일 생성
