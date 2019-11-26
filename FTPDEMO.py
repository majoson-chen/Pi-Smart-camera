import ftplib,os,time

FTP_HOST = '192.168.3.11'
FTP_USER = 'ftp_127_0_0_1'
FTP_PASSWD = '0000'
FTP_PORT = 21
FTP_BUFSIZE = 1500 # 缓冲区大小
FTP_REFRESH_clock = 600 # FTP服务器每次刷新的间隔
FTP_ENCODING = 'utf-8' 

class FTPOBJ ():
    def __init__ (self):
        self.FTP = ftplib.FTP ()
    
    def is_online (self):
        try:
            self.FTP.nlst ('')
            return True
        except:
            return False

    def login (self, host , user , passwd , acct='' , port=0 , timeout=-999 , source_address=None ):
        '''
            登录FTP,成功返回 True 失败返回 False

            - source_address 代理服务器的元组 (host,port)
        '''
        try:
            self.FTP.connect (host,port,timeout,source_address)
            self.FTP.login (user,passwd,acct)
            return True
        except:
            return False

    def get_all_list (self,path=''):
        '''
            返回目录下的所有文件夹与文件,返回格式如:
            [('f','a.txt'),('d',b),('f','b'),('d','.dir')]
            f为文件, d为文件夹
        '''
        result = []
        return_list = []
        self.FTP.retrlines('LIST {path}'.format(path=path),result.append)
        for i in result:
            if i[0] == 'd' or i [0] == '1': # 文件夹
                if i [i.rfind(' ')+1:] == '.' or i [i.rfind(' ')+1:] == '..':
                    continue # 省略掉 '.' 和 '..' 两个目录
                return_list.append ( ('d', i [i.rfind(' ')+1:] ) )
                continue
            if i [0] == '-': # 文件
                return_list.append ( ('f', i [i.rfind(' ')+1:] ) )
                continue
        return return_list

        


    def get_file_info (self,path=''):
        pass
        

import time
FTP = FTPOBJ ()
FTP.login (FTP_HOST,FTP_USER,FTP_PASSWD)
print (FTP.get_all_list())
