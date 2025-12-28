import sys
import typing
import dotenv
import logging
import logging.handlers

from pydantic          import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from itertools         import cycle

ENV_PATH = dotenv.find_dotenv()

class Settings(BaseSettings):

    DATABASE_URL:  SecretStr
    DISCORD_TOKEN: SecretStr

    LOGGING_LEVEL: typing.Literal["DEBUG", "INFO", "ERROR", "WARNING", "CRITICAL"] = "INFO"

    BOT_PREFIX:         str = "."
    LITTLE_ANGEL_COLOR: int = 0x5b00c1

    DEFAULT_ORDINARY_TEXTS: list[str] = ["https://media.discordapp.net/attachments/1121112898173947955/1132372263912603759/HeccTxBWNxo.png", "https://media.discordapp.net/attachments/1121112898173947955/1132372263509954702/IMG_20230711_142256_184.png", "https://media.discordapp.net/attachments/1121112898173947955/1132372263040200884/277228817_1102088540338356_6484851209964957547_n.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1132358006089195710/youtube-eyqIGScJ6Bs.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1132358005669761034/Screenshot_2023-07-20-07-00-59-81_f9ee0578fe1cc94de7482bd41accb329.png", "https://media.discordapp.net/attachments/1121112898173947955/1132358005267124305/VID_20230720_145528_106.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1132358004923175033/IMG_20230604_142358_105.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1132358004507955250/4.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1132358004071735356/6ea79d250d9e5934.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1132358003656495104/meme_1.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1132358003211903086/VID_20230721_165824_835.mp4", "https://tenor.com/view/among-us-among-us-poop-among-us-proof-among-us-prove-prove-it-gif-25395324", "https://tenor.com/view/woman-women-am-i-right-woman-am-i-right-gif-23666905", "https://youtu.be/1-52IfX_HS4", "https://media.discordapp.net/attachments/1121112898173947955/1128370722104942692/alex.usticed3ad17.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1128370721698103368/VE7y97Klp_E.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1128370716962738176/IMG_20230711_142256_184.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1127871593020923924/58b37f908f92acabfcb0491dc7ff5af2.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1127630321924460565/Download_-_2023-07-05T131651.288.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1127630129124888698/20f9a7926d27967b-1.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1127630128671883404/SPOILER_hahaha.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1127630128080506910/0bf2005b3bb4635ebd75af7ec6b010b1.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1126515988750417980/azov.gif", "https://media.discordapp.net/attachments/1121112898173947955/1126515988414857329/VID_20230629_130520_737.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1126515988129656982/Screenshot_20230629_145620_Telegram.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1126515987878002788/FU6YjjTCRGs.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1126515987425013852/VID_20230706_144552_007.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1126515987114639390/Screenshot_2023-07-06-15-41-56-319_org.telegram.messenger-edit.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1126515986758107207/-MGE-STATUS.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1126010979164102716/VID_20230702_174726_006.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1126010978895671306/Qybe6qSRo1o.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1126010978572718130/RPReplay_Final1688408409.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1126010978283298847/yBnFNkkUPFg.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1126010978002284625/VID_20230705_104327_495.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1125714495541608468/youtube-4io8SzKHM6g.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1125714598205599754/VID_20230704_120406_388.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1125440770585919640/VID_20230628_012725_032.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1125440770124566578/caption-1.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1125440769357004800/Screenshot_2023-06-29-21-18-23-416_com.google.android.youtube-edit-1.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1123627871311757372/drunyaldinho_2023-06-27-11-15-07_1687853707288.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1123288260303650978/eda2a3ddf15738b8.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1123288462158725221/IMG_20230624_093016_878.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1123278889595183194/VID_20230626_175818_556.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121774974286450721/videoplayback.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121774974580047984/IMG_20230623_171111.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121774974936547328/94-___.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121774975209197588/CwLFkinHQ6o.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121774975595069450/amuhanumoni_2023-06-21-16-51-26_1687355486876.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121774976077398036/IMG_20230620_210721_445.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121774976433934346/VID_20230612_191945.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121774976874315826/IMG_20230604_215039_408.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121774977335709886/000b882093c59f31-1.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121774977759330334/86fbc74365edf52815ff457c82bbd8a2.png.webp", "https://media.discordapp.net/attachments/1121112898173947955/1121775094805581875/vU3qFdXo3wA.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121775095120150648/trim.6BF8D9C2-2132-4E62-AF96-2E295C9FAD80.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121775095568937051/cachedVideo.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121776919302656051/IMG_20230430_204946_932.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121776919600431215/IMG_20230430_204947_241.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121776919965356062/IMG_20230430_205001.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121776920267337788/trim.93A05836-9F2B-4017-AA5D-A679B74B00BB.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121776920674172999/1683447534613.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121776920955211836/image-47.png", "https://media.discordapp.net/attachments/1121112898173947955/1121776921483673711/IMG_20230430_204947_467.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121776921924087848/yngbl6ss_2023-05-07-12-44-00_1683452640586.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121855241403519087/video0-28.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121855241839714364/xecyccolo_1_2023-05-24-16-49-15_1684918155498.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121855242238177420/80_360p-1-1.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121855255903215726/IMG_20230623_232930_545.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121855256167460924/IMG_20230623_233024_240.jpg", "https://media.discordapp.net/attachments/1121112898173947955/1121855256532373524/VID_20230623_232930_258.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121855256935014470/VID_20230623_232930_174.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121855257379622962/VID_20230623_232930_894.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121855257807429803/VID_20230623_232949_342.mp4", "https://media.discordapp.net/attachments/1121112898173947955/1121855488099889152/VID_20230101_133602_447-1.mp4"]
    DEFAULT_NSFW_TEXTS:     list[str] = ["Похотливый человек-паук мастурбирует, разряжает паутину. Смотреть онлайн\nhttps://gay0day.com/ru/videos/154192/lustful-spiderman-masturbates-discharges-web/", "https://cdn.discordapp.com/attachments/1028040824862289920/1037496997567021107/animated-toon-3sum_360.mp4"]

    ACTIVITY_NAMES: cycle = cycle([
        {
            "name": "🖤 Memento Mori",
            "streaming_url": ""
        },
        {
            "name": "няшные котики",
            "streaming_url": "https://www.twitch.tv/jasteeq"
        }
    ])

    BOT_LOGS_CHANNEL_ID:         int = 1380518098053894146
    GUILD_ID:                    int = 1380518097114497095
    SPAM_SUGGESTIONS_CHANNEL_ID: int = 1380820965436428361
    AUTOMOD_LOGS_CHANNEL_ID:     int = 1415381171939967076

    ADS_CHANNELS_IDS: typing.List[int] = [
        1434948088199516302, 
        1441759667217764462, 
        1434634895602225172
    ]

    PROTECTED_CHANNELS_IDS: typing.List[int] = [
        1415337442327789568,
        1380586615214178445,
        1421844403802341377,
        1438948881533505649,
        1434731894251065477,
        1445045932600197221,
        1436379767409737910,
        1415381171939967076,
        1380518098053894146,
        1415383643437928509,
        1415357514974887937,
        1415371944894926929,
        1434761574215848068,
        1435943738688929934,
        1415369367864082435,
        1445094411498291230,
        1415345171092213782,
        1449068959121936394,
        1454815375152648395
    ]

    # ROFLS_CHANNEL_ID: int = 1437046827315892375

    model_config = SettingsConfigDict(
        env_file=ENV_PATH, enable_decoding="utf-8"
    )

config = Settings()

# Логирование
def setup_logging():
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    stdout_handler = logging.StreamHandler(stream=sys.stdout)
    stdout_handler.setFormatter(
        logging.Formatter('[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')
    )

    backup_handler = logging.handlers.TimedRotatingFileHandler(
        filename='logs/tmp.log', 
        when='D', 
        interval=1, 
        backupCount=10, 
        encoding='utf-8', 
        delay=False
    )
    backup_handler.setFormatter(
        logging.Formatter('[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s')
    )
    
    root_logger.setLevel(config.LOGGING_LEVEL)
    root_logger.addHandler(stdout_handler)
    root_logger.addHandler(backup_handler)
    
    logging.getLogger('discord').setLevel(logging.ERROR)
    logging.getLogger('discord.client').setLevel(logging.ERROR)
    logging.getLogger('discord.gateway').setLevel(logging.ERROR)
    # logging.getLogger('discord.http').setLevel(logging.ERROR)
    logging.getLogger('discord.webhook.async_').setLevel(logging.ERROR)
    
    # logging.getLogger('apscheduler').setLevel(logging.WARNING)

setup_logging()