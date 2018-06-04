# coding=utf-8
import os
import sys
import re
import time
import yaml
import getopt
import shutil
import subprocess

from configobj import ConfigObj
from dateutil.relativedelta import relativedelta
from multiprocessing import Pool, Lock
from datetime import datetime
from PB import pb_io, pb_time, pb_name
from PB.CSC.pb_csc_console import SocketServer, LogServer

__description__ = u'交叉主调度处理的函数'
__author__ = 'wangpeng'
__date__ = '2018-05-30'
__version__ = '1.0.0_beat'

python = '/home/gsics/LIB/anaconda2/bin/python -W ignore'

# 启动socket服务,防止多实例运行
port = 10000
sserver = SocketServer()
if sserver.createSocket(port) == False:
    sserver.closeSocket(port)
    print (u'----已经有一个实例在实行')
    sys.exit(-1)

MainPath, MainFile = os.path.split(os.path.realpath(__file__))
cfgFile = os.path.join(MainPath, 'cfg/global.cfg')
PYTHON_PATH = os.environ.get("PYTHONPATH")
odmFile = os.path.join(PYTHON_PATH, 'DM/ODM/dm_odm.cfg')
# odmFile = os.path.join(MainPath, 'cfg/dm_odm.cfg')
inCfg = ConfigObj(cfgFile)
odmCfg = ConfigObj(odmFile)

CROSS_DIR = inCfg['PATH']['IN']['CROSS']
SNOX_DIR = inCfg['PATH']['IN']['SNOX']
ORDER_DIR = inCfg['PATH']['IN']['ORDER']
MVREC_DIR = inCfg['PATH']['IN']['MVREC']
DATA_DIR = inCfg['PATH']['IN']['DATA']
PROJ_DIR = inCfg['PATH']['MID']['PROJ_DATA']
MATCH_DIR = inCfg['PATH']['MID']['MATCH_DATA']
JOBCFG_DIR = inCfg['PATH']['OUT']['JOBCFG']
LogPath = inCfg['PATH']['OUT']['LOG']
Log = LogServer(LogPath)


def usage():
    print(u"""
    -h / --help :使用帮助
    -v / --verson: 显示版本号
    -j / --job : 作业步骤 -j 01 or --job 01
    -s / --sat : 卫星信息  -s FY3B+MERSI_AQUA+MODIS or --sat FY3B+MERSI_AQUA+MODIS
    -t / --time :日期   -t 20180101-20180101 or --time 20180101-20180101
    """)


def CreateYamlCfg(yaml_dict, cfgFile):
    cfgPath = os.path.dirname(cfgFile)
    if not os.path.isdir(cfgPath):
        os.makedirs(cfgPath)
    with open(cfgFile, 'w') as stream:
        yaml.dump(yaml_dict, stream, default_flow_style=False)


def main():

    try:
        opts, args = getopt.getopt(
            sys.argv[1:], "hv:j:s:t:", ["version", "help", "job=", "sat=" "time="])
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(1)

    for key, val in opts:
        if key in ('-v', '--version'):
            verbose = '1.0.1'
            print 'Version: %s' % verbose
            sys.exit()

        elif key in ("-h", "--help"):
            usage()
            sys.exit()

        elif key in ("-j", "--job"):
            job_id = val

        elif key in ("-s", "--sat"):

            sat_pair = val

        elif key in ("-t", "--time"):
            str_time = val
        else:
            assert False, "unhandled option"

    date_s, date_e = pb_time.arg_str2date(str_time)
    date_start = date_s

    job_exe = inCfg['PAIRS'][sat_pair]['job_%s' % job_id]

    if len(job_exe) > 0:
        print 'start %s process ......' % job_id

        if job_id in ['01', '02', '03', '04']:
            # 创建job01 ~ job04 作业需要的输入文件
            craete_incfg_job_01_04(sat_pair, date_s, date_e, job_id)

            # 拼接job01 ~ job04 作业的参数命令行
            arg_list = get_arglist_job01_04(job_exe,
                                            sat_pair, date_start, date_e, job_id)

        elif job_id in ['07']:
            arg_list = get_arglist_job07(
                job_exe, sat_pair, date_s, date_e, job_id)
        elif job_id in ['08']:
            arg_list = get_arglist_job08(
                job_exe, sat_pair, date_s, date_e, job_id)
        elif job_id in ['09', '10']:
            arg_list = get_arglist_job09_10(
                job_exe, sat_pair, date_s, date_e, job_id)
        elif job_id in ['11']:
            arg_list = get_arglist_job11(
                job_exe, sat_pair, date_s, date_e, job_id)

        # 运行所有参数
        run_command(arg_list)
    else:
        print 'job_%s not process ......' % job_id


def get_arglist_job11(job_exe, sat_pair, date_s, date_e, job_id):
    '''
    :月回归
    '''
    Log.info(u'in function get_arglist_job10')
    arg_list = []
    while date_s <= date_e:
        ym = date_s.strftime('%Y%m')

        cmd_list = '%s %s %s %s' % (python, job_exe, sat_pair, ym)
        arg_list.append(cmd_list)
        date_s = date_s + relativedelta(months=1)
    return arg_list


def get_arglist_job09_10(job_exe, sat_pair, date_s, date_e, job_id):
    '''
    :蝴蝶图和日回归
    '''
    Log.info(u'in function get_arglist_job09')
    arg_list = []
    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')

        cmd_list = '%s %s %s %s' % (python, job_exe, sat_pair, ymd)
        arg_list.append(cmd_list)
        date_s = date_s + relativedelta(days=1)
    return arg_list


def get_arglist_job08(job_exe, sat_pair, date_s, date_e, job_id):
    '''
    :国际标准nc合成
    '''
    Log.info(u'in function get_arglist_job08')
    arg_list = []

    cmd_list = '%s %s %s ' % (python, job_exe, sat_pair)
    arg_list.append(cmd_list)
    return arg_list


def get_arglist_job07(job_exe, sat_pair, date_s, date_e, job_id):
    '''
    :国际标准nc生成
    '''
    Log.info(u'in function get_arglist_job07')
    arg_list = []
    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')

        cmd_list = '%s %s %s %s' % (python, job_exe, sat_pair, ymd)
        arg_list.append(cmd_list)
        date_s = date_s + relativedelta(days=1)
    return arg_list


def get_arglist_job01_04(job_exe, sat_pair, date_s, date_e, job_id):

    Log.info(u'in function get_arglist_job01_04')
    arg_list = []
    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')
        cfg_path = os.path.join(
            JOBCFG_DIR, sat_pair, 'job_%s' % job_id, ymd)

        if not os.path.isdir(cfg_path):
            Log.error(u'not found %s ' % (cfg_path))
            date_s = date_s + relativedelta(days=1)
            continue

        Lst = sorted(os.listdir(cfg_path), reverse=False)

        for Line in Lst:
            yaml_file = os.path.join(cfg_path, Line)
            cmd_list = '%s %s %s' % (python, job_exe, yaml_file)
            arg_list.append(cmd_list)

        date_s = date_s + relativedelta(days=1)

    return arg_list


def run_command(arg_list):
    Log.info(u'in function run_command')
    if len(arg_list) > 0:
        pool = Pool(processes=3)
        for cmd_list in arg_list:
            pool.apply_async(command, (cmd_list,))
        pool.close()
        pool.join()


def command(args_cmd):
    '''
    args_cmd: python a.py 20180101  (完整的执行参数)
    '''

    print args_cmd
    try:
        P1 = subprocess.Popen(args_cmd.split())
    except Exception, e:
        Log.error(e)
        return

    timeout = 6000
    t_beginning = time.time()
    seconds_passed = 0

    while (P1.poll() is None):

        seconds_passed = time.time() - t_beginning

        if timeout and seconds_passed > timeout:
            print seconds_passed
            P1.kill()
        time.sleep(1)


def craete_incfg_job_01_04(sat_pair, date_s, date_e, job_id):

    Log.info(u'in function craete_sat_pair_yaml')
    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')

        if 'FIX' in sat_pair:
            create_leo_fix(sat_pair, ymd, job_id)
        elif 'HIRAS' in sat_pair:
            create_leo_leo_fine(sat_pair, ymd, job_id)
        elif job_id in ['01', '02', '03']:
            create_leo_leo_cross(sat_pair, ymd, job_id)
        else:
            print 'job_%s not support %s' % (job_id, sat_pair)
            sys.exit(-1)

        date_s = date_s + relativedelta(days=1)


def create_leo_fix(sat_pair, ymd, job_id):
    '''
    创建 极轨卫星 和 固定点 的作业配置文件
    '''
    Log.info(u'[%s] [%s]' % (sat_pair, ymd))
    shortsat1 = (sat_pair.split('_')[0]).split('+')[0]

    # 解析 cross.cfg中的信息
    NUM1 = inCfg['PAIRS'][sat_pair]['num1']
    NUM2 = inCfg['PAIRS'][sat_pair]['num2']
    sec1 = inCfg['PAIRS'][sat_pair]['sec1']

    # 根据编号在dm_odm.cfg中查找到对应的数据描述信息
    sat1 = odmCfg['ORDER'][NUM1[0]]['SELF_SAT']
    sensor1 = odmCfg['ORDER'][NUM1[0]]['SELF_SENSOR']
    product1 = odmCfg['ORDER'][NUM1[0]]['SELF_PRODUCT']
    interval1 = odmCfg['ORDER'][NUM1[0]]['SELF_INTERVAL']
    reg1 = odmCfg['ORDER'][NUM1[0]]['SELF_REG'][0]

    # 存放俩颗卫星的原始数据目录位置
    inpath1 = os.path.join(DATA_DIR, '%s/%s/%s/%s' %
                           (sat1, sensor1, product1, interval1), ymd[:6])

    # 将所有交叉点时间，根据sec1偏差变为时间段
    timeList = []
    # 拼接预报文件,读取固定点交叉预报文件进行文件获取
    ForecastFile = os.path.join(
        CROSS_DIR, sat1 + '_' + 'FIX', sat1 + '_' + 'FIX' + '_' + ymd + '.txt')

    if os.path.isfile(ForecastFile):
        fp = open(ForecastFile, 'r')
        Lines = fp.readlines()
        fp.close()

        for Line in Lines[10:]:
            hms = Line.split()[1].strip()
            name = Line.split()[2].strip()
            lat = float(Line.split()[3].strip())
            lon = float(Line.split()[4].strip())
            cross_time = datetime.strptime(
                '%s %s' % (ymd, hms), '%Y%m%d %H:%M:%S')
            timeList.append([cross_time, name, lat, lon])

    if len(timeList) <= 0:
        Log.error('cross nums: 0')
        return

    # 每个固定点的组时间偏差sec是不一样的，在这里做区分标记
    cross_sec_group = {}
    for i in xrange(len(NUM2)):
        cross_sec_group[NUM2[i]] = sec1[i]

    # 根据num1对应的数据找到迁移数据清单，提取数据列表

    file_list = find_file(inpath1, ymd, reg1)

    # 根据每个交叉点进行判断，并创建投影的配置文件
    for crossTime in timeList:
        # 根据站点分组，找到对应每个组下面的具体站点名称
        for group in NUM2:
            fixList = odmCfg['FIX_LIST'][group]
            # timeList 0=交叉点时间    1=站点名称  2=经度  3=纬度
            if crossTime[1] in fixList:
                # 根据分组，提取站点对应偏差的秒数，然后把交叉点时间变为时间段
                secs = cross_sec_group[group]
                s_cross_time1 = crossTime[0] - relativedelta(seconds=int(secs))
                e_cross_time1 = crossTime[0] + relativedelta(seconds=int(secs))
                # 从数据列表中查找过此交叉点时间的数据块,查到过此固定点的数据 select File
                file_list1 = Find_data_FromCrossTime(
                    file_list, s_cross_time1, e_cross_time1)
                # 交叉点时间，固定点名称，纬度，经度
                ymdhms = crossTime[0].strftime('%Y%m%d%H%M%S')
                ymdhms1 = crossTime[0].strftime('%Y%m%d %H:%M:%S')
                fixName = crossTime[1]
                Lat = crossTime[2]
                Lon = crossTime[3]

                # 投影后结果的命名方式
                projName1 = '%s_%s_GBAL_L1_%s_%s_proj_lon%+08.3f_lat%+08.3f.hdf' % (
                    shortsat1, sensor1, ymdhms[:8], ymdhms[8:12], Lon, Lat)
                # 投影后的输出全路径名称
                projName1 = os.path.join(
                    PROJ_DIR, sat_pair, ymdhms[:6], projName1)

                cmd = '+proj=laea  +lat_0=%f +lon_0=%f +x_0=0 +y_0=0 +ellps=WGS84' % (
                    Lat, Lon)

                cfgFile1 = os.path.join(JOBCFG_DIR, sat_pair, 'job_%s' % job_id, ymdhms[
                                        :8], '%s_%s.yaml' % (ymdhms, fixName))

                # 调用创建投影配置文件程序生成配置，其中南极和北极需要的分辨率是 512*512，其他256*256
                if len(inFileLst) != 0:
                    Log.info('%s %s create success' % (ymdhms1, fixName))
                    if 'Dome_C' in fixName or 'Greenland' in fixName or 'xinjiangaletai' in fixName:
                        dict1 = {'INFO': {'sat': shortsat1, 'sensor': sensor1, 'ymd': ymdhms},
                                 'PROJ': {'cmd': cmd, 'row': 512, 'col': 512, 'res': 1000},
                                 'PATH': {'opath': projName1, 'ipath': file_list1}}
                        CreateYamlCfg(dict1, cfgFile1)
                    else:
                        dict1 = {'INFO': {'sat': shortsat1, 'sensor': sensor1, 'ymd': ymdhms},
                                 'PROJ': {'cmd': cmd, 'row': 256, 'col': 256, 'res': 1000},
                                 'PATH': {'opath': projName1, 'ipath': file_list1}}
                        CreateYamlCfg(dict1, cfgFile1)
                else:
                    Log.error('%s %s create failed ' % (ymdhms1, fixName))


def create_leo_leo_fine(sat_pair, ymd, job_id):
    '''
    创建精匹配配置接口文件
    '''
    Log.info(u'[%s] [%s]' % (sat_pair, ymd))
    # 解析mathcing: FY3A+MERSI_AQUA+MODIS ,根据下划线分割获取 卫星+传感器 ,再次分割获取俩颗卫星短名
    shortsat1 = (sat_pair.split('_')[0]).split('+')[0]
    shortsat2 = (sat_pair.split('_')[1]).split('+')[0]
    # 解析global.cfg中的信息
    NUM1 = inCfg['PAIRS'][sat_pair]['num1']
    NUM2 = inCfg['PAIRS'][sat_pair]['num2']
    sec1 = inCfg['PAIRS'][sat_pair]['sec1']
    sec2 = inCfg['PAIRS'][sat_pair]['sec2']

    # 根据编号在dm_odm.cfg中查找到对应的数据描述信息
    sat1 = odmCfg['ORDER'][NUM1[0]]['SELF_SAT']
    sensor1 = odmCfg['ORDER'][NUM1[0]]['SELF_SENSOR']
    product1 = odmCfg['ORDER'][NUM1[0]]['SELF_PRODUCT']
    interval1 = odmCfg['ORDER'][NUM1[0]]['SELF_INTERVAL']
    reg1 = odmCfg['ORDER'][NUM1[0]]['SELF_REG'][0]

    sat2 = odmCfg['ORDER'][NUM2[0]]['SELF_SAT']
    sensor2 = odmCfg['ORDER'][NUM2[0]]['SELF_SENSOR']
    product2 = odmCfg['ORDER'][NUM2[0]]['SELF_PRODUCT']
    interval2 = odmCfg['ORDER'][NUM2[0]]['SELF_INTERVAL']
    reg2 = odmCfg['ORDER'][NUM2[0]]['SELF_REG'][0]

    # 存放俩颗卫星的原始数据目录位置
    inpath1 = os.path.join(DATA_DIR, '%s/%s/%s/%s' %
                           (sat1, sensor1, product1, interval1), ymd[:6])
    inpath2 = os.path.join(DATA_DIR, '%s/%s/%s/%s' %
                           (sat2, sensor2, product2, interval2), ymd[:6])

    file_list1 = find_file(inpath1, ymd, reg1)
    file_list2 = find_file(inpath2, ymd, reg2)

    # file_list2是高光普数据，根据list2找list1符合条件的数据
    for filename2 in file_list2:
        name2 = os.path.basename(filename2)
        nameClass = pb_name.nameClassManager()
        info = nameClass.getInstance(filename2)
        if info == None:
            continue
        # 获取数据时间段
        data_stime2 = info.dt_s - timedelta(minutes=5)
        data_etime2 = info.dt_e + timedelta(minutes=5)

        ymdhms = info.dt_s.strftime('%Y%m%d%H%M%S')

        new_file_list1 = Find_data_FromCrossTime(
            file_list1, data_stime2, data_etime2)

        yaml_file = os.path.join(
            JOBCFG_DIR, sat_pair, 'job_%s' % job_id, ymdhms[:8], '%s_%s_%s.yaml' % (ymdhms, sensor1, sensor2))

        # 输出文件命名
        filename = 'W_CN-CMA-NSMC,SATCAL+NRTC,GSICS+MATCHEDPOINTS,%s_C_BABJ_%s.hdf5' % (
            sat_pair, ymdhms)

        # 输出完整路径
        full_filename = os.path.join(
            MATCH_DIR, sat_pair, ymdhms[:4], ymdhms[:8], filename3)
        if len(new_file_list1) > 0:
            dict1 = {'INFO': {'sat1': sat1, 'sensor1': sensor1, 'sat2': sat2, 'sensor2': sensor2, 'ymd': ymdhms},
                     'PATH': {'opath': full_filename, 'ipath1': new_file_list1, 'ipath2': [filename2]}}
            CreateYamlCfg(dict, yaml_file)


def create_leo_leo_cross(sat_pair, ymd, job_id):
    '''
    创建 极轨卫星 和 极轨卫星 的作业配置文件
    '''
    Log.info(u'[%s] [%s]  create cross yaml' % (sat_pair, ymd))
    # 解析mathcing: FY3A+MERSI_AQUA+MODIS ,根据下划线分割获取 卫星+传感器 ,再次分割获取俩颗卫星短名
    shortsat1 = (sat_pair.split('_')[0]).split('+')[0]
    shortsat2 = (sat_pair.split('_')[1]).split('+')[0]
    # 解析global.cfg中的信息
    NUM1 = inCfg['PAIRS'][sat_pair]['num1']
    NUM2 = inCfg['PAIRS'][sat_pair]['num2']
    sec1 = inCfg['PAIRS'][sat_pair]['sec1']
    sec2 = inCfg['PAIRS'][sat_pair]['sec2']

    # 根据编号在dm_odm.cfg中查找到对应的数据描述信息
    sat1 = odmCfg['ORDER'][NUM1[0]]['SELF_SAT']
    sensor1 = odmCfg['ORDER'][NUM1[0]]['SELF_SENSOR']
    product1 = odmCfg['ORDER'][NUM1[0]]['SELF_PRODUCT']
    interval1 = odmCfg['ORDER'][NUM1[0]]['SELF_INTERVAL']
    reg1 = odmCfg['ORDER'][NUM1[0]]['SELF_REG'][0]

    sat2 = odmCfg['ORDER'][NUM2[0]]['SELF_SAT']
    sensor2 = odmCfg['ORDER'][NUM2[0]]['SELF_SENSOR']
    product2 = odmCfg['ORDER'][NUM2[0]]['SELF_PRODUCT']
    interval2 = odmCfg['ORDER'][NUM2[0]]['SELF_INTERVAL']
    reg2 = odmCfg['ORDER'][NUM2[0]]['SELF_REG'][0]

    # 存放俩颗卫星的原始数据目录位置
    inpath1 = os.path.join(DATA_DIR, '%s/%s/%s/%s' %
                           (sat1, sensor1, product1, interval1), ymd[:6])
    inpath2 = os.path.join(DATA_DIR, '%s/%s/%s/%s' %
                           (sat2, sensor2, product2, interval2), ymd[:6])

    # 读取交叉点上的俩颗卫星的交叉时间，1列=经度  2列=纬度  3列=卫星1时间  4列=卫星2时间
    timeList = ReadCrossFile_LEO_LEO(sat1, sat2, ymd)
    if len(timeList) <= 0:
        Log.error('cross nums: 0')
        return

    file_list1 = find_file(inpath1, ymd, reg1)
    file_list2 = find_file(inpath2, ymd, reg2)

    # 根据交叉点时间，找到数据列表中需要的数据 select File
    for crossTime in timeList:
        Lat = crossTime[0]
        Lon = crossTime[1]
        ymdhms = crossTime[2].strftime('%Y%m%d%H%M%S')
        s_cross_time1 = crossTime[2] - relativedelta(seconds=int(sec1))
        e_cross_time1 = crossTime[2] + relativedelta(seconds=int(sec1))
        s_cross_time2 = crossTime[3] - relativedelta(seconds=int(sec2))
        e_cross_time2 = crossTime[3] + relativedelta(seconds=int(sec2))

        # 从数据列表中查找过此交叉点时间的数据块,两颗卫星的数据

        list1 = Find_data_FromCrossTime(
            file_list1, s_cross_time1, e_cross_time1)
        list2 = Find_data_FromCrossTime(
            file_list2, s_cross_time2, e_cross_time2)

        # 存放匹配信息的yaml配置文件存放位置
        yaml_file1 = os.path.join(
            JOBCFG_DIR, sat_pair, 'job_%s' % job_id, ymdhms[:8], '%s_%s.yaml' % (ymdhms, sensor1))

        yaml_file2 = os.path.join(
            JOBCFG_DIR, sat_pair, 'job_%s' % job_id, ymdhms[:8], '%s_%s.yaml' % (ymdhms, sensor2))

        yaml_file3 = os.path.join(
            JOBCFG_DIR, sat_pair, 'job_%s' % job_id, ymdhms[:8], '%s_%s_%s.yaml' % (ymdhms, sensor1, sensor2))

        # 输出文件命名
        filename1 = '%s_%s_GBAL_L1_%s_%s_proj_lon%+08.3f_lat%+08.3f.hdf' % (
            shortsat1, sensor1, ymdhms[:8], ymdhms[8:12], Lon, Lat)
        filename2 = '%s_%s_GBAL_L1_%s_%s_proj_lon%+08.3f_lat%+08.3f.hdf' % (
            shortsat2, sensor2, ymdhms[:8], ymdhms[8:12], Lon, Lat)
        filename3 = 'W_CN-CMA-NSMC,SATCAL+NRTC,GSICS+MATCHEDPOINTS,%s_C_BABJ_%s.hdf5' % (
            sat_pair, ymdhms)

        # 输出完整路径
        full_filename1 = os.path.join(
            PROJ_DIR, sat_pair, ymdhms[:6], filename1)
        full_filename2 = os.path.join(
            PROJ_DIR, sat_pair, ymdhms[:6], filename2)
        full_filename3 = os.path.join(
            MATCH_DIR, sat_pair, ymdhms[:6], filename3)

        # 投影参数
        cmd = '+proj=laea  +lat_0=%f +lon_0=%f +x_0=0 +y_0=0 +ellps=WGS84' % (
            Lat, Lon)

        if len(list1) > 0:

            dict1 = {'INFO': {'sat': shortsat1, 'sensor': sensor1, 'ymd': ymdhms},
                     'PROJ': {'cmd': cmd, 'row': 1024, 'col': 1024, 'res': 1000},
                     'PATH': {'opath': full_filename1, 'ipath': list1}}

            if '01' in job_id:
                Log.info('%s %s %s create proj1 cfg success' %
                         (shortsat1, sensor1, ymdhms))
                CreateYamlCfg(dict1, yaml_file1)

        if len(list2) > 0:

            dict2 = {'INFO': {'sat': shortsat2, 'sensor': sensor2, 'ymd': ymdhms},
                     'PROJ': {'cmd': cmd, 'row': 1024, 'col': 1024, 'res': 1000},
                     'PATH': {'opath': full_filename2, 'ipath': list2}}

            if '02' in job_id:
                Log.info('%s %s %s create proj1 cfg success' %
                         (shortsat2, sensor2, ymdhms))
                CreateYamlCfg(dict2, yaml_file2)

        if len(list1) > 0 and len(list2) > 0:

            row = 1024
            col = 1024
            res = 1000

            if sensor2 in ['MODIS', 'VIIRS']:
                row = 128
                col = 128
                res = 8000
            elif sensor2 in ['IASI', 'GOME', 'CRIS']:
                row = 4100
                col = 4100
                res = 1000

            dict3 = {'INFO': {'sat1': shortsat1, 'sensor1': sensor1, 'sat2': shortsat2, 'sensor2': sensor2, 'ymd': ymdhms},
                     'PATH': {'opath': full_filename3, 'ipath1': list1, 'ipath2': list2},
                     'PROJ': {'cmd': cmd, 'row': row, 'col': col, 'res': res}}

            if '03' in job_id:
                Log.info('%s %s create collocation cfg success' %
                         (sat_pair, ymdhms))
                CreateYamlCfg(dict3, yaml_file3)


def ReadCrossFile_LEO_LEO(sat1, sat2, ymd):

    # 本模块于2017-12-14添加了snox的订购。订购时应注意相同卫星对的情况下，cross与snox内卫星前后顺序是否一致。
    timeList = []
    # 拼接cross, snox预报文件
    Filedir = sat1 + '_' + sat2
    FileName1 = Filedir + '_' + ymd + '.txt'
    FileName2 = Filedir + '_' + 'SNOX' + '_' + ymd + '.txt'
    crossFile = os.path.join(CROSS_DIR, Filedir, FileName1)
    snoxFile = os.path.join(SNOX_DIR, Filedir, FileName2)
    index1 = (1, 2, 3, 4)
    index2 = (1, 2, 3, 4)
    if not os.path.isfile(crossFile):  # 不存在则调换卫星顺序
        Filedir = sat2 + '_' + sat1
        FileName = sat2 + '_' + sat1 + '_' + ymd + '.txt'
        crossFile = os.path.join(CROSS_DIR, Filedir, FileName)
        iddex1 = (4, 5, 6, 1)

    if not os.path.isfile(snoxFile):  # 不存在则调换卫星顺序
        Filedir = sat2 + '_' + sat1
        FileName = Filedir + '_' + 'SNOX' + '_' + ymd + '.txt'
        snoxFile = os.path.join(SNOX_DIR, Filedir, FileName)
        iddex2 = (4, 5, 6, 1)

    Lines1 = []
    Lines2 = []
    # 交叉点预报文件内容
    if os.path.isfile(crossFile):
        fp = open(crossFile, 'r')
        bufs = fp.readlines()
        fp.close()
        # 获取长度不包含头信息
        Lines1 = bufs[10:]

    # 近重合预报文件内容
    if os.path.isfile(snoxFile):
        fp = open(snoxFile, 'r')
        bufs = fp.readlines()
        fp.close()
        # 获取长度
        Lines2 = bufs[10:]

    timelst1 = get_cross_file_timelist(Lines1, index1)
    timelst2 = get_cross_file_timelist(Lines2, index2)
    timeList = timelst1 + timelst2

    return timeList


def get_cross_file_timelist(Lines, index):

    # 获取交叉匹配文件中的信息
    timeList = []
    for Line in Lines:
        ymd = Line.split()[0].strip()
        hms1 = Line.split()[index[0]].strip()
        lat1 = float(Line.split()[index[1]].strip())
        lon1 = float(Line.split()[index[2]].strip())
        hms2 = Line.split()[index[3]].strip()
        cross_time1 = datetime.strptime(
            '%s %s' % (ymd, hms1), '%Y%m%d %H:%M:%S')
        cross_time2 = datetime.strptime(
            '%s %s' % (ymd, hms2), '%Y%m%d %H:%M:%S')
        timeList.append([lat1, lon1, cross_time1, cross_time2])

    return timeList


def Find_data_FromCrossTime(FileList, start_crossTime, end_crossTime):
    dataList = []
    for FileName in FileList:
        name = os.path.basename(FileName)
        nameClass = pb_name.nameClassManager()
        info = nameClass.getInstance(name)
        if info == None:
            continue
        # 获取数据时间段
        data_stime1 = info.dt_s
        data_etime1 = info.dt_e
        if InCrossTime(data_stime1, data_etime1, start_crossTime, end_crossTime):
            dataList.append(FileName)
    return dataList


def InCrossTime(s_ymdhms1, e_ymdhms1, s_ymdhms2, e_ymdhms2):
    '''
    判断俩个时间段是否有交叉
    '''

    if s_ymdhms2 <= s_ymdhms1 <= e_ymdhms2:
        return True
    elif s_ymdhms2 <= e_ymdhms1 <= e_ymdhms2:
        return True
    elif s_ymdhms2 >= s_ymdhms1 and e_ymdhms2 <= e_ymdhms1:
        return True
    else:
        return False


def find_file(path, ymd, reg):
    '''
    path: 要遍历的目录
    reg: 符合条件的文件
    '''
    FileLst = []
    try:
        lst = os.walk(path)
        for root, dirs, files in lst:
            for name in files:
                try:
                    m = re.match(reg, name)
                except Exception as e:
                    print str(e)
                    continue
                if m:
                    nameClass = pb_name.nameClassManager()
                    info = nameClass.getInstance(name)
                    if info == None:
                        continue
                    if info.dt_s.strftime('%Y%m%d') != ymd:
                        continue
                    FileLst.append(os.path.join(root, name))
    except Exception as e:
        print str(e)

    return sorted(FileLst)

if __name__ == '__main__':

    main()
