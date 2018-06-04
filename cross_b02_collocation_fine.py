# coding: utf-8
__author__ = 'wangpeng'

'''
Description:  精匹配调度  适用于高光谱和成像仪
Author:       wangpeng
Date:         2018-04-18
version:      1.0
'''

# 引用系统库
import numpy as np
import sys
import os
import glob
import h5py
import yaml
from datetime import datetime

# 引用自编库
from DP.dp_collcation_fine import *
from DP.dp_nearest2 import dp_nearest
from DV import dv_map, dv_plt
from PB.DRC.pb_drc_MERSI2_L1 import CLASS_MERSI2_L1
from PB.DRC.pb_drc_HIRAS_L1 import CLASS_HIRAS_L1
from PB.DRC.pb_drc_VIIRS_L1 import CLASS_VIIRS_L1
from PB.DRC.pb_drc_CRIS_L1 import CLASS_CRIS_L1
from PB import pb_space

# 文件默认编码修改位utf-8
reload(sys)
sys.setdefaultencoding('utf-8')
# 配置文件信息，设置为全局
MainPath, MainFile = os.path.split(os.path.realpath(__file__))


class ReadYaml():

    def __init__(self, inFile):
        """
        读取yaml格式配置文件
        """
        if not os.path.isfile(inFile):
            print 'Not Found %s' % inFile
            sys.exit(-1)

        with open(inFile, 'r') as stream:
            cfg = yaml.load(stream)
        self.sat1 = cfg['INFO']['sat1']
        self.sensor1 = cfg['INFO']['sensor1']
        self.sat2 = cfg['INFO']['sat2']
        self.sensor2 = cfg['INFO']['sensor2']
        self.ymd = cfg['INFO']['ymd']

        self.ifile1 = cfg['PATH']['ipath1']
        self.ifile2 = cfg['PATH']['ipath2']
        self.ofile = cfg['PATH']['opath']


def main(inYamlFile):

    ##########01 ICFG = 输入配置文件类 ##########
    ICFG = ReadYaml(inYamlFile)

    # 02 MCFG = 阈值配置文件类
    modeFile = os.path.join(
        MainPath, 'cfg', 'COLLOC_%s_%s.yaml' % (ICFG.sensor1, ICFG.sensor2))
    MCFG = ReadModeYaml(modeFile)

    # setup parameters
    Fov_fov = np.cos(np.deg2rad(MCFG.S2_Fov_fov / 2.0))
    Env_fov = np.cos(np.deg2rad(MCFG.S2_Env_fov / 2.0))

    # 中心点矩阵范围,注释掉，算好了可以写在配置文件中
    FovWind1 = np.round(np.deg2rad(MCFG.S2_Fov_fov / 2.0) *
                        MCFG.S1_satHeight / MCFG.S1_resolution * 4).astype(np.int)
    EnvWind1 = np.round(np.deg2rad(MCFG.S2_Env_fov / 2.0) *
                        MCFG.S1_satHeight / MCFG.S1_resolution * 4).astype(np.int)
    print Fov_fov, Env_fov, FovWind1, EnvWind1

    # 判断是否重写
    if os.path.isfile(ICFG.ofile):
        rewrite_mask = True
    else:
        rewrite_mask = False

    COLLOC = COLLOC_COMM(MCFG.row, MCFG.col, MCFG.chan1)

    if not rewrite_mask:
        T1 = datetime.now()
        ##########03 解析 第一颗传感器的L1数据 ##########
        if 'MERSI2' == ICFG.sensor1:  # D1 成像仪数据解析 2000*2048
            D1 = CLASS_MERSI2_L1()
            for inFile1 in ICFG.ifile1:
                D1.Load(inFile1)
                D1.get_G_P_L()

        elif 'VIIRS' == ICFG.sensor1:
            D1 = CLASS_VIIRS_L1()
            for inFile1 in ICFG.ifile1:
                D1.Load(inFile1)
                D1.get_G_P_L()

        # D2 高光谱数据解析 ggp数据全部变量由(30*29*4 = 3480)转成了 3480*1
        if 'HIRAS' == ICFG.sensor2:
            for inFile2 in ICFG.ifile2:
                D2 = CLASS_HIRAS_L1(MCFG.chan1)
                D2.Load(inFile2)
                D2.get_G_P_L()
                D2.get_rad_tbb(D1, MCFG.chan1)

        elif 'CRIS' == ICFG.sensor2:
            for inFile2 in ICFG.ifile2:
                D2 = CLASS_CRIS_L1(MCFG.chan1)
                D2.Load(inFile2)
                D2.get_G_P_L()
                D2.get_rad_tbb(D1, MCFG.chan1)

        T2 = datetime.now()
        print '读取数据耗时 :', (T2 - T1).total_seconds()

        T1 = datetime.now()
#         P_pos2 = D2.hiras_pos
        # 朝找最近匹配点，返回查找表和G矢量
        P1 = dp_nearest()
        P1.FindNearest(
            D1.G_pos, D2.G_pos, D2.P_pos, D2.L_pos, Fov_fov, MCFG.FovWind1)
        P2 = dp_nearest()
        P2.FindNearest(
            D1.G_pos, D2.G_pos, D2.P_pos, D2.L_pos, Env_fov, MCFG.EnvWind1)
        T2 = datetime.now()
        print 'kdtree 空间匹配耗时 :', (T2 - T1).total_seconds()
        ########## 值计算 ##########
        T1 = datetime.now()
        COLLOC.save_rough_data(P1, P2, D1, D2, MCFG)
        T2 = datetime.now()
        print '均值和std计算耗时 :', (T2 - T1).total_seconds()

    else:
        T1 = datetime.now()
        COLLOC.reload_data(ICFG, MCFG)
        T2 = datetime.now()
        print '数据存在 重新读取耗时:', (T2 - T1).total_seconds()

    T1 = datetime.now()
    COLLOC.save_fine_data(MCFG)
    COLLOC.correct_target_ref_data()
    T2 = datetime.now()
    print 'colloc:', (T2 - T1).total_seconds()

    ##########09 输出匹配结果 ##########
    if rewrite_mask:
        T1 = datetime.now()
        COLLOC.rewrite_hdf5(ICFG, MCFG)
        T2 = datetime.now()
        print 'rewrite:', (T2 - T1).total_seconds()
    elif MCFG.rewrite:
        T1 = datetime.now()
        COLLOC.write_hdf5(ICFG, MCFG)
        T2 = datetime.now()
        print 'write:', (T2 - T1).total_seconds()

    ##########10 对结果进行绘图 ##########
    if MCFG.drawmap:
        T1 = datetime.now()
        COLLOC.draw_dclc(ICFG, MCFG)
        T2 = datetime.now()
        print 'map:', (T2 - T1).total_seconds()


if __name__ == '__main__':

    # 获取python输入参数，进行处理
    args = sys.argv[1:]
    if len(args) == 1:  # 跟参数，则处理输入的时段数据
        inYamlFile = args[0]
    else:
        print 'input args error exit'
        sys.exit(-1)

    # 统计整体运行时间
    T_all_1 = datetime.now()
    main(inYamlFile)
    T_all_2 = datetime.now()
    print 'all times:', (T_all_2 - T_all_1).total_seconds()
