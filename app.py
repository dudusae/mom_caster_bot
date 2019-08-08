import telegram # 텔레그램 모듈을 임포트합니다.
import config

my_token = config.my_token
bot = telegram.Bot(token = my_token) # bot을 선언합니다.

updates = bot.getUpdates() # 업데이트 내역(받은메시지)을 받아옵니다.

for u in updates:
    print(u.message) # 업데이트 내역 중 메시지를 출력합니다.