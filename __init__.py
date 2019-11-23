'''
    树莓派智能摄像头:
        1. 启动后长按按钮3秒录制,单击按钮拍照
        2. 拍照过程中LED闪烁,录制过程中LED长亮
        3. 再次按下按钮结束录制,LED灯泡熄灭

        - 拍照文件保存至 /img
        - 视频文件保存至 /video
'''
import picamera # 摄像头操作支持库
# 参考手册:https://blog.csdn.net/m0_37509650/article/details/80282646
# [官方文档] https://picamera.readthedocs.io/en/release-1.13/
# https://blog.csdn.net/talkxin/article/details/50504601
import os , time 
import threading as TR


if os.name == 'posix':
    import RPi.GPIO as GPIO
else:
    import GPIO_Win as GPIO
# 针对不同平台的GPIO库进行代码提示优化
# =================== 载入支持库 ==============================

if __name__ ==  '__main__':
    try:
        os.rename('/etc/foo', '/etc/bar')
    except IOError :
            print ("Need root permissions.")
            quit() # 需要root权限以创建文件
else:
    quit ()
# ==================== 启动方式检测 =============================

os.chdir (os.path.dirname((os.path.abspath(__file__)))) # 更改路径到脚本运行目录
os.mkdir ('img',mode=0o777)
os.mkdir ('video',mode=0o777)
DIR_IMG = '/img/'
DIR_VIDEO = '/video/'
EXIT = False # 退出标志符
TH_LIST = []
class CODEING_STATE ():
    get = None
    FREE = 0 # 空闲
    RECODING = 1 # 录制中
    TRANSCODING = 2 # 文件编码
# ===================== 常量赋值 ============================

GPIO.setmode (GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup (18,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup (19,GPIO.OUT)
STATELED = GPIO.PWM (19,0.2) # 录制状态led灯泡的PWM类
# ====================== GPIO初始化 ===========================

PICM = picamera.PiCamera() #实例化
PICM.video_stabilization = True # 摄像稳定
PICM.framerate = 24 # 帧率
PICM.resolution = (1920,1080) # 1080p
# ====================== PiCamera初始化 ===========================

def getTimeStamp (): # 获取时间戳
    '''获取时间戳'''
    fmt='%Y-%m-%d-%a-%H-%M-%S'      #定义时间显示格式
    return time.strftime(fmt,time.localtime())     #把传入的元组按照格式，输出字符串
# ======================= 辅助函数 ===============================

def stateListener ():
    global EXIT,CODEING_STATE,STATELED
    STATELED.start (50)
    FREQUENCY = 0.2
    try:
        while not EXIT:
            if CODEING_STATE.get == CODEING_STATE.FREE: # 空闲, 慢速闪烁
                if not (FREQUENCY == 0.2) : # 如果频率不等于12,更改为12
                    STATELED.ChangeFrequency (0.2)
                    FREQUENCY = 0.2
            elif CODEING_STATE.get == CODEING_STATE.RECODING: # 录制中,快速闪烁
                if not (FREQUENCY == 12):
                    STATELED.ChangeFrequency (12)
                    FREQUENCY = 12
            elif CODEING_STATE == CODEING_STATE.RECODING: # 编码中,弱光
                if not (FREQUENCY == 30):
                    STATELED.ChangeFrequency (30)
                    FREQUENCY = 30
            time.sleep (1)
    except KeyboardInterrupt:
        EXIT = True
TH_STATE_LISTENER = TR.Thread (target=stateListener)
TH_STATE_LISTENER.start ()
TH_LIST.append (TH_STATE_LISTENER)
# ======================= LED监听初始化 ==========================

def buttonListener ():
    '''录制按钮的监听程序'''
    global EXIT,CODEING_STATE,DIR_VIDEO
    try:
        while not EXIT:
            if GPIO.wait_for_edge (18,GPIO.RISING,bouncetime=200,timeout=1000) != None: # 等待按钮按下
                CODEING_STATE.get = CODEING_STATE.RECODING # 按钮按下,开始录制 设置标记
                with open (DIR_VIDEO+getTimeStamp+'.h264','wb') as stream:
                    time.sleep (1)
                    PICM.start_recording(stream,format='h264',quality=35) # 开始录制
                    GPIO.wait_for_edge (18,GPIO.FALLING,bouncetime=200) # 等待按钮再次按下
                    PICM.stop_recording () # 停止录制
                
    except KeyboardInterrupt:
        PICM.stop_preview ()
        PICM.stop_recording () # 停止录制
        EXIT = True
TH_BUTTON_LISTENER = TR.Thread(target=buttonListener)
TH_BUTTON_LISTENER.start ()
TH_LIST.append (TH_BUTTON_LISTENER)
# ======================= 按钮监听初始化 ==========================


while not EXIT: # 循环事件
    time.sleep (1) # 循环事件
else:
    for i in TH_LIST:
        i.join () # 等待线程结束
    quit ()