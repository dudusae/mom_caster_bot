from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove, ForceReply)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler)
import logging
import datetime
import config
import requests
from pymongo import MongoClient
from emoji import emojize

client = MongoClient('localhost', 27017)
db = client.mommbot

my_token = config.my_token
my_key_weather = config.my_key_weather

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

GENDER, LOCATION, LOCATION_SELECT, WEATHER = range(4)


# 챗봇함수 시작 ---------------------------------------------------------------


# /start 명령 : '누구니'라고 물어본다. '딸' '아들' 선택 버튼이 나타난다.
def start(update, context):
    reply_keyboard = [[emojize('딸이얌:heart:', use_aliases=True),
                       emojize('아들이요:alien:', use_aliases=True)]]

    update.message.reply_text('누구니?',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard,one_time_keyboard=True))

    return GENDER


# 딸, 아들 정보 저장하고 지역 물어보기
def gender(update, context):
    chat_id = update.message.chat_id

    if '딸' in update.message.text:
        gender = '딸'
    else:
        gender = '아들'

    db.user.insert_one({'chat_id': chat_id, 'gender': gender})

    update.message.reply_text('우리'+gender+emojize(':heart:', use_aliases=True)+
                              '밥먹었니?\n나는 날씨를 알려주는 날씨 엄마란다',
                              reply_markup=ReplyKeyboardRemove())
    update.message.reply_html('날씨를 알고 싶은 <b>동 이름</b>을 알려주면 날씨 소식을 전해줄게.')

    return LOCATION


def gender_error(update, context):
    update.message.reply_text('누구냐? 딸이냐 아들이냐'+emojize(':shit:', use_aliases=True))


# 동이름 검색하고 사용자 지역정보 저장하기
def location(update, context):
    chat_id = update.message.chat_id
    chat_txt = update.message.text

    search_result = db.location.find({'3단계': {'$regex':chat_txt+'$'}})
    search_result_list = []

    for i in search_result:
        search_result_list.append(i)

    # 1 검색결과가 1개일 때 DB에 저장하고 저장했다고 알려줌
    if len(search_result_list) == 1:
        reply_keyboard = [[emojize('아니요 알려주세요:raised_hands:', use_aliases=True),
                           emojize('네 이미 알고 있죠:v:', use_aliases=True)]]

        db.user.find_one_and_update({'chat_id': chat_id},
                                             {'$set': {'location_id': search_result_list[0]['_id']}})
        update.message.reply_text(search_result_list[0]['3단계']+'이구나 기억했다.\n오늘 일기예보는 확인했니?',
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard,one_time_keyboard=True))
        return WEATHER

    # 2 검색결과가 2개 이상일 때 다시 확인한다
    elif len(search_result_list) >= 2:
        reply_keyboard = []
        for i in search_result_list:
            reply_keyboard.append(i['1단계']+' '+i['2단계']+' '+i['3단계'])
        reply_keyboard.append('이 중에는 없어요')
        update.message.reply_text(chat_txt + ', 여러 곳이있네. \n이중에 어디를 말하는거니?',
                                  reply_markup=ReplyKeyboardMarkup.from_column(reply_keyboard, one_time_keyboard=True))
        return LOCATION_SELECT

    # 3 입력한 지역정보를 찾을 수 없을 때 다시 물어봄
    else:
        update.message.reply_html('엄마는 잘 모르는 곳인 것 같구나'+emojize(':eyes:', use_aliases=True)
                                  +'\n<b>시나 군</b> 이름으로 알려줘.')
        return LOCATION


def location_null(update, context):
    update.message.reply_html('이중에 없다구?'+ emojize(':speak_no_evil:', use_aliases=True)
                              + '\n엄마가 모르는 동네인가 보다.\n<b>시나 군</b> 이름으로 알려줘.')
    return LOCATION


# 동정보가 없을 경우 시,군,구로 조회
def location_city(update, context):
    chat_id = update.message.chat_id
    chat_txt = update.message.text

    search_result = db.location.find({'$and': [{'2단계': {'$regex':chat_txt+'$'}},{'3단계':''}]})
    search_result_list = []

    for i in search_result:
        search_result_list.append(i)

    # 1 검색결과가 1개일 때 DB에 저장하고 저장했다고 알려줌
    if len(search_result_list) == 1:
        reply_keyboard = [[emojize('아니요 알려주세요:raised_hands:', use_aliases=True),
                           emojize('네 이미 알고 있죠:v:', use_aliases=True)]]

        db.user.find_one_and_update({'chat_id': chat_id},
                                    {'$set': {'location_id': search_result_list[0]['_id']}})
        update.message.reply_text(search_result_list[0]['2단계']+'이구나 기억했다.\n오늘 일기예보는 확인했니?',
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard,one_time_keyboard=True))
        return WEATHER

    # 2 검색결과가 2개 이상일 때 다시 확인한다
    elif len(search_result_list) >= 2:
        reply_keyboard = []
        for i in search_result_list:
            reply_keyboard.append(i['1단계']+' '+i['2단계'])
        reply_keyboard.append('이 중에는 없어요')
        update.message.reply_text(chat_txt + ', 여러 곳이있네. \n이중에 어디를 말하는거니?',
                                  reply_markup=ReplyKeyboardMarkup.from_column(reply_keyboard, one_time_keyboard=True))
        return LOCATION_SELECT

    # 3 입력한 지역정보를 찾을 수 없을 때 다시 물어봄
    else:
        update.message.reply_html('엄마는 잘 모르는 곳인 것 같구나'+emojize(':eyes:', use_aliases=True)
                                  +'\n<b>다른 지명</b>으로 알려줘.')
        return LOCATION


def location_error(update, context):
    update.message.reply_html('엄마는 나이가 들어서 정확하게 알려줘야해.'+emojize(':see_no_evil:', use_aliases=True)
                              +'\n정확한 <b>동 이름</b>을 다시 알려주렴.')
    return LOCATION


def location_save(update, context):
    chat_id = update.message.chat_id
    chat_txt = update.message.text
    location_value = chat_txt.split(' ')
    reply_keyboard = [[emojize('아니요 알려주세요:raised_hands:', use_aliases=True),
                       emojize('이미 알고 있죠:v:', use_aliases=True)]]

    if len(location_value) >= 3 :
        search_result = db.location.find_one({'$and': [{'1단계': location_value[0]},
                                                   {'2단계': location_value[1]},
                                                   {'3단계': location_value[2]}]})
        update.message.reply_text(search_result['1단계']+' '
                                  + search_result['2단계']+' '
                                  + search_result['3단계']
                                  + '이구나 기억했다.')
    else :
        search_result = db.location.find_one({'$and': [{'1단계': location_value[0]},
                                                   {'2단계': location_value[1]}]})
        update.message.reply_text(search_result['1단계']+' '
                                  + search_result['2단계']+' '
                                  + '이구나 기억했다.')
    db.user.find_one_and_update({'chat_id': chat_id},
                                {'$set': {'location_id': search_result['_id']}})
    update.message.reply_text('오늘 일기예보는 확인했니?',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return WEATHER


# 날씨를 알려준다
def weather(update, context):
    # user = update.message.from_user
    # print(user['id'])
    chat_id = update.message.chat_id
    print(chat_id)
    location_id = db.user.find_one({'chat_id': chat_id})['location_id']
    location_x = db.location.find_one({'_id': location_id})['격자 X']
    location_y = db.location.find_one({'_id': location_id})['격자 Y']
    print(location_x, location_y)

    now = datetime.datetime.now()
    today = now.strftime('%Y%m%d')
    time = '0600'

    r = requests.get(
        'http://newsky2.kma.go.kr/service/SecndSrtpdFrcstInfoService2/ForecastGrib?ServiceKey='
        + my_key_weather + '&base_date=' + today + '&base_time=' + time
        + '&nx=' + str(location_x) + '&ny=' + str(location_y) + '&pageNo=1&numOfRows=1&_type=json')
    rjson = r.json()
    weather = rjson['response']['body']['items']['item']
    print(weather)
    update.message.reply_text('그래, 날씨를 알려줄께.\n'+weather['category']+':'+str(weather['obsrValue']),
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def weather_skip(update, context):
    chat_id = update.message.chat_id
    gender = db.user.find_one({'chat_id':chat_id})['gender']
    update.message.reply_text('우리'+gender+'이 웬일이래.'+emojize(':innocent:', use_aliases=True)
                              +'\n그래 내일 아침부터 문자 넣을게.\n'
                              +'주소 바뀌면 /location\n'
                              +'날씨 궁금하면 /weather 라고 엄마한테 말해줘\n'
                              +'영어라고 어려워말고'+emojize(':kissing_heart:', use_aliases=True),
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


# /location 명령 : 지역정보 업데이트
def location_update(update, context):
    chat_id = update.message.chat_id

    update.message.reply_text('주소 바뀌었니?')
    update.message.reply_html('날씨를 알고 싶은 <b>동 이름</b>을 알려주면 날씨 소식을 전해줄게.')

    return LOCATION


def cancel(update, context):
    update.message.reply_text('그래 나중에 연락해'+emojize(':ok_woman:', use_aliases=True),
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


# 정의되지 않은 메시지에 대한 처리 : 받은 메시지를 돌려준다
def echo(update, context):
    update.message.reply_text(update.message.text)


# 챗봇 실행

def main():
    my_token = config.my_token
    updater = Updater(token=my_token, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start),
                      CommandHandler('location', location_update)],

        states={
            GENDER: [MessageHandler(Filters.regex('^(딸|아들)'), gender),
                     MessageHandler(Filters.regex('[^(딸|아들)]'), gender_error)],

            LOCATION: [MessageHandler(Filters.regex('(동|읍|면)$'), location),
                              MessageHandler(Filters.regex('(시|군|구)$'), location_city),
                       MessageHandler(Filters.regex('[^(동|읍|면)$]'), location_error)],

            LOCATION_SELECT: [MessageHandler(Filters.regex('(동|읍|면|시|군|구)$'), location_save),
                              MessageHandler(Filters.regex('[^(동|읍|면)$]'), location_null)],

            WEATHER: [MessageHandler(Filters.regex('^(아니|아직)'), weather),
                      MessageHandler(Filters.regex('^(네|응|이미|그럼|당연|ㅇㅇ)'), weather_skip)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )


    dp.add_handler(conv_handler)
    dp.add_handler(MessageHandler(Filters.text, echo))
    dp.add_handler(CommandHandler("weather", weather))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()

