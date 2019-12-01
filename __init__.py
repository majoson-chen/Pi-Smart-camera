#/usr/bin/python3
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
import os , time , ftplib , sys , pywifi , json , logging
import threading as TR

if os.name == 'posix':
    import RPi.GPIO as GPIO
else:
    import GPIO_Win as GPIO
# 针对不同平台的GPIO库进行代码提示优化
# =================== 载入支持库 ==============================

if __name__ ==  '__main__':
    # if os.geteuid () != 0: # 具有 Root 权限
    #     print ('ERROR: Need root EUID permissions.')
    #     print ('Service Stop')
    #     exit ()
    pass
else:
    quit ()


def getTimeStamp (format='%Y-%m-%d-%a-%H-%M-%S'): # 获取时间戳
    '''获取时间戳'''
    return time.strftime(format,time.localtime())     #把传入的元组按照格式，输出字符串
# ======================= 辅助函数 ===============================


# ==================== 启动方式检测 =============================

os.chdir (os.path.dirname((os.path.abspath(__file__)))) # 更改路径到脚本运行目录
for i in os.listdir ():
    if i == 'video': # 已经创建video
        break
else:
    try:
        os.mkdir ('video',mode=0o755) # 如果没有被 break 说明文件夹没有被创建
    except:
        print ('ERROR : video dir was created failed.')
        quit ()


#logging.basicConfig(level = logging.INFO,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
loger = logging.getLogger (__name__)
loger.setLevel (logging.DEBUG)
handler = logging.FileHandler("log/{0}.txt".format(getTimeStamp('%Y-%m-%d')))
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
loger.addHandler (handler)

# ================== 配置Log & 创建文件夹 ========================

TH_LIST = []
class CODEING_STATE ():
    RECODING = False
    UPLOADING = False
    DECODEING = False
# === FTP===
FTP_HOST = '192.168.3.11'
FTP_USER = 'ftp_127_0_0_1'
FTP_PASSWD = '0000'
FTP_PORT = 21
FTP_BUFSIZE = 1500 # 缓冲区大小
FTP_REFRESH_CLOCK = 600 # FTP服务器每次刷新的间隔
#FTP_ENCODING = 'utf-8' 
REMOVE_CYCLE = 7 # 自动删除大于该天数的视频

# ===================== 常量赋值 ============================

GPIO.setmode (GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup (23,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup (18,GPIO.OUT)
STATELED = GPIO.PWM (18,0.2) # 录制状态led灯泡的PWM类
# ====================== GPIO初始化 ===========================

PICM = picamera.PiCamera() #实例化
PICM.video_stabilization = True # 摄像稳定
PICM.framerate = 24 # 帧率
PICM.resolution = (1920,1080) # 1080p
# ====================== PiCamera初始化 ===========================

def load_config ():
    loger.info ('Loading Config.')
    global FTP_BUFSIZE,FTP_HOST,FTP_PASSWD,FTP_PORT,FTP_REFRESH_CLOCK,FTP_USER,REMOVE_CYCLE
    try:
        with open ('/boot/camera_config.json','r') as config_file:
            try:
                cfg = json.load (config_file)
                FTP_BUFSIZE = cfg['FTP']['FTP_BUFSIZE']
                FTP_HOST = cfg['FTP']['FTP_HOST']
                FTP_PASSWD = cfg['FTP']['FTP_PASSWD']
                FTP_PORT = cfg['FTP']['FTP_PORT']
                FTP_REFRESH_CLOCK = cfg['FTP']['FTP_REFRESH_CLOCK']
                FTP_USER = cfg['FTP']['FTP_USER']
                REMOVE_CYCLE = cfg['FTP']['REMOVE_CYCLE']
            except Exception as e:
                loger.error ('Config read faild | ' + repr (e))
            try:
                # 现在开始连接网络
                wifi = pywifi.PyWiFi ()
                iface = wifi.interfaces () [1] # 第二个无线网卡才是树莓派的WIFI网卡
                if iface.status () == 4: # 4 是已经连接
                    print ('MSG: WIFI connect already. Pass reconnect.')
                else:
                    iface.scan ()
                    time.sleep (10) # 等待扫描完毕
                    for i in iface.scan_results ():
                        if i.ssid == cfg['NETWORK']['SSID']:
                            i.key = cfg['NETWORK']['PASSWD']
                            iface.connect (iface.add_network_profile (i))
                            # 如果与比对的SSID相符
            except Exception as e:
                loger.error ('Wifi connect faild | {0}'.format (repr(e)))
    except Exception as e:
        loger.error ('Config loading faild because of file open error. | {0}'.format(repr (e)))
load_config ()
# ============== 配置读取 & 网络连接 ============================

def stateListener ():
    loger.info ('state-Listener work satrt.')
    global CODEING_STATE,STATELED
    STATELED.start (50)
    FREQUENCY = 0.2
    while True:
        try:
            while True:
                if CODEING_STATE.DECODEING or CODEING_STATE.UPLOADING: # 如果正在上传或转码
                    STATELED.ChangeDutyCycle (100) # 常亮
                elif CODEING_STATE.RECODING == False and CODEING_STATE.UPLOADING == False and CODEING_STATE.DECODEING == False: 
                    # 空闲, 慢速闪烁
                    if not (FREQUENCY == 0.2) : 
                        STATELED.ChangeFrequency (0.2)
                        FREQUENCY = 0.2
                elif CODEING_STATE.RECODING: # 录制中,快速闪烁
                    if not (FREQUENCY == 12): # 如果频率不等于12,更改为12
                        STATELED.ChangeFrequency (12)
                        FREQUENCY = 12
                time.sleep (1)
        except KeyboardInterrupt:
            return
        except Exception as e:
            loger.error ('state-Listener work in trouble | {0}'.format(repr (e)))
        
TH_STATE_LISTENER = TR.Thread (target=stateListener)
TH_STATE_LISTENER.start ()
TH_LIST.append (TH_STATE_LISTENER)
print ('MSG : State listener start now.')
# ======================= LED监听开始 ==========================

def buttonListener ():
    '''录制按钮的监听程序'''
    global CODEING_STATE
    loger.info ('button-Listener work start.')
    try:
        while True:
            try:
                if GPIO.wait_for_edge (23,GPIO.RISING,bouncetime=200,timeout=86400000) != GPIO.RISING: # 等待按钮按下
                    try:
                        for i in os.listdir ('video'):
                            if i == getTimeStamp('%Y-%m-%d'):
                                break
                        else:
                            try:
                                os.mkdir (os.path.join('video',getTimeStamp('%Y-%m-%d')))
                            except:
                                pass
                    except Exception as e:
                        loger.error ("Creat date dir in 'video' faild | {0}".format (e))

                    try:
                        with open (os.path.join('video',getTimeStamp('%Y-%m-%d'),getTimeStamp())+'.h264','wb') as stream:
                            loger.info ('Video now recoding.')
                            PICM.start_recording(stream,format='h264',quality=30) # 开始录制
                            # 30 - 5Mbps 码率
                            CODEING_STATE.RECODING = True
                            time.sleep (3)
                            # 至少录制三秒
                            GPIO.wait_for_edge (23,GPIO.FALLING,bouncetime=200) # 等待按钮再次按下
                            PICM.stop_recording () # 停止录制
                            CODEING_STATE.RECODING = False
                            loger.info ('Video end recoding.')
                    except Exception as e:
                        loger.error ('button-Listener: have something in trouble in recoding {0}'.format(repr(e)))
            except KeyboardInterrupt:
                PICM.stop_recording () # 停止录制
            except SystemExit:
                PICM.stop_recording () # 停止录制
            except Exception as e:
                loger.error ('button-Listener work in trouble | {0}'.format (repr(e)))
                
    except KeyboardInterrupt:
        return
    except Exception as e:
        loger.error ('button-Listener work in trouble | {0}'.format (repr(e)))
TH_BUTTON_LISTENER = TR.Thread(target=buttonListener)
TH_BUTTON_LISTENER.start ()
TH_LIST.append (TH_BUTTON_LISTENER)
print ('MSG : Button listener start now.')
# ======================= 按钮监听开始 ==========================

FTP = ftplib.FTP ()
FTP.set_pasv (False) # 禁用被动模式,使用20端口传输
def FTPWORKER ():
    loger.info ('ftp-worker work start.')
    def login ():
        '''
            登录到服务器,成功返回True,否则False
        '''
        # global FTP
        try:
            FTP.connect(FTP_HOST,port=FTP_PORT)
            FTP.login(FTP_USER,FTP_PASSWD)
            # FTP.encoding = FTP_ENCODING # FTP 服务器使用的是UTF - 8 编码
            FTP.cwd ('/PiCamera') # 挂载到项目目录下
            print ('Ftp server connect successed.')
            loger.info ('ftp-worker: login successed.')
            return True
        except TimeoutError: # 超时
            print ('Connect failed : time out.')
            loger.error ('ftp-worker: login faild.')
            return False
    def is_online ():
        '''判断是否与FTP服务器断开连接 返回 T or F'''
        # global FTP
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

        CODEING_STATE.UPLOADING = True

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
            loger.info ('File upload start: {path}'.format(path=path))
            with open (path,'rb') as fp:
                FTP.storbinary('STOR {path}'.format(os.path.join (dir,os.path.basename(path))), fp, FTP_BUFSIZE)
                # 函数返回即上传成功
            
            CODEING_STATE.UPLOADING = False
            loger.info ('File upload succesed: {path}'.format(path=path))
            return True
        except Exception as e:
            loger.error ('File upload failed. path: {path} | {err}'.format (path=path,err=repr(e)))
            CODEING_STATE.UPLOADING = False
            return False
    # =====辅助函数=====
    loger.info ('ftp-infomation | MSG : FTP_HOST : {0} | FTP_PASSWD : {1} | FTP_PORT : {2}'.format (FTP_HOST,FTP_PASSWD,FTP_PORT))
    login ()
    while True:
        try:
            if not is_online: # 判断是否掉线
                if not login ():
                    time.sleep(FTP_REFRESH_CLOCK)
                    loger.warning('ftp-worker login faild. Pass to wait for next refresh.')
                    # 如果登录失败,等待下次循环
                
            # 遍历本地文件夹
            ALL_LOCAL_FILE = [] # 待上传文件的绝对路径
            try:
                for i_dirlist in os.listdir ('video'):
                    if os.path.isdir (os.path.join('video',i_dirlist)): # 这里是日期文件夹
                        # 如果是文件夹,则列出文件夹内所有的mp4文件
                        for i_file in os.listdir (os.path.join('video',i_dirlist)):
                            if i_file [-4:] == '.mp4': # 如果是mp4文件, 将绝对路径添加到 ALL_FILE
                                ALL_LOCAL_FILE.append (os.path.join('video',i_dirlist,i_file))
            except Exception as e:
                loger.error ("ftp-worker listdir in 'video' faild. | {0}".format (e))
            # 本地文件遍历完成
            
            # 开始比对服务器信息
            # 遍历服务器目录
            try:
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
                                            try:
                                                FTP.delete (os.path.join (name,name_))
                                            except Exception as e:
                                                loger.error ('ftp-worker delete fiel faild | {0}'.format(repr(e)))
                                            
                                            if upload (file_name,name):
                                                # 弹出 ALL_LOCAL_FILE 中的对应项目
                                                ALL_LOCAL_FILE.remove (file_name)
            except Exception as e:
                loger.error ('ftp-worker mlsd cmd fiald | {0}'.format ( repr (e) ))


            # 第一轮筛选完毕 , 已经将所有大小与本地不符 , 且已经上传过的文件弹出

            # 现在开始上传服务器中没有的项目

            for file_name in ALL_LOCAL_FILE:
                CODEING_STATE.UPLOADING = True
                upload (os.path.basename(file_name),file_name[:10])
                # '2019-11-26-Tue-22-42-22'
                # [:10] 即 2019-11-26
            CODEING_STATE.UPLOADING = False

            time.sleep (FTP_REFRESH_CLOCK) # 休眠 , 等待下一次循环

        except Exception as e:
            loger.error ('FTPworker worked in trouble. : {0} ; now retry again.'.format (repr (e)))

        time.sleep (FTP_REFRESH_CLOCK)

    # =======下载操作==========
    # fp = open ('D:\\a.jpg','wb')
    # FTP.retrbinary('RETR ' + '白色.jpg', fp.write, 1024)
    # =================
    # 开始周期循环
    # 文件上传 FTP.storbinary('STOR {path}'.format(), fp, FTP_BUFSIZE)
TH_FTPWORKER = TR.Thread(target=FTPWORKER)
TH_FTPWORKER.start()
TH_LIST.append (TH_FTPWORKER)
print ('MSG : Ftp Worker start now.')
# https://blog.csdn.net/cl965081198/article/details/82803333
# https://blog.csdn.net/liqinghai058/article/details/79483761
# http://blog.sina.com.cn/s/blog_86d691b80100xu2s.html FTP原始命令
# https://blog.csdn.net/liqinghai058/article/details/79483761
# https://blog.csdn.net/qq_28506941/article/details/88345511
# ========================== FTP 监听开始 ==========================

def videodecoder ():
    loger.info ('video-decoder work start.')
    while True:
        try:
            # 开始遍历文件夹
            ALL_FILE = [] # 等待编码文件的绝对路径
            for i_dir in os.listdir ('video'):
                if os.path.isdir (os.path.join('video',i_dir)):
                    # 如果是目录 则说明是日期目录
                    # 继续往下
                    for i_file in os.listdir (os.path.join('video',i_dir)):
                        if i_file [-4:] == '.h264':
                            # 如果是h.264文件,说明还没有被转码
                            # 添加到目录中
                            ALL_FILE.append (os.path.realpath(os.path.join(
                                'video',i_dir,i_file
                            )))



            # 将所有待转码文件进行转码
            for i in ALL_FILE:
                try: # 防止出现编码失败
                    if os.system ('./ffmpeg -i {input} -codec copy {output}'.format (input=i,output=i[:-4] + '.mp4')) == 0:
                        # =0 说明成功
                        try:
                            os.remove (i) # 删除 '.h264' 文件
                        except Exception as e:
                            loger.error ('video-decoder remove file faild in {path} | {err}'.format(path=i,err=repr(e)))
                    else:
                        # 如果失败
                        try:
                            os.remove (i[:-4] + '.mp4')
                        except:
                            loger.error ('video-decoder remove file faild in {path} | {err}'.format(path=i[:-4] + '.mp4',err=repr(e)))
                except:
                    loger.error ('video-decoder decode faild at {path} | {err}'.format (path=i,err=repr(e)))
        except:
            loger.error ('video-decoder worked in trouble | {err}'.format(err=repr(e)))

        time.sleep (FTP_REFRESH_CLOCK * 2)
TH_VIDEOCODER = TR.Thread (target=videodecoder)
TH_VIDEOCODER.start ()
TH_LIST.append (TH_VIDEOCODER)
print ('MSG : Videdecoder Worker start now.')
# FFmepg和x264的编译用于硬件加速: https://blog.csdn.net/weixin_37272286/article/details/93893959
# ffmpeg -i 2018.h264 -codec copy 2018.mp4 直接复制视频流
# ============== 转码监听开始 ================

def autoremove (): # 自动删除程序
    loger.info ('auto-remove work start.')
    global REMOVE_CYCLE
    REMOVE_CYCLE *= 86400
    while True:
        try:
            # 遍历文件
            for i_dir in os.listdir ('video'): # 遍历 video 目录下的日期目录
                    # 当前位于日期目录
                    if os.path.isdir ('video/' + i_dir):
                        # 如果是日期文件夹 , 则进入
                        for i_file in os.listdir ('video/' + i_dir):
                            try:
                                # i_file [:-4] 去掉后缀
                                createTime = time.mktime(time.strptime (i_file [:-4],'%Y-%m-%d-%a-%H-%M-%S')) 
                                # ↑ 此方法将时间转为秒
                                # Such as: 2019-11-28-Thu-22-06-58 => 1574950018.0

                                if (time.time () - createTime) > REMOVE_CYCLE: # 如果大于删除的周期
                                    os.remove (os.path.join ('video',i_dir,i_file)) # 删除文件
                            except Exception as e:
                                loger.error ('auto-remove remove file faild | {0}'.format (repr (e)))
        except Exception as e:
            loger.error ('auto-remove listdir faild | {0}'.format (repr (e)))
        time.sleep (REMOVE_CYCLE)
TH_AUTOREMOVE = TR.Thread (target=autoremove)
TH_AUTOREMOVE.start ()
TH_LIST.append (TH_AUTOREMOVE)
print ('MSG : Autoremove Worker start now.')
# =========== 自动清理 =============

while True:
    try:
        time.sleep (0.5)
    except SystemExit:
        GPIO.cleanup ()
        loger.info ('SystemExit.')
    except KeyboardInterrupt:
        GPIO.cleanup ()
        loger.info ('SystemExit.')
        exit ()

    