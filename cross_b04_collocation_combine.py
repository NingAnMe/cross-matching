# coding=UTF-8
__author__ = 'wangpeng'

import os
import sys
import re
import h5py
import numpy as np
from configobj import ConfigObj
from dateutil.relativedelta import relativedelta
from PB import pb_time
from PB.CSC.pb_csc_console import LogServer
from datetime import datetime


def run(pair, ymd):
    # 解析配置文件
    Log.info(u'[%s] [%s]' % (pair, ymd))
    # 解析配置文件
    shortsat1 = (pair.split('_')[0]).split('+')[0]
    sensor1 = (pair.split('_')[0]).split('+')[1]
    shortsat2 = (pair.split('_')[1]).split('+')[0]
    sensor2 = (pair.split('_')[1]).split('+')[1]
    # 输入 输出
    ipath = os.path.join(MATCH_DIR, pair, ymd[:6])
    outName = 'COLLOC+LEOLEOIR,%s+%s_%s+%s_C_BABJ_%s.hdf5' % (
        shortsat1, sensor1, shortsat2, sensor2, ymd)
    opath = os.path.join(MATCH_DIR, pair, outName)

    # 获取输入文件列表
    pat = '[_,\-\+\w]+_%s\d{6}.hdf5' % ymd
    FileLst = FindFile(ipath, pat)
    if len(FileLst) > 0:
        h5File_W = h5py.File(opath, 'w')
        for iFile in FileLst:
            try:
                h5File_R = h5py.File(iFile, 'r')
                combineHDF5(h5File_R, h5File_W)
                h5File_R.close()
            except Exception as e:
                print str(e)
        h5File_W.close()


def combineHDF5(pre_object, out_object):
    """
    combine daily hdf5 file from times hdf5 files（针对GSICS新版本时次的匹配结果代码掩码数据集）
    :pre_object (输入的hdf5文件流标识)
    :out_object (输出的hdf5文件流标识)
    :数据集合并 (多个时次的数据通过掩码降维，然后拼接输出)
    """

    # 01 记录根目录下的数据集名称和数据（不包含分组的数据信息）
    pre_rootgrp_geo = {}
    for key in pre_object.keys():
        pre_rootgrp = pre_object.get(key)  # 获取根下名字
        if type(pre_rootgrp).__name__ == "Group":
            pass
        else:
            #             print sys.getsizeof(pre_rootgrp.value)
            if 'MaskRough' in key:  # 剔除粗匹配查找表这个数据集
                continue
            elif 'Spec_MaskRough' in key:  # 剔除spec日合成会比较大
                continue
            else:
                pre_rootgrp_geo[key] = pre_rootgrp

    # 02 再次遍历根下的所有数据集，本次是遍历分组信息，并记录数据
    for key in pre_object.keys():
        pre_rootgrp = pre_object.get(key)
        if type(pre_rootgrp).__name__ == "Group":  # 判断名字是否属于组
            # 如果目标文件中没有这个组，则创建.
            if key not in out_object.keys():
                out_rootgrp = out_object.create_group(key)
            else:  # 如果存在，则读取
                out_rootgrp = out_object.get(key)

            # 03 把当前组里的数据和组外的定位数据集整合到一起
            for dkey in pre_rootgrp.keys() + pre_rootgrp_geo.keys():

                # 如果数据集在定位数据集中，则使用pre_rootgrp_geo取值
                if dkey in pre_rootgrp_geo.keys():
                    pre_dateset = pre_rootgrp_geo[dkey]
                else:  # 如果数据集在分组数据集中，则使用get获取
                    pre_dateset = pre_rootgrp.get(dkey)

                # 04 使用分组中的 MaskFine数据集对数据进行筛选
                MaskFine = pre_rootgrp.get('MaskFine')[:]
                idx = np.where(MaskFine > 0)
                data = pre_dateset.value[idx]

                # 05 如果数据集没有在这个分组中，则创建，注意第一维度采用可扩展维度
                if dkey not in out_rootgrp.keys():
                    out_dateset = out_rootgrp.create_dataset(dkey, (len(data), 1), dtype=pre_dateset.dtype, maxshape=(
                        None, 1), compression='gzip', compression_opts=5)
                    out_dateset[:] = data.reshape(len(data), 1)  # 给数据集赋值
                else:  # 如果数据集已经存在这个分组中，则读取。
                    out_dateset = out_rootgrp.get(dkey)
                    dim1 = out_dateset.value.shape[0]  # 取出第一维长度
                    out_dateset.resize(dim1 + len(data), axis=0)  # 长度重新计算
                    out_dateset[dim1:] = data.reshape(len(data), 1)

                # 复制dataset属性
                for akey in pre_dateset.attrs.keys():
                    out_dateset.attrs[akey] = pre_dateset.attrs[akey]

            # 复制group属性
            for akey in pre_object.attrs.keys():
                out_object.attrs[akey] = pre_object.attrs[akey]


def FindFile(ipath, pat):
    ncLst = []
    # 要查找当天文件的正则
    if not os.path.isdir(ipath):
        return ncLst
    Lst = sorted(os.listdir(ipath), reverse=False)
    for Line in Lst:
        FullPath = os.path.join(ipath, Line)
        if os.path.isdir(FullPath):
            continue
        # 如果是文件则进行正则判断，并把符合规则的所有文件保存到List中
        elif os.path.isfile(FullPath):
            FileName = Line
            m = re.match(pat, FileName)
            if m:
                ncLst.append(FullPath)
    if len(ncLst) == 0:
        Log.error('Not found  file')
        return ncLst
    else:
        Log.info('Found file')
        return ncLst


######################### 程序全局入口 ##############################

# 获取程序参数接口
args = sys.argv[1:]
help_info = \
    u'''
        【参数1】：FY3A+MERSI_AQUA+MODIS(样例，具体参见global.cfg 标签PAIRS下的标识)
        【参数2】：yyyymmdd-yyyymmdd
    '''
if '-h' in args:
    print help_info
    sys.exit(-1)

# 获取程序所在位置，拼接配置文件
MainPath, MainFile = os.path.split(os.path.realpath(__file__))
cfgFile = os.path.join(MainPath, 'cfg', 'global.cfg')

# 配置不存在预警
if not os.path.isfile(cfgFile):
    print (u'配置文件不存在 %s' % cfgFile)
    sys.exit(-1)
# 载入配置文件
inCfg = ConfigObj(cfgFile)
PARAM_DIR = inCfg['PATH']['PARAM']
MATCH_DIR = inCfg['PATH']['MID']['MATCH_DATA']
LogPath = inCfg['PATH']['OUT']['LOG']
Log = LogServer(LogPath)


if len(args) == 2:
    Log.info(u'手动日合成程序开始运行-----------------------------')
    satPair = args[0]
    str_time = args[1]
    date_s, date_e = pb_time.arg_str2date(str_time)

    while date_s <= date_e:
        ymd = date_s.strftime('%Y%m%d')
        run(satPair, ymd)
        date_s = date_s + relativedelta(days=1)

else:
    print 'args: FY3A+MERSI_AQUA+MODIS yyyymmdd-yyyymmdd '
    sys.exit(-1)
