import telegram # 텔레그램 모듈을 임포트합니다.
import config

my_token = config.my_token
bot = telegram.Bot(token = my_token) # bot을 선언합니다.

updates = bot.getUpdates() # 업데이트 내역(받은메시지)을 받아옵니다.

for u in updates:
    print(u.message) # 업데이트 내역 중 메시지를 출력합니다.

chat_id = bot.getUpdates()[-1].message.chat.id # 마지막으로 문자를 보낸사람 아이디를 찾아서 chat_id에 넣음
bot.sendMessage(chat_id = chat_id, text="너 어디니")