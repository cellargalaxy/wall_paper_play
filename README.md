# wallPaperPlay

这是一个动态壁纸播放器（替换器），会监控窗口焦点。如果没有窗口焦点则会播放壁纸，否则停止。停止后可播放一段音频。

This is a live wallpaper player (replacer) that monitors the window focus.
If there is no window focus, the wallpaper will be played, otherwise it will stop. After stopping, a piece of audio can be played.

不依赖于ffmpeg，但是或许需要ffmpeg来处理视频和音频。

Does not depend on ffmpeg, but may need ffmpeg to handle video and audio.

```batch
ffmpeg -i "E:/bt/视频/video.mkv" -vf "drawtext=fontsize=15:fontcolor=gray:text='%{pts\:hms}'" -r 4 -q:v 2 -f image2 "E:/bt/视频/images/%05d.jpeg"
ffmpeg -i "E:/bt/视频/video.mkv" -ac 2 "E:/bt/视频/audio.wav"
```

第一种选择，可以在可执行文件目录下创建一个名为`wall_paper_play.json`的文件保存配置。

The first option is to create a file named `wall_paper_play.json` in the executable file directory to save the configuration of json.

或者配置一个环境变量，变量名为`WALL_PAPER`，结构为json：

Or configure an environment variable, the variable name is `WALL_PAPER`, and the structure is json:

```json
{
  "imageFolderPath": "E:/bt/视频/images",  //使用ffmpeg生成的图片的文件夹
  "imageIndex": 8000,  //当前播放到图片的下标
  "frameRate": 4,  //每秒多少帧，与ffmpeg的-r参数一致

  "audioPath": "E:/bt/视频/audio.wav",  //音频路径，为空则不播放音频
  "audioVolume": -10,  //音频音量调整
  "audioLength": 10000,  //音频播放毫秒
  "audioFadeIn": 3000,  //音频渐入毫秒
  "audioFadeOut": 4000,  //音频渐出毫秒

  "noWindowPlayTime": 3,  //多少秒无窗口焦点则播放
  "checkWindowTime": 1,  //间隔多久监听一次窗口焦点
  "logPath": "E:/bt/视频/wall_paper.log", //日志路径

  "currentWallPaperPath": "E:/bt/视频/current_wall_paper.jpg",  //保存当前壁纸路径，为空则不保存
  "currentBlackWallPaperPath": "E:/bt/视频/current_black_wall_paper.jpg",  //保存当前黑遮罩壁纸路径，为空则不保存
  "blackConcentration": 230  //黑遮罩壁纸黑程度
}
```

