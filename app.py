from telegram import (ReplyKeyboardMarkup, ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
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


# 딸, 아들 정보 저장하고 지역을 물어본다.
def gender(update, context):
    chat_id = update.message.chat_id
    chat_txt = update.message.text
    db_chat_id = db.user.find_one({'chat_id': chat_id})['chat_id']

    if '딸' in chat_txt:
        gender = '딸'
    else:
        gender = '아들'


    if chat_id == db_chat_id:
        db.user.find_one_and_update({'chat_id': chat_id},
                                {'$set': {'gender': gender}})
    else:
        db.user.insert_one({'chat_id': chat_id, 'gender': gender})


    update.message.reply_text('우리'+gender+emojize(':heart:', use_aliases=True)+
                              '밥먹었니?\n나는 날씨를 알려주는 날씨 엄마란다',
                              reply_markup=ReplyKeyboardRemove())
    update.message.reply_html('날씨를 알고 싶은 <b>동 이름</b>을 알려주면 날씨 소식을 전해줄게.')

    return LOCATION


def gender_error(update, context):
    update.message.reply_text('누구냐? 딸이냐 아들이냐'+emojize(':shit:', use_aliases=True))


# 입력한 지역정보의 좌표가 DB에 있는지 검색하고, 사용자 지역정보에 저장한다
def location_find(update, context):
    chat_id = update.message.chat_id
    chat_txt = update.message.text

    location_unit, location = location_find_round_1(chat_txt)
    
    i = 0
    while i <= 1:
        locations = []
        for i in location:
            locations.append(i)

        # 좌표DB를 검색하여 일치하는 지역이 1개일 경우 바로 저장한다
        if len(locations) == 1:
            return location_save(chat_id, locations, location_unit, update)

        # 좌표DB를 검색하여 일치하는 지역이 2개일 경우 여러 지역 중 어디가 맞는지 되묻는다
        elif len(locations) >= 2:
            return location_select(chat_txt, locations, location_unit, update)

        # 좌표DB를 검색하여 일치하는 지역이 없을경우 검색범위를 확장하여 재검색한다.
        else:
            location = location_find_round_2(location_unit, chat_txt)
            i = i+1
    
    else:
        return location_null(update)


def location_find_round_1(chat_txt):
    if chat_txt[-1] in {'읍', '면', '동'}:
        location_unit = '읍면동'
        location = db.location.find({'읍면동': {'$regex': chat_txt + '$'}})

    elif chat_txt[-1] in {'시', '군', '구'}:
        location_unit = '시군구'
        location = db.location.find({'$and': [{'시군구': {'$regex': chat_txt + '$'}}, {'읍면동': ''}]})
    return location_unit, location


def location_find_round_2(location_unit, chat_txt):
    if location_unit == '읍면동':
        location = db.location.find({'읍면동': {'$regex': '.*' + chat_txt[:2] + '.*'}})
    elif location_unit == '시군구':
        location = db.location.find({'$and': [{'시군구': {'$regex': '.*' + chat_txt[:2] + '.*'}}, {'읍면동': ''}]})
    return location


def location_save(chat_id, locations, location_unit, update):
    db.user.find_one_and_update({'chat_id': chat_id},
                                {'$set': {'location_id': locations[0]['_id']}})
    update.message.reply_text(locations[0][location_unit] + '이구나 기억했다.')
    keyboard_weather_request(update)

    return WEATHER


def location_select(chat_txt, locations, location_unit, update):
    reply_keyboard = []
    for i in locations:
        if location_unit =='읍면동':
            reply_keyboard.append(i['시도'] + ' ' + i['시군구'] + ' ' + i['읍면동'])
        elif location_unit =='시군구':
            reply_keyboard.append(i['시도'] + ' ' + i['시군구'])

    reply_keyboard.append('이 중에는 없어요')
    update.message.reply_text(chat_txt + ', 여러 곳이있네. \n이중에 어디를 말하는거니?',
                              reply_markup=ReplyKeyboardMarkup.from_column(reply_keyboard, one_time_keyboard=True))
    return LOCATION_SELECT


def location_select_and_save(update, context):
    chat_id = update.message.chat_id
    chat_txt = update.message.text
    location_value = chat_txt.split(' ')

    if len(location_value) >= 3:
        location = db.location.find_one({'$and': [{'시도': location_value[0]},
                                                   {'시군구': location_value[1]},
                                                   {'읍면동': location_value[2]}]})
        update.message.reply_text(location['시도']+' '
                                  + location['시군구']+' '
                                  + location['읍면동']
                                  + '이구나 기억했다.')
    else :
        location = db.location.find_one({'$and': [{'시도': location_value[0]},
                                                   {'시군구': location_value[1]}]})
        update.message.reply_text(location['시도']+' '
                                  + location['시군구']+' '
                                  + '이구나 기억했다.')
    db.user.find_one_and_update({'chat_id': chat_id},
                                {'$set': {'location_id': location['_id']}})
    keyboard_weather_request(update)

    return WEATHER


def keyboard_weather_request(update):
    reply_keyboard = [[emojize('아니요 알려주세요:raised_hands:', use_aliases=True),
                       emojize('네 이미 알고 있죠:v:', use_aliases=True)]]
    update.message.reply_text('\n오늘 일기예보는 확인했니?',
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))


def location_select_null(update, context):
    update.message.reply_html('이중에 없다구?'+ emojize(':speak_no_evil:', use_aliases=True))
    return location_null(update)


def location_null(update):
    update.message.reply_html('엄마는 잘 모르는 곳인 것 같구나' + emojize(':eyes:', use_aliases=True)
                              + '\n<b>다른 지명</b>으로 알려줘.')
    return LOCATION


def location_error(update, context):
    update.message.reply_html('엄마는 나이가 들어서 정확하게 알려줘야해.'+emojize(':see_no_evil:', use_aliases=True)
                              +'\n정확한 <b>동 이름</b>을 다시 알려주렴.')
    return LOCATION


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


    # 날씨API에서 코드형태로 받은 값을 우리가 이해할 수 있는 말로 바꿔준다(ex.POP=강수확률)
    for weather in weather_response:
        weather_dic = db.weather_dic.find_one({'cat': weather['category']})

        category = weather_dic['txt']
        valueType = weather_dic['valueType']
        value = weather['obsrValue']
        unit = ''

        # 날씨 값의 단위(ex.%)가 있는 값은 표시하고 없는값은 표시하지 않는다.
        if 'unit' in weather_dic:
            unit = weather_dic['unit']
        else:
            unit = ''

        # 날씨 값의 유형이 코드값(code)일때 weather_dic DB를 참조하여 변환
        if valueType == 'code':
            value = weather_dic[str(value)]

        # 날씨 값의 유형이 계산식(cal)을 거쳐 코드화 되어야 하는 값일 때 항목에 맞는 계산식을 적용
        elif valueType == 'cal':
            value = weather_calculator(category, url, value, weather_dic)

        weather_txt = '\n' + category + ' : ' + str(value) + unit

        # 지나치게 세부적인 정보(ex.동서성분의 풍속)는 DB에 ignore로 분류하여 표시되지 않도록 한다.
        if valueType == 'ignore':
            weather_txt = ''

        weather_message = weather_message + weather_txt

    keyboard_weather_report(chat_location, update, weather_message)

    return ConversationHandler.END


def weather_calculator(category, url, value, weather_dic):
    if '풍향' in category:
        value = int((value + 22.5 * 0.5) / 22.5)
        value = weather_dic[str(value)]
    elif '풍속' in category:
        if value < 4:
            value = '4m/s 연기 흐름에 따라 풍향감지가 가능한 약한 바람'
        elif 4 <= value < 9:
            value = '4~9m/s 안면에 감촉을 느끼면서 나뭇잎이 조금 흔들리는 약간 강한 바람'
        elif 9 <= value < 14:
            value = '9~14m/s 나무 가지와 깃발이 가볍게 흔들리는 강한 바람'
        elif 14 <= value:
            value = '14m/s 먼지가 일고, 작은 나무 전체가 흔들리는 매우 강한 바람'
    elif '낙뢰' in category:
        if 'getForecastGrib' in url:
            value = db.weather_dic.find_one({'cat': 'LGT1'})[value]
        elif 'getForecastTimeData' in url:
            value = db.weather_dic.find_one({'cat': 'LGT2'})[value]
    return value


def keyboard_weather_report(chat_location, update, weather_message):
    reply_keyboard = [[emojize('엄마최고:thumbsup:', use_aliases=True),
                       emojize('사랑해요:kissing_heart:', use_aliases=True)]]
    update.message.reply_text('그래, 알려줄께.\n'
                              + chat_location['시군구'] + ' ' + chat_location['읍면동'] + '의 현재 날씨란다.\n'
                              + weather_message,
                              reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True))


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

    update.message.reply_text('주소 바뀌었니?')
    update.message.reply_html('날씨를 알고 싶은 <b>동 이름</b>을 알려주면 날씨 소식을 전해줄게.')

    return LOCATION


def cancel(update, context):
    update.message.reply_text('그래 나중에 연락해'+emojize(':ok_woman:', use_aliases=True),
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


# 기타 메시지에 대한 챗봇의 답변 패턴
def echo(update, context):
    chat_id = update.message.chat_id
    chat_txt = update.message.text

    if '엄마최고'in chat_txt:
        update.message.reply_text('오키 이제 엄마는 장보러~'+emojize(':dancer:', use_aliases=True),
                              reply_markup=ReplyKeyboardRemove())
    elif '사랑해요'in chat_txt:
        update.message.reply_text('나도 사랑해 내새끼~'+emojize(':revolving_hearts:', use_aliases=True),
                              reply_markup=ReplyKeyboardRemove())
    elif '엄마' in chat_txt:
        update.message.reply_text('왜~\n'
                                  + '날씨가 알고싶으면' + emojize(':point_right:', use_aliases=True) + '/weather\n'
                                  + '주소가 바뀌었으면' + emojize(':point_right:', use_aliases=True) + '/location')
    else :
        update.message.reply_text(chat_txt)




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

            LOCATION: [MessageHandler(Filters.regex('(동|읍|면|시|군|구)$'), location_find),
                       MessageHandler(Filters.regex('[^(동|읍|면시|군|구)$]'), location_error)],

            LOCATION_SELECT: [MessageHandler(Filters.regex('(동|읍|면|시|군|구)$'), location_select_and_save),
                              MessageHandler(Filters.regex('[^(동|읍|면|시|군|구)$]'), location_select_null)],

            WEATHER: [MessageHandler(Filters.regex('^(아니|아닝|아직)'), weather),
                      MessageHandler(Filters.regex('^(네|넹|넵|응|이미|그럼|당연|ㅇㅇ)'), weather_skip)]
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

