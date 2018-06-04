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
from configobj import ConfigObj
from dateutil.relativedelta import relativedelta

from matplotlib.path import Path
import matplotlib.patches as patches
import matplotlib as mpl
from matplotlib import cm

# 引用自编库
from DV import dv_map, dv_plt
from PB import pb_space, pb_io, pb_time
from PB.CSC.pb_csc_console import LogServer


# 获取程序所在位置，拼接配置文件
MainPath, MainFile = os.path.split(os.path.realpath(__file__))
cfgFile = os.path.join(MainPath, 'cfg', 'global.cfg')

# 配置不存在预警
if not os.path.isfile(cfgFile):
    print (u'配置文件不存在 %s' % cfgFile)
    sys.exit(-1)
# 载入配置文件
inCfg = ConfigObj(cfgFile)
MATCH_DIR = inCfg['PATH']['MID']['MATCH_DATA']
LogPath = inCfg['PATH']['OUT']['LOG']
Log = LogServer(LogPath)


# 经纬度方向list封装
codes = [Path.MOVETO,
         Path.LINETO,
         Path.CLOSEPOLY,
         ]
TmpLst = [Path.LINETO] * 35
codes[1:-1] = TmpLst

BandLst = ['CH_21', 'CH_22', 'CH_24', 'CH_25']


def run(satPair, ymd):
    # 解析配置文件
    shortsat1 = (satPair.split('_')[0]).split('+')[0]
    sensor1 = (satPair.split('_')[0]).split('+')[1]
    shortsat2 = (satPair.split('_')[1]).split('+')[0]
    sensor2 = (satPair.split('_')[1]).split('+')[1]

    #ipath = os.path.join(MATCH_DIR, satPair, ymd[:6])
    ipath = os.path.join(MATCH_DIR, satPair, ymd[:4], ymd)

    # 获取输入文件列表
    pat = '[_,\-\+\w]+_%s\d{6}.hdf5' % ymd
    FileLst = pb_io.FindFile(ipath, pat)
    dictLon1 = {}
    dictLat1 = {}
    dictTbb1 = {}
    dictLon2 = {}
    dictLat2 = {}
    dictTbb2 = {}

    i = 0
    if FileLst != []:
        for iFile in FileLst:
            try:
                h5File_R = h5py.File(iFile, 'r')
                obritType = h5File_R.attrs.get('obrit Direction1')[0]
                Lon1 = h5File_R.get('S1_Lon')[:]
                Lat1 = h5File_R.get('S1_Lat')[:]
                Lon2 = h5File_R.get('S2_Lon')[:]
                Lat2 = h5File_R.get('S2_Lat')[:]

                if len(obritType) == 0:
                    print iFile
                    continue

                if obritType not in dictLon1.keys():
                    dictLon1[obritType] = Lon1
                    dictLat1[obritType] = Lat1
                    dictLon2[obritType] = Lon2
                    dictLat2[obritType] = Lat2
                    dictTbb1[obritType] = {}
                    dictTbb2[obritType] = {}
                    for band in BandLst:
                        tbb1 = h5File_R.get('/%s/S1_FovTbbMean' % band)[:]
                        tbb2 = h5File_R.get('/%s/S2_FovTbbMean' % band)[:]
                        if band not in dictTbb1[obritType].keys():
                            dictTbb1[obritType][band] = tbb1
                            dictTbb2[obritType][band] = tbb2
                else:
                    dictLon1[obritType] = np.concatenate(
                        (dictLon1[obritType], Lon1))
                    dictLat1[obritType] = np.concatenate(
                        (dictLat1[obritType], Lat1))
                    dictLon2[obritType] = np.concatenate(
                        (dictLon2[obritType], Lon2))
                    dictLat2[obritType] = np.concatenate(
                        (dictLat2[obritType], Lat2))
                    for band in BandLst:
                        tbb1 = h5File_R.get('/%s/S1_FovTbbMean' % band)[:]
                        tbb2 = h5File_R.get('/%s/S2_FovTbbMean' % band)[:]
                        dictTbb1[obritType][band] = np.concatenate(
                            (dictTbb1[obritType][band], tbb1))
                        dictTbb2[obritType][band] = np.concatenate(
                            (dictTbb2[obritType][band], tbb2))

                h5File_R.close()

            except Exception as e:
                print str(e)

        # 按照升降轨道 和 不同通道分别出图，暂时出tbb即可
        for adType in dictLat1.keys():
            for band in dictTbb1[adType].keys():
                print adType, band
                Tbb1 = dictTbb1[adType][band]
                Tbb2 = dictTbb2[adType][band]
                Tbb1 = np.ma.masked_where(Tbb1 <= 0, Tbb1)
                Tbb2 = np.ma.masked_where(Tbb1 <= 0, Tbb2)
                outName = '%s+%s_GBAL_MAP_%s_%s_%s.png' % (
                    shortsat1, sensor1, adType, ymd, band)
                #opath = os.path.join(MATCH_DIR, satPair, outName)
                opath = os.path.join(MATCH_DIR, satPair, ymd[:4], outName)
                p = dv_map.dv_map(figsize=(6, 5))
                p.title = '%s %s BT collocated with %s at %s %s (%s)' % (
                    shortsat1, sensor1, sensor2, band, ymd, adType)
                # p.colorbar_fmt = '%0.2f'
                vmin = 180
                vmax = 300
                p.delat = 30
                p.delon = 30
                p.easyplot(dictLat1[adType], dictLon1[
                           adType], Tbb1, vmin=vmin, vmax=vmax, markersize=1, marker='.')
                p.savefig(opath, dpi=300)

                outName = '%s+%s_GBAL_MAP_%s_%s_%s.png' % (
                    shortsat2, sensor2, adType, ymd, band)
                #opath = os.path.join(MATCH_DIR, satPair, outName)
                opath = os.path.join(MATCH_DIR, satPair, ymd[:4], outName)
                p = dv_map.dv_map(figsize=(6, 5))
                p.title = '%s %s BT convoluted at %s at %s %s (%s)' % (
                    shortsat2, sensor2, sensor1, band, ymd, adType)
                # p.colorbar_fmt = '%0.2f'
                vmin = 180
                vmax = 300
                p.delat = 30
                p.delon = 30
                p.easyplot(dictLat2[adType], dictLon2[
                           adType], Tbb2, vmin=vmin, vmax=vmax, markersize=1, marker='.')
                p.savefig(opath, dpi=300)

                outName = '%s+%s_%s+%s_GBAL_MAP_%s_%s_%s.png' % (
                    shortsat1, sensor1, shortsat2, sensor2, adType, ymd, band)
                #opath = os.path.join(MATCH_DIR, satPair, outName)
                opath = os.path.join(MATCH_DIR, satPair, ymd[:4], outName)
                p = dv_map.dv_map(figsize=(6, 5))
                p.title = '%s %s BT  at %s %s (%s)' % (
                    sensor1, sensor2, band, ymd, adType)
                # p.colorbar_fmt = '%0.2f'
                vmin = -2
                vmax = 2
                p.delat = 30
                p.delon = 30
                diffTbb = Tbb1 - Tbb2
                diffTbb = np.ma.masked_where(Tbb1 <= 0, diffTbb)
                p.easyplot(dictLat1[adType], dictLon1[
                           adType], diffTbb, vmin=vmin, vmax=vmax, markersize=1, marker='.')
                p.savefig(opath, dpi=300)

        # 绘制真实大小，速度比较慢
#         norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax, clip=False)
#         p.easyplot(None, None, None, vmin=vmin, vmax=vmax, markersize=5, marker='.')
#
#         # 测试画圆方式里面填充颜色
#         for i in xrange(aLon.shape[0]):
#             for j in xrange(aLon.shape[1]):
#                 x, y = p.m(aLon[i, j, 0, :], aLat[i, j, 0, :])
#                 verts = []
#                 for k in xrange(aLon.shape[3]):
#                     verts.append((x[k], y[k]))
#                 path = Path(verts, codes)
#                 rgba_color = cm.jet(norm(aTbb[i, j, 0]))
#                 ax_pathches = patches.PathPatch(path, facecolor=rgba_color, edgecolor='k', lw=0)
#                 p.ax.add_patch(ax_pathches)
#         p.colormap = "jet"
#         p.add_colorbar_right()
# #         p.easyplot(aLat, aLon, aTbb, vmin=vmin, vmax=vmax, markersize=0.5, marker='.')
#         p.savefig(opath, dpi=300)


if __name__ == '__main__':

    # 获取程序参数接口
    args = sys.argv[1:]

    if len(args) == 2:
        Log.info(u'手动精匹配分布图绘制程序开始运行-----------------------------')
        satPair = args[0]
        str_time = args[1]
        date_s, date_e = pb_time.arg_str2date(str_time)
        while date_s <= date_e:
            ymd = date_s.strftime('%Y%m%d')
            run(satPair, ymd)
            date_s = date_s + relativedelta(days=1)

    else:
        print(u'参数错误-----------------------------')
