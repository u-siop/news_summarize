# 프로그램 실행 명세서

## 1. .exe 파일이 있을 경우
해당 프로그램 실행

a.	해당 input 값에 원하는 값 입력
i.	User input
1.	분석할 뉴스 사이트 ( default : 연합뉴스 )
	예시 )
http://www.ansannews.co.kr/news/articleView.html?idxno=13510 
	https://n.news.naver.com/article/011/0004403177?ntype=RANKING 
	http://www.civicnews.com/news/articleView.html?idxno=28776  https://www.yna.co.kr/view/AKR20160524181900033 
	https://www.bbc.com/future/article/20220718-the-best-way-to-brush-your-teeth 

b.	issue_briefing.exe 파일이 있는 폴더에 issue_briefing_현재시간.txt 파일 생성

## 2. .exe 파일이 유실 되었을 경우
python 설치가 필요한 경우
https://www.python.org/downloads/ 


Python 설치 후
Win + r
Cmd 


Cmd 창에 ```pip install``` 후 엔터

pip install 이 안 되는 경우, 해당 링크 참조 https://balabala.tistory.com/76 
<br><br> ```pip install requests beautifulsoup4 selenium webdriver-manager openai pyinstaller```
<br>Cmd에 해당 위 명령어 복사 실행

issue_briefing.py 파일이 있는 폴더에서 해당 빨간 부분 클릭후, 경로 복사
<br>Cd 경로, 엔터

경로 바뀌었는지 한 번 더 확인 
<br> ```pyinstaller --onefile issue_briefing.py```
<br>복사 후, 붙여넣기

엄청난 양의 코드 끝에 “dist” 폴더에 issue_briefing.exe 파일 생성
