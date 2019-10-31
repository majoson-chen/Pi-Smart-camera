import picamera # 摄像头操作支持库
# 参考手册:https://blog.csdn.net/m0_37509650/article/details/80282646
# [官方文档] https://picamera.readthedocs.io/en/release-1.13/
# https://blog.csdn.net/talkxin/article/details/50504601
import os , time , io 

if os.name == 'posix':
    import RPi.GPIO as gpio
else:
    import GPIO_Win as gpio

'''
    树莓派智能摄像头:
        1. 启动后长按按钮3秒录制,单击按钮拍照
        2. 拍照过程中LED闪烁,录制过程中LED长亮
        3. 再次按下按钮结束录制,LED灯泡熄灭

        - 拍照文件保存至 /img
        - 视频文件保存至 /video
'''


if __name__ ==  '__main__':
    pass
else:
    quit ()
# 启动方式检测

with open ('video.h264','wb') as stream:

    picm = picamera.PiCamera() #实例化
    picm.video_stabilization = True # 摄像稳定
    picm.framerate = 24 # 帧率
    picm.resolution = (1920,1080) # 1080p

    picm.start_preview()
    time.sleep (2)
    picm.start_recording(stream,format='h264',quality=35)
    time.sleep (10)
    picm.stop_recording ()


