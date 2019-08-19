# 2단계
import datetime
import config
from telegram.ext import Updater, MessageHandler, Filters
import requests
from pymongo import MongoClient
from emoji import emojize

client = MongoClient('localhost', 27017)
db = client.mommbot

my_token = config.my_token
my_key_weather = config.my_key_weather

updater = Updater(token=my_token)
dispatcher = updater.dispatcher
updater.start_polling()


# 오늘날짜 불러오기
now = datetime.datetime.now()
today = now.strftime('%Y%m%d')

# 입력한 동 지역정보가 db에서 일치할 경우 동 정보와 location_id값을 저장
def find_locaciton(message):
    results = db.location.find({'3단계':{'$regex':'.*'+message+'.*'}})
    results_py = []
    for i in results:
        results_py.append(i)
    # 1 검색결과가 1개일 때 지역정보 id를 저장하고 저장했다고 알려줌
    if len(results_py) == 1:
        db.user_location.insert_one({'chat_id': 'TEST', 'location': results_py[0]['_id']})
        print(results_py[0]['3단계']+' 저장했습니다')
    # 2 검색결과가 2개 이상일 때 다시 확인한다
    elif len(results_py) >= 2:
        print('다음중 어느 주소입니까?')
        for i in results_py:
            print('-'+i['1단계']+' '+i['2단계']+' '+i['3단계'])
    # 3 입력한 지역정보를 찾을 수 없을 때 다시 물어봄
    elif len(results_py) == 0:
        print('정확한 지역정보를 입력하세요')
    else:
        print('OK')

    # **추가해야하는부분**
    #4 저장할 때 기존 chat_id정보가 있는지 찾아봄. 있을 경우 덮어씀
    #5 행정구역DB를 보충하여 보정해야함

find_locaciton('서교')


# (신)동네예보정보조회서비스 API정보 불러오기
r = requests.get('http://newsky2.kma.go.kr/service/SecndSrtpdFrcstInfoService2/ForecastGrib?ServiceKey='+my_key_weather+'&base_date='+today+'&base_time=0600&nx=55&ny=127&pageNo=1&numOfRows=1&_type=json')
rjson = r.json()
print (rjson['response']['body']['items']['item'])

# 챗봇
def handler(bot, update):
    text = update.message.text
    chat_id = update.message.chat_id

    if '신촌동' in text:
        bot.send_message(chat_id=chat_id, text=text+'에서 뭐하니')
        db.user_location.insert_one({'chat_id': chat_id, 'location': text}) #아이디 지역 저장
        bot.send_message(chat_id=chat_id, text='아이디 지역 저장했다')
    elif '혜님' in text:
        bot.send_message(chat_id=chat_id, text=emojize('아잉:heart_eyes:', use_aliases=True))
    else:
        bot.send_message(chat_id=chat_id, text='몰라')

echo_handler = MessageHandler(Filters.text, handler)
dispatcher.add_handler(echo_handler)
