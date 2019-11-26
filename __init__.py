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
import os , time , ftplib
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
for i in os.listdir (''):
    if i == 'video': # 已经创建video
        break
else:
    try:
        os.mkdir ('video',mode=0o777) # 如果没有被 break 说明文件夹没有被创建
    except:
        print ('ERROR : video dir was created failed.')
        quit ()

# ============ 创建文件夹 ============================ 


EXIT = False # 退出标志符
TH_LIST = []
class CODEING_STATE ():
    get = None
    FREE = 0 # 空闲
    RECODING = 1 # 录制中
    BUSY = 2 # 转码 & 上传中
# === FTP===
FTP_HOST = '192.168.3.11'
FTP_USER = 'ftp_127_0_0_1'
FTP_PASSWD = '0000'
FTP_PORT = 21
FTP_BUFSIZE = 1500 # 缓冲区大小
FTP_REFRESH_CLOCK = 600 # FTP服务器每次刷新的间隔
#FTP_ENCODING = 'utf-8' 
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

# def getFileName (path): 
#     '''
#         传入一个文本,返回在最后一个 '/' 之后的全部字符
#         例如: '/a/b/c.exe' 返回 'c.exe'
#     '''
#     index = 0
#     for i in path[::-1]:
#         if i == '/':
#             break
#         index += 1
 
#     return path [-1:0-index+1]
def getTimeStamp (format='%Y-%m-%d-%a-%H-%M-%S'): # 获取时间戳
    '''获取时间戳'''
    return time.strftime(format,time.localtime())     #把传入的元组按照格式，输出字符串
# ======================= 辅助函数 ===============================

def stateListener ():
    global EXIT,CODEING_STATE,STATELED
    STATELED.start (50)
    FREQUENCY = 0.2
    try:
        while not EXIT:
            if CODEING_STATE.get == CODEING_STATE.BUSY: # 如果正在上传或转码
                STATELED.ChangeDutyCycle (100) # 常亮

            elif CODEING_STATE.get == CODEING_STATE.FREE: # 空闲, 慢速闪烁
                if not (FREQUENCY == 0.2) : 
                    STATELED.ChangeFrequency (0.2)
                    FREQUENCY = 0.2
            elif CODEING_STATE.get == CODEING_STATE.RECODING: # 录制中,快速闪烁
                if not (FREQUENCY == 12): # 如果频率不等于12,更改为12
                    STATELED.ChangeFrequency (12)
                    FREQUENCY = 12

            time.sleep (1)
    except KeyboardInterrupt:
        EXIT = True
TH_STATE_LISTENER = TR.Thread (target=stateListener)
TH_STATE_LISTENER.start ()
TH_LIST.append (TH_STATE_LISTENER)
# ======================= LED监听开始 ==========================

def buttonListener ():
    '''录制按钮的监听程序'''
    global EXIT,CODEING_STATE

    while not EXIT:
        try:
            if GPIO.wait_for_edge (18,GPIO.RISING,bouncetime=200,timeout=1000) != None: # 等待按钮按下
                CODEING_STATE.get = CODEING_STATE.RECODING # 按钮按下,开始录制 设置标记

                for i in os.listdir ('video'):
                    if i == getTimeStamp('%Y-%m-%d'):
                        break
                else:
                    try:
                        os.mkdir (os.path.join('video',getTimeStamp('%Y-%m-%d')))
                    except:
                        pass
                
                with open (os.path.join('video',getTimeStamp('%Y-%m-%d'),getTimeStamp())+'.h264','wb') as stream:
                    time.sleep (1)
                    PICM.start_recording(stream,format='h264',quality=35) # 开始录制
                    GPIO.wait_for_edge (18,GPIO.FALLING,bouncetime=200) # 等待按钮再次按下
                    PICM.stop_recording () # 停止录制
            
        except KeyboardInterrupt:
            EXIT = True
            PICM.stop_recording () # 停止录制

TH_BUTTON_LISTENER = TR.Thread(target=buttonListener)
TH_BUTTON_LISTENER.start ()
TH_LIST.append (TH_BUTTON_LISTENER)
# ======================= 按钮监听开始 ==========================

FTP = ftplib.FTP ()
def FTPWORKER ():
    global FTP
    # =================
    def login ():
        global FTP
        while True: # 循环连接服务器
            try:
                FTP.connect(FTP_HOST,port=FTP_PORT)
                FTP.login(FTP_USER,FTP_PASSWD)
                # FTP.encoding = FTP_ENCODING # FTP 服务器使用的是UTF - 8 编码
                FTP.cwd ('/PiCamera') # 挂载到项目目录下
                print ('Ftp server connect successed.')
                break
            except TimeoutError: # 超时
                print ('Connect failed : time out.')
            time.sleep (2)
    
    def is_online ():
        '''判断是否与FTP服务器断开连接 返回 T or F'''
        global FTP
        try:
            FTP.dir ('')
            return True
        except:
            return False

    def upload (path,dir=''):
        '''
            上传某个文件到服务器
            成功返回 True , 失败返回 False
            - path 欲上传文件的路径
            - dir  上传目录
        '''

        CODEING_STATE.get == CODEING_STATE.BUSY

        try:
            # 先判断上传目录是否存在,无则创建之
            for i in FTP.mlsd ():
                # i[0] : 文件名 
                if i[0] == dir: # 如果存在 , 跳出循环后上传
                    break
                else:
                    FTP.mkd (dir)
                    break
            
            # 开始上传
            with open (path,'rb') as fp:
                FTP.storbinary('STOR {path}'.format(os.path.join (dir,os.path.basename(path))), fp, FTP_BUFSIZE)
                # 函数返回即上传成功
            
            CODEING_STATE.get = CODEING_STATE.FREE
            return True
        except:
            print ('ERROR: File upload failed. path: {path} .'.format (path))
            CODEING_STATE.get = CODEING_STATE.FREE
            return False
            

    # =====辅助函数=====

    while True:
        try:
            if not is_online: # 判断是否掉线
                login ()

                # 遍历本地文件夹
                ALL_LOCAL_FILE = [] # 待上传文件的绝对路径
                for i_dirlist in os.listdir ('video'):
                    if os.path.isdir (os.path.join('video',i_dirlist)): # 这里是日期文件夹
                        # 如果是文件夹,则列出文件夹内所有的mp4文件
                        for i_file in os.listdir (os.path.join('video',i_dirlist)):
                            if i_file [-4:] == '.mp4': # 如果是mp4文件, 将绝对路径添加到 ALL_FILE
                                ALL_LOCAL_FILE.append (os.path.join('video',i_dirlist,i_file))
                # 本地文件遍历完成
                
                # 开始比对服务器信息
                # 遍历服务器目录
                for name,info in FTP.mlsd (): # 日期目录
                    # mlsd 返回信息如下:
                    # ('.' ,{'type': 'pdir', 'sizd': '4096' ... })
                    # ('..' ,{'type': 'cdir', 'sizd': '4096' ... })
                    # ('_DSC3265.jpg' ,{'type': 'file', 'size': '11954758' ... })
                    # 首先列出所有 mp4 文件
                    if info ['type'] == 'dir': # 对 Picamera 目录下的文件进行筛选

                        for name_ , info_ in FTP.mlsd (name): # 日期目录下的文件
                            # 列出日期目录下的所有文件
                            if info_ ['type'] == 'file':

                                for file_name in ALL_LOCAL_FILE:
                                    # 如果是文件 , 在本地所有文件中进行查找 , 
                                    # 如果找到且文件大小不相等 , 删掉服务器的版本后重新上传
                                    if os.path.basename (file_name) == name_: # 如果文件相同
                                        if os.path.getsize (file_name) == int(info_ ['size']):
                                            # 如果相等,弹出 ALL_LOCAL_FILE 中的对应项目
                                            ALL_LOCAL_FILE.remove (file_name)
                                            break
                                        else:
                                            # 如果不相等 , 重新上传文件
                                            FTP.delete (os.path.join (name,name_))
                                            if upload (file_name,name):
                                                # 弹出 ALL_LOCAL_FILE 中的对应项目
                                                ALL_LOCAL_FILE.remove (file_name)

                # 第一轮筛选完毕 , 已经将所有大小与本地不符 , 且已经上传过的文件弹出

                # 现在开始上传服务器中没有的项目

                for file_name in ALL_LOCAL_FILE:
                    upload (os.path.basename(file_name),file_name[:10])
                    # '2019-11-26-Tue-22-42-22'
                    # [:10] 即 2019-11-26
                
            time.sleep (FTP_REFRESH_CLOCK) # 休眠 , 等待下一次循环

        except Exception as e:
            print ('ERROR : FTPworker worked in trouble. : {0} ; now retry again.'.format (repr (e)))


    # 流程:
    # 循环:
    #   判断是否有上传任务
    #   |     无:
    #   |       | 重新登录 , 比对本地与服务器的信息
    #   |       |    有待上传文件:
    #   |       |        add to list
    #   |       |     无待上传文件:
    #   |       |        放弃,等待下一次循环                    
    #   |     有:
    #   |       | 放弃 , 等待下一次循环 
    #  


    
    # =======下载操作==========
    # fp = open ('D:\\a.jpg','wb')
    # FTP.retrbinary('RETR ' + '白色.jpg', fp.write, 1024)
    # =================
    # 开始周期循环
    # 文件上传 FTP.storbinary('STOR {path}'.format(), fp, FTP_BUFSIZE)


TH_FTPWORKER = TR.Thread(target=FTPWORKER)
TH_FTPWORKER.start()
TH_LIST.append (TH_FTPWORKER)
# https://blog.csdn.net/cl965081198/article/details/82803333
# https://blog.csdn.net/liqinghai058/article/details/79483761
# http://blog.sina.com.cn/s/blog_86d691b80100xu2s.html FTP原始命令
# https://blog.csdn.net/liqinghai058/article/details/79483761
# https://blog.csdn.net/qq_28506941/article/details/88345511
# ========================== FTP 监听开始 ==========================


while not EXIT: # 循环事件
    time.sleep (1) # 循环事件
else:
    for i in TH_LIST:
        i.join () # 等待线程结束
        time.sleep (1)
    quit ()