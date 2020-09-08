import json
import logging
import os
import shutil
import time
from ctypes import *
from threading import Thread
from time import sleep

import win32api
import win32con
import win32gui
from PIL import Image, ImageDraw
from pydub import AudioSegment
from pydub.playback import play

# ffmpeg -i "E:/bt/视频/video.mkv" -vf "drawtext=fontsize=15:fontcolor=gray:text='%{pts\:hms}'" -r 4 -q:v 2 -f image2 "E:/bt/视频/images/%05d.jpeg"
# ffmpeg -i "E:/bt/视频/video.mkv" -ac 2 "E:/bt/视频/audio.wav"
# pydub只支持一通道或者两通道的音频

user32 = windll.user32
kernel32 = windll.kernel32
psapi = windll.psapi

CONFIG_FILE_PATH = 'wall_paper_play.json'
DEFAULT_CONFIG = {
    "imageFolderPath": "images",
    "imageIndex": 0,
    "frameRate": 4,

    "audioPath": "",
    "audioVolume": -10,
    "audioLength": 10000,
    "audioFadeIn": 3000,
    "audioFadeOut": 4000,

    "noWindowPlayTime": 3,
    "checkWindowTime": 1,
    "logPath": "wall_paper.log",

    "currentWallPaperPath": "",
    "currentBlackWallPaperPath": "",
    "blackConcentration": 230,
}
DEFAULT_CONFIG_JSON_STRING = json.dumps(DEFAULT_CONFIG)
CONFIG = None
AUDIO_SONG = None


def load_config():
    if not os.path.exists(CONFIG_FILE_PATH):
        print('加载配置，配置文件不存在')
        return None

    config_json_string = None
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config_json_string = f.read()
    except:
        print('读取配置文件失败')
        return None
    # print('配置文件读取配置: ', config_json_string)

    try:
        config = json.loads(config_json_string)
        # print('反序列化配置: ', config)
    except:
        print('反序列化配置失败')
        return None

    return config


def flush_config():
    new_config = load_config()
    if new_config == None:
        return

    global CONFIG, DEFAULT_CONFIG
    if CONFIG == None:
        init_log(new_config)
        init_audit(new_config)
    else:
        if 'logPath' in new_config and new_config['logPath'] != CONFIG['logPath']:
            init_log(new_config)
        if 'audioPath' in new_config and new_config['audioPath'] != CONFIG['audioPath']:
            init_audit(new_config)

    for key, value in DEFAULT_CONFIG.items():
        if key not in new_config:
            new_config[key] = value
    CONFIG = new_config
    logging.info('刷新配置: %r', CONFIG)


def save_config(config):
    if config == None:
        logging.error('配置对象为空，保存对象失败')
        return

    try:
        config_json_string = json.dumps(config, indent=4)
        logging.info('序列化配置: %r', config_json_string)
    except:
        logging.error('序列化配置对象失败')
        return

    if not os.path.exists(CONFIG_FILE_PATH):
        logging.error('保存配置，配置文件不存在')
        return

    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write(config_json_string)
    except:
        logging.error('保存配置到文件失败')
        return

    logging.info('配置文件保存成功')


def init_log(config):
    logging.basicConfig(
        filename=config['logPath'],
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%y-%m-%d %H:%M:%S',
    )
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logging.info('初始化日志完成')


def copy_current_wall_paper(wall_paper_path, config):
    logging.info('开始复制当前壁纸')
    if wall_paper_path == None or wall_paper_path == '':
        logging.info('壁纸路径为空，不进行当前壁纸替换')
        return
    current_wall_paper_path = config['currentWallPaperPath']
    if current_wall_paper_path == None or current_wall_paper_path == '':
        logging.info('当前壁纸路径为空，不进行当前壁纸替换')
        return
    shutil.copyfile(wall_paper_path, current_wall_paper_path)
    logging.info('成功复制当前壁纸')


def black_current_wall_paper(wall_paper_path, config):
    logging.info('开始黑遮罩当前壁纸')
    if wall_paper_path == None or wall_paper_path == '':
        logging.info('壁纸路径为空，不进行当前壁纸黑遮罩')
        return
    current_black_wall_paper_path = config['currentBlackWallPaperPath']
    if current_black_wall_paper_path == None or current_black_wall_paper_path == '':
        logging.info('当前黑遮罩壁纸路径为空，不进行当前壁纸黑遮罩')
        return
    black_concentration = config['blackConcentration']
    image = Image.open(wall_paper_path)
    image = image.convert("RGBA")
    black_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(black_image)
    draw.rectangle(((0, 0), image.size), fill=(0, 0, 0, black_concentration))
    image = Image.alpha_composite(image, black_image)
    image = image.convert("RGB")
    image.save(current_black_wall_paper_path)
    logging.info('成功黑遮罩当前壁纸')


def init_audit(config):
    global AUDIO_SONG
    if "audioPath" not in config or config["audioPath"] == None or config["audioPath"] == '':
        logging.info('无音频配置')
        AUDIO_SONG = None
        return
    AUDIO_SONG = AudioSegment.from_file(config["audioPath"])


def play_audio(config):
    global AUDIO_SONG
    if AUDIO_SONG == None:
        logging.info('无音频对象')
        return
    millisecond = config["imageIndex"] / config["frameRate"] * 1000
    song = AUDIO_SONG[millisecond: millisecond + config["audioLength"]]
    song = song + config["audioVolume"]
    song = song.fade_in(config["audioFadeIn"]).fade_out(config["audioFadeOut"])
    play(song)


def init_wall_paper():
    logging.info('开始配置壁纸注册表')
    # 打开指定注册表路径
    reg_key = win32api.RegOpenKeyEx(win32con.HKEY_CURRENT_USER, "Control Panel\\Desktop", 0, win32con.KEY_SET_VALUE)
    # 最后的参数:2拉伸,0居中,6适应,10填充,0平铺
    win32api.RegSetValueEx(reg_key, "WallpaperStyle", 0, win32con.REG_SZ, "2")
    # 最后的参数:1表示平铺,拉伸居中等都是0
    win32api.RegSetValueEx(reg_key, "TileWallpaper", 0, win32con.REG_SZ, "0")
    logging.info('成功配置壁纸注册表')


def set_wall_paper(image_path):
    win32gui.SystemParametersInfo(win32con.SPI_SETDESKWALLPAPER, image_path, win32con.SPIF_SENDWININICHANGE)


class WallPaperTask:
    def __init__(self, config):
        self._running = True
        self.config = config
        self.sleep_time = 1.0 / self.config['frameRate']

    def interrupt(self):
        self._running = False
        # 让调用方停一停，等本线程的run的sleep过了结束
        time.sleep(self.sleep_time * 2)
        play_audio(self.config)

    def run(self):
        image_folder_path = self.config['imageFolderPath']
        image_index = self.config['imageIndex']

        while self._running:
            if not os.path.exists(image_folder_path):
                logging.error('文件夹不存在: %r', image_folder_path)
                break
            files = os.listdir(image_folder_path)
            if files == None or len(files) == 0:
                logging.error('文件夹没有文件')
                break
            if image_index < 0 or image_index >= len(files):
                logging.info('重置图片下标为0, image_index: %r', image_index)
                image_index = 0
            for index in range(image_index, len(files)):
                wall_paper_path = os.path.join(image_folder_path, files[index])
                set_wall_paper(wall_paper_path)
                image_index = image_index + 1
                time.sleep(self.sleep_time)
                if not self._running:
                    break

        self.config['imageIndex'] = image_index
        copy_current_wall_paper(wall_paper_path, self.config)
        black_current_wall_paper(wall_paper_path, self.config)
        logging.info('结束壁纸更换线程')


def get_process_name():
    hwnd = user32.GetForegroundWindow()
    pid = c_ulong(0)
    user32.GetWindowThreadProcessId(hwnd, byref(pid))

    executable = create_string_buffer(512)
    h_process = kernel32.OpenProcess(0x400 | 0x10, False, pid)
    psapi.GetModuleBaseNameA(h_process, None, byref(executable), 512)

    window_title = create_string_buffer(512)
    user32.GetWindowTextA(hwnd, byref(window_title), 512)

    kernel32.CloseHandle(hwnd)
    kernel32.CloseHandle(h_process)

    return [executable.value.decode('gbk'), window_title.value.decode('gbk')]


def check_focus():
    no_window_time = 0
    wall_paper_task = None
    names = [[None, None], [None, None]]

    while True:
        check_window_time = CONFIG['checkWindowTime']
        no_window_play_time = CONFIG['noWindowPlayTime']

        name = get_process_name()
        names.pop(0)
        names.append(name)
        logging.info('焦点窗口检查: %r', names)
        if names == None or len(names) != 2 or \
                names[0] == None or len(names[0]) != 2 or \
                names[1] == None or len(names[1]) != 2:
            logging.error('非法窗口结构')
            sleep(check_window_time)
            continue

        # explorer = names[0][0] != None and names[0][0].lower() == 'explorer.exe' and \
        #            names[0][1] != None and names[0][1].lower() == '' and \
        #            names[1][0] != None and names[1][0].lower() == 'explorer.exe' and \
        #            names[1][1] != None and names[1][1].lower() == ''

        # hipstray = names[0][0] != None and names[0][0].lower() == 'hipstray.exe' and \
        #            names[0][1] != None and names[0][1].lower() == '' and \
        #            names[1][0] != None and names[1][0].lower() == 'hipstray.exe' and \
        #            names[1][1] != None and names[1][1].lower() == ''

        explorer = names[0][1] != None and names[0][1].lower() == '' and \
                   names[1][1] != None and names[1][1].lower() == ''

        program_manager = names[0][0] != None and names[0][0].lower() == 'explorer.exe' and \
                          names[0][1] != None and names[0][1].lower() == 'program manager' and \
                          names[1][0] != None and names[1][0].lower() == 'explorer.exe' and \
                          names[1][1] != None and names[1][1].lower() == 'program manager'

        if explorer or program_manager:
            logging.info('空桌面')
            no_window_time = no_window_time + check_window_time
            if no_window_time > no_window_play_time and wall_paper_task == None:
                logging.info('创建并启动线程')
                flush_config()
                wall_paper_task = WallPaperTask(CONFIG)
                thead = Thread(target=wall_paper_task.run, daemon=True)
                thead.start()
        elif wall_paper_task != None:
            logging.info('非空桌面，销毁线程')
            wall_paper_task.interrupt()
            save_config(wall_paper_task.config)
            no_window_time = 0
            wall_paper_task = None

        sleep(check_window_time)


def main():
    flush_config()
    init_wall_paper()
    check_focus()


if __name__ == '__main__':
    main()
