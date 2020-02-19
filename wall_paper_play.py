import json
import logging
import os
import shutil
import time
import win32api
import win32con
import win32gui
from PIL import Image, ImageDraw
from ctypes import *
from threading import Thread
from time import sleep

# ffmpeg -i "/mnt/e/视频/[U3-Project] Liz and the Blue Bird [BD AVC 1080p DTS-HDMA FLAC PGS].mkv" -vf "drawtext=fontsize=15:fontcolor=gray:text='%{pts\:hms}'" -r 5 -q:v 2 -f image2 "/mnt/e/视频/images/%05d.jpeg"

user32 = windll.user32
kernel32 = windll.kernel32
psapi = windll.psapi

ENV_CONFIG_KEY = 'WALL_PAPER'
DEFAULT_CONFIG = {
    "imageFolderPath": "images",
    "sleepTime": 0.2,
    "imageIndex": 0,
    "noWindowPlayTime": 3,
    "checkWindowTime": 1,
    "logPath": "wall_paper.log",
    "isCopyWallPaper": False,
    "currentWallPaperName": "current_wall_paper.jpg",
    "currentBlackWallPaperName": "current_black_wall_paper.jpg",
    "blackConcentration": 230,
}
DEFAULT_CONFIG_JSON_STRING = json.dumps(DEFAULT_CONFIG)


def get_config():
    config_json_string = os.getenv(ENV_CONFIG_KEY, DEFAULT_CONFIG_JSON_STRING)
    logging.info('环境变量读取配置: %r', config_json_string)

    try:
        config = json.loads(config_json_string)
        logging.info('反序列化配置: %r', config)
    except:
        logging.error('反序列化配置失败')
        return DEFAULT_CONFIG

    for key, value in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = value

    logging.info('生成配置: %r', config)
    return config


def save_config(config):
    config_json_string = json.dumps(config)
    logging.info('序列化配置: %r', config_json_string)
    cmd = 'setx %s "%s"' % (ENV_CONFIG_KEY, config_json_string.replace('"', '\\"'))
    logging.info('环境变量保存配置命令: %r', cmd)
    os.system(cmd)
    logging.info('保存配置完成')


def config_log():
    config_json_string = os.getenv(ENV_CONFIG_KEY, DEFAULT_CONFIG_JSON_STRING)
    print('环境变量读取配置: %s' % config_json_string)

    try:
        config = json.loads(config_json_string)
        print('反序列化配置: %r' % config)
    except:
        print('反序列化配置失败')
        config = DEFAULT_CONFIG

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


def copy_current_wall_paper(wall_paper_path, config):
    logging.info('开始复制当前壁纸')
    if wall_paper_path is None or wall_paper_path is '':
        logging.info('壁纸路径为空，不进行当前壁纸替换')
        return
    current_wall_paper_name = config['currentWallPaperName']
    image_folder_path = config['imageFolderPath']
    current_wall_paper_path = os.path.abspath(os.path.join(image_folder_path, os.path.pardir, current_wall_paper_name))
    shutil.copyfile(wall_paper_path, current_wall_paper_path)
    logging.info('成功复制当前壁纸')


def black_current_wall_paper(wall_paper_path, config):
    logging.info('开始黑遮罩当前壁纸')
    if wall_paper_path is None or wall_paper_path is '':
        logging.info('壁纸路径为空，不进行当前壁纸黑遮罩')
        return
    current_black_wall_paper_name = config['currentBlackWallPaperName']
    image_folder_path = config['imageFolderPath']
    black_concentration = config['blackConcentration']
    current_wall_paper_path = os.path.abspath(
        os.path.join(image_folder_path, os.path.pardir, current_black_wall_paper_name))
    image = Image.open(wall_paper_path)
    image = image.convert("RGBA")
    black_image = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(black_image)
    draw.rectangle(((0, 0), image.size), fill=(0, 0, 0, black_concentration))
    image = Image.alpha_composite(image, black_image)
    image = image.convert("RGB")
    image.save(current_wall_paper_path)
    logging.info('成功黑遮罩当前壁纸')


def config_wall_paper():
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

    def interrupt(self):
        self._running = False
        # 让调用方停一停，等本线程的run的sleep过了结束
        sleep_time = self.config['sleepTime']
        time.sleep(sleep_time * 2)

    def run(self):
        image_folder_path = self.config['imageFolderPath']
        image_index = self.config['imageIndex']
        sleep_time = self.config['sleepTime']

        while self._running:
            if not os.path.exists(image_folder_path):
                logging.error('文件夹不存在: %r', image_folder_path)
                break
            files = os.listdir(image_folder_path)
            if files is None or len(files) == 0:
                logging.error('文件夹没有文件')
                break
            if image_index < 0 or image_index >= len(files):
                logging.info('重置图片下标为0, image_index: %r', image_index)
                image_index = 0
            for index in range(image_index, len(files)):
                wall_paper_path = os.path.join(image_folder_path, files[index])
                set_wall_paper(wall_paper_path)
                image_index = image_index + 1
                time.sleep(sleep_time)
                if not self._running:
                    break

        self.config['imageIndex'] = image_index
        save_config(self.config)
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
    config = get_config()
    check_window_time = config['checkWindowTime']
    no_window_play_time = config['noWindowPlayTime']

    no_window_time = 0
    wall_paper_task = None
    names = [[None, None], [None, None]]

    while True:
        name = get_process_name()
        names.pop(0)
        names.append(name)
        logging.info('焦点窗口检查: %r', names)
        if names is None or len(names) != 2 or \
                names[0] is None or len(names[0]) != 2 or \
                names[1] is None or len(names[1]) != 2:
            logging.error('非法窗口结构')
            sleep(check_window_time)
            continue

        explorer = names[0][0] != None and names[0][0].lower() == 'explorer.exe' and \
                   names[0][1] != None and names[0][1].lower() == '' and \
                   names[1][0] != None and names[1][0].lower() == 'explorer.exe' and \
                   names[1][1] != None and names[1][1].lower() == ''

        hipstray = names[0][0] != None and names[0][0].lower() == 'hipstray.exe' and \
                   names[0][1] != None and names[0][1].lower() == '' and \
                   names[1][0] != None and names[1][0].lower() == 'hipstray.exe' and \
                   names[1][1] != None and names[1][1].lower() == ''

        program_manager = names[0][0] != None and names[0][0].lower() == 'explorer.exe' and \
                          names[0][1] != None and names[0][1].lower() == 'program manager' and \
                          names[1][0] != None and names[1][0].lower() == 'explorer.exe' and \
                          names[1][1] != None and names[1][1].lower() == 'program manager'

        if explorer or hipstray or program_manager:
            logging.info('空桌面')
            no_window_time = no_window_time + check_window_time
            if no_window_time > no_window_play_time and wall_paper_task is None:
                logging.info('创建并启动线程')
                wall_paper_task = WallPaperTask(config)
                thead = Thread(target=wall_paper_task.run, daemon=True)
                thead.start()
        elif wall_paper_task is not None:
            logging.info('非空桌面，销毁线程')
            wall_paper_task.interrupt()
            no_window_time = 0
            wall_paper_task = None

        sleep(check_window_time)


def main():
    config_log()
    config_wall_paper()
    check_focus()


if __name__ == '__main__':
    main()
