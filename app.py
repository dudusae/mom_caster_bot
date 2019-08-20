import logging
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


# 사용자 지역정보에 맞는 오늘 날씨를 호출
def request_weather(chat_id):
    location_id = db.user_location.find_one({'chat_id':chat_id})['location_id']
    location_x = db.location.find_one({'_id':location_id})['격자 X']
    location_y = db.location.find_one({'_id':location_id})['격자 Y']
    print(location_x,location_y)
    # 기준시간 설정(오늘, 오전 6시)
    now = datetime.datetime.now()
    today = now.strftime('%Y%m%d')
    time = '0600'
    # (신)동네예보정보조회서비스 API정보 불러오기
    r = requests.get(
        'http://newsky2.kma.go.kr/service/SecndSrtpdFrcstInfoService2/ForecastGrib?ServiceKey='+my_key_weather+'&base_date='+today+'&base_time='+time+'&nx='+str(location_x)+'&ny='+str(location_y)+'&pageNo=1&numOfRows=1&_type=json')
    rjson = r.json()
    print(rjson['response']['body']['items']['item'])
# request_weather('test_user_2')


# 챗봇시작
# 로그사용하기(뭔지 잘 모르겠음)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(bot, update):
    reply_keyboard = [[emojize('딸이얌:heart:', use_aliases=True), emojize('아들이요:alien:', use_aliases=True), ]]

    update.message.reply_text(
        '누구니?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))


# 입력한 동 지역정보가 db에서 일치할 경우 chat_id와 location_id값을 저장
def location(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='어디니?', reply_markup=ForceReply())

    find_location(update.message.chat_id,update.message.text)


def find_location(chat_id, message):
    results = db.location.find({'3단계':{'$regex':'.*'+message+'.*'}})
    results_py = []
    for i in results:
        results_py.append(i)
    # 1 검색결과가 1개일 때 DB에 저장하고 저장했다고 알려줌
    if len(results_py) == 1:
        db.user_location.insert_one({'chat_id': chat_id, 'location_id': results_py[0]['_id']})
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

#
# def echo(bot, update):
#     """Echo the user message."""
#     bot.send_message(chat_id=update.message.chat_id, text=update.message.text)
#
#
# def error(bot, update):
#     """Log Errors caused by Updates."""
#     logger.warning('Update "%s" caused error "%s"', bot, update.error)


def main():
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    my_token = config.my_token
    updater = Updater(token=my_token)
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("주소변경", start))
    dp.add_handler(CommandHandler("location", location))

    # on noncommand i.e message - echo the message on Telegram
    # dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    # dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()



#
# def start(update, context):
#     reply_keyboard = [[emojize('딸이얌:heart:', use_aliases=True), emojize('아들이요:alien:', use_aliases=True), ]]
#     update.message.reply_text(
#         '누구니?',
#         reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
#     if '아들이요' in text:
#         bot.send_message(chat_id=chat_id, text=text+' 밥은 먹었니')
#     return GENDER

#
# # 챗봇
# def handler(bot, update):
#     text = update.message.text
#     chat_id = update.message.chat_id
#
#     if '아들이요' in text:
#
#         bot.send_message(chat_id=chat_id, text=text+' 밥은 먹었니')
#         # find_locaciton(chat_id,text)
#         # bot.send_message(chat_id=chat_id, text='아이디 지역 저장했다')
#     else:
#         bot.send_message(chat_id=chat_id, text='몰라')
#
# echo_handler = MessageHandler(Filters.text, handler)
# dispatcher.add_handler(echo_handler)
