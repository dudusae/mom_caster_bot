from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply)
import datetime
import config
import requests
from pymongo import MongoClient
from emoji import emojize

client = MongoClient('localhost', 27017)
db = client.mommbot

my_token = config.my_token
my_key_weather = config.my_key_weather

#### 날씨 정보 찾기 함수 #####

# 사용자 지역정보 저장하기
#   : 입력한 동이름(message)이 db.location의 지역이름과 일치할 경우
#     db.user_location에 chat_id와 location_id값을 저장한다.

def find_location(chat_id, message):
    results = db.location.find({'3단계':{'$regex':'.*'+message+'.*'}})
    results_py = []
    for i in results:
        results_py.append(i)
    # 1 검색결과가 1개일 때 DB에 저장하고 저장했다고 알려줌
    if len(results_py) == 1:
        db.user_location.insert_one({'chat_id': chat_id, 'location_id': results_py[0]['_id']})
        print(results_py[0]['3단계']+'이구나 기억했다.')
    # 2 검색결과가 2개 이상일 때 다시 확인한다
    elif len(results_py) >= 2:
        print(results_py[0]['3단계']+'이 여러 곳이있네. 이중에 어디가 맞아?')
        for i in results_py:
            print('-'+i['1단계']+' '+i['2단계']+' '+i['3단계'])
    # 3 입력한 지역정보를 찾을 수 없을 때 다시 물어봄
    else:
        print('엄마가 못알아 들었어. 다시 한번 말해줘봐.')

    # **추가해야하는부분**
    #4 저장할 때 기존 chat_id정보가 있는지 찾아봄. 있을 경우 덮어쓴다.
    #5 빠진 행정구역이 있어서, 행정구역 DB를 보충하여 검색결과를 보정해야함.


# 사용자 지역의 날씨 정보 호출하기
#   : 사용자의 location_id와 일치하는 기상 위치 xy값을 db.location으로 부터 불러와서
#     (신)동네예보정보조회서비스 API에 날씨 정보를 호출한다.(오늘 오전 6시 기준)
def request_weather(chat_id):
    location_id = db.user_location.find_one({'chat_id':chat_id})['location_id']
    location_x = db.location.find_one({'_id':location_id})['격자 X']
    location_y = db.location.find_one({'_id':location_id})['격자 Y']
    print(location_x,location_y)

    now = datetime.datetime.now()
    today = now.strftime('%Y%m%d')
    time = '0600'

    r = requests.get(
        'http://newsky2.kma.go.kr/service/SecndSrtpdFrcstInfoService2/ForecastGrib?ServiceKey='+my_key_weather+'&base_date='+today+'&base_time='+time+'&nx='+str(location_x)+'&ny='+str(location_y)+'&pageNo=1&numOfRows=1&_type=json')
    rjson = r.json()
    print(rjson['response']['body']['items']['item'])


####### 챗봇 함수 ####

# /start 명령을 입력하면 '누구니'라고 물어본다. '딸' '아들' 선택 버튼이 나타난다.
def start(bot, update):
    reply_keyboard = [[emojize('딸이얌:heart:', use_aliases=True), emojize('아들이요:alien:', use_aliases=True), ]]

    update.message.reply_text(
        '누구니?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

# /location 명령을 입력하면 '어디니'라고 물어본다. 답변 입력창이 열린다.
def location(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='어디니? 동 이름으로 알려줘.', reply_markup=ForceReply())


def main():
    my_token = config.my_token
    updater = Updater(token=my_token)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("location", location))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()


#### 챗봇에서 추가해야하는부분 **
# /start에서 질문-답변을 단계적으로 진행해 나가야함.
#    = 아들이라고 답하면 아들이구나 하고 지역을 묻는 스텝으로 넘어가야함.
#    >> Conversation Handler와 관련 있는 듯.
# 답변을 받아서 DB에 저장하고, DB를 검색하는 변수로 활용해야 함.