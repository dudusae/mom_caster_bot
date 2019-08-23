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
    chat_txt = update.message.text

    if '딸' in chat_txt:
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

    find_location = db.location.find({'읍면동': {'$regex':chat_txt+'$'}})
    find_locations = []

    for i in find_location:
        find_locations.append(i)

    # 1 검색결과가 1개일 때 DB에 저장하고 저장했다고 알려줌
    if len(find_locations) == 1:
        reply_keyboard = [[emojize('아니요 알려주세요:raised_hands:', use_aliases=True),
                           emojize('네 이미 알고 있죠:v:', use_aliases=True)]]

        db.user.find_one_and_update({'chat_id': chat_id},
                                    {'$set': {'location_id': find_locations[0]['_id']}})
        update.message.reply_text(find_locations[0]['읍면동']+'이구나 기억했다.\n오늘 일기예보는 확인했니?',
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard,one_time_keyboard=True))
        return WEATHER

    # 2 검색결과가 2개 이상일 때 다시 확인한다
    elif len(find_locations) >= 2:
        reply_keyboard = []
        for i in find_locations:
            reply_keyboard.append(i['시도']+' '+i['시군구']+' '+i['읍면동'])
        reply_keyboard.append('이 중에는 없어요')
        update.message.reply_text(chat_txt + ', 여러 곳이있네. \n이중에 어디를 말하는거니?',
                                  reply_markup=ReplyKeyboardMarkup.from_column(reply_keyboard,one_time_keyboard=True))
        return LOCATION_SELECT

    # 3 입력한 지역정보를 찾을 수 없을 때 다시 물어봄
    else:
        update.message.reply_html('엄마는 잘 모르는 곳인 것 같구나'+emojize(':eyes:', use_aliases=True)
                                  +'\n<b>시, 군, 구</b> 이름으로 알려줘.')
        return LOCATION


def location_null(update, context):
    update.message.reply_html('이중에 없다구?'+ emojize(':speak_no_evil:', use_aliases=True)
                              + '\n엄마가 모르는 동네인가 보다.\n<b>시, 군, 구</b> 이름으로 알려줘.')
    return LOCATION


# 동정보가 없을 경우 시,군,구로 조회
def location_city(update, context):
    chat_id = update.message.chat_id
    chat_txt = update.message.text

    find_location = db.location.find({'$and': [{'시군구': {'$regex':chat_txt+'$'}},{'읍면동':''}]})
    find_locations = []

    for i in find_location:
        find_locations.append(i)

    # 1 검색결과가 1개일 때 DB에 저장하고 저장했다고 알려줌
    if len(find_locations) == 1:
        reply_keyboard = [[emojize('아니요 알려주세요:raised_hands:', use_aliases=True),
                           emojize('네 이미 알고 있죠:v:', use_aliases=True)]]

        db.user.find_one_and_update({'chat_id': chat_id},
                                    {'$set': {'location_id': find_locations[0]['_id']}})
        update.message.reply_text(find_locations[0]['시군구']+'이구나 기억했다.\n오늘 일기예보는 확인했니?',
                                  reply_markup=ReplyKeyboardMarkup(reply_keyboard,one_time_keyboard=True))
        return WEATHER

    # 2 검색결과가 2개 이상일 때 다시 확인한다
    elif len(find_locations) >= 2:
        reply_keyboard = []
        for i in find_locations:
            reply_keyboard.append(i['시도']+' '+i['시군구'])
        reply_keyboard.append('이 중에는 없어요')
        update.message.reply_text(chat_txt + ', 여러 곳이있네. \n이중에 어디를 말하는거니?',
                                  reply_markup=ReplyKeyboardMarkup.from_column(reply_keyboard, one_time_keyboard=True))
        return LOCATION_SELECT

    # 3 입력한 지역정보를 찾을 수 없을 때 다시 물어봄
    else:
        chat_txt = chat_txt[:2]
        find_location = db.location.find({'$and': [{'시군구': {'$regex': '.*' + chat_txt + '.*'}}, {'읍면동': ''}]})
        find_locations = []

        for i in find_location:
            find_locations.append(i)

        if len(find_locations) == 1:
            reply_keyboard = [[emojize('아니요 알려주세요:raised_hands:', use_aliases=True),
                               emojize('네 이미 알고 있죠:v:', use_aliases=True)]]

            db.user.find_one_and_update({'chat_id': chat_id},
                                        {'$set': {'location_id': find_locations[0]['_id']}})
            update.message.reply_text(find_locations[0]['시군구'] + '이구나 기억했다.\n오늘 일기예보는 확인했니?',
                                      reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))
            return WEATHER

        # 2 검색결과가 2개 이상일 때 다시 확인한다
        elif len(find_locations) >= 2:
            reply_keyboard = []
            for i in find_locations:
                reply_keyboard.append(i['시도'] + ' ' + i['시군구'])
            reply_keyboard.append('이 중에는 없어요')
            update.message.reply_text(chat_txt + ', 여러 곳이있네. \n이중에 어디를 말하는거니?',
                                      reply_markup=ReplyKeyboardMarkup.from_column(reply_keyboard,
                                                                                   one_time_keyboard=True))
            return LOCATION_SELECT

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

    if len(location_value) >= 3:
        find_location = db.location.find_one({'$and': [{'시도': location_value[0]},
                                                   {'시군구': location_value[1]},
                                                   {'읍면동': location_value[2]}]})
        update.message.reply_text(find_location['시도']+' '
                                  + find_location['시군구']+' '
                                  + find_location['읍면동']
                                  + '이구나 기억했다.')
    else :
        find_location = db.location.find_one({'$and': [{'시도': location_value[0]},
                                                   {'시군구': location_value[1]}]})
        update.message.reply_text(find_location['시도']+' '
                                  + find_location['시군구']+' '
                                  + '이구나 기억했다.')
    db.user.find_one_and_update({'chat_id': chat_id},
                                {'$set': {'location_id': find_location['_id']}})
    update.message.reply_text('오늘 일기예보는 확인했니?',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))

    return WEATHER


# 날씨를 알려준다
def weather(update, context):
    chat_id = update.message.chat_id
    chat_location_id = db.user.find_one({'chat_id': chat_id})['location_id']
    chat_location = db.location.find_one({'_id': chat_location_id})
    

    url = 'http://newsky2.kma.go.kr/service/SecndSrtpdFrcstInfoService2/ForecastGrib?ServiceKey='
    my_key_weather = config.my_key_weather
    now = datetime.datetime.now()
    today = now.strftime('%Y%m%d')
    release_time = (now - datetime.timedelta(hours=1)).strftime('%H00')
    location_x = str(chat_location['격자 X'])
    location_y = str(chat_location['격자 Y'])


    r = requests.get(url + my_key_weather + '&base_date=' + today + '&base_time='+ release_time +
                     '&nx=' + location_x + '&ny=' + location_y + '&pageNo=1&numOfRows=30&_type=json')
    rjson = r.json()
    weather_response = rjson['response']['body']['items']['item']
    weather_message = ''


    for weather in weather_response:
        find_weather_dic = db.weather_dic.find_one({'cat': weather['category']})

        cat = find_weather_dic['txt']
        valueType = find_weather_dic['valueType']
        value = weather['obsrValue']
        unit = ''

        if 'unit' in find_weather_dic:
            unit = find_weather_dic['unit']
        else:
            unit = ''

        if valueType == 'code':
            value = find_weather_dic[str(value)]
        elif valueType == 'cal':
            if '풍향' in cat:
                value = int(( value + 22.5 * 0.5 ) / 22.5)
                value = find_weather_dic[str(value)]
            elif '풍속' in cat:
                if value < 4:
                    value = '4m/s 연기 흐름에 따라 풍향감지가 가능한 약한 바람'
                elif 4 <= value < 9 :
                    value = '4~9m/s 안면에 감촉을 느끼면서 나뭇잎이 조금 흔들리는 약간 강한 바람'
                elif 9 <= value < 14 :
                    value = '9~14m/s 나무 가지와 깃발이 가볍게 흔들리는 강한 바람'
                elif 14 <= value :
                    value = '14m/s 먼지가 일고, 작은 나무 전체가 흔들리는 매우 강한 바람'
            elif '낙뢰' in cat:
                if 'getForecastGrib' in url:
                    value = db.weather_dic.find_one({'cat': 'LGT1'})[value]

                elif 'getForecastTimeData' in url:
                    value = db.weather_dic.find_one({'cat': 'LGT2'})[value]

        weather_txt = '\n' + cat + ' : ' + str(value) + unit

        if valueType == 'ignore':
            weather_txt = ''

        weather_message = weather_message + weather_txt


    print(weather_message)
    update.message.reply_text('그래, 현재 날씨를 알려줄께.\n'
                              +chat_location['시군구'] + ' ' + chat_location['읍면동'] +'의 현재 날씨란다.\n'
                              +weather_message,
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def weather_skip(update, context):
    chat_id = update.message.chat_id
    gender = db.user.find_one({'chat_id':chat_id})['gender']
    update.message.reply_text('우리'+gender+'이 웬일이래.'+emojize(':innocent:', use_aliases=True)
                              +'\n그래 주소 바뀌면 /location\n'
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
    dp.add_handler(CommandHandler("cancel", cancel))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()

