# coding: utf-8
__author__ = 'wangpeng'

'''
FileName:     job_step_proj.py
Description:  订购卫星数据
Author:       wangpeng
Date:         2015-08-21
version:      1.0.0.050821_beat
Input:        args1:开始时间-结束时间  [YYYYMMDD-YYYYMMDD]
Output:       (^_^)
'''

import sys, os, yaml, h5py, re
from pyhdf.SD import SD, SDC
from DP.dp_prj_FY3C import prj_core, fill_points_2d
import numpy as np
from posixpath import join as urljoin
from DV import dv_img
from PB.DRC.pb_drc_MERSI2_L1 import CLASS_MERSI2_L1

class PROJ_COMM():

    def __init__(self, in_proj_cfg):
        '''
        读取yaml格式配置文件
        '''
        if not os.path.isfile(in_proj_cfg):
            print 'Not Found %s' % in_proj_cfg
            sys.exit(-1)

        with open(in_proj_cfg, 'r') as stream:
            cfg = yaml.load(stream)
        self.sat = cfg['INFO']['sat']
        self.sensor = cfg['INFO']['sensor']
        self.ymd = cfg['INFO']['ymd']

        self.ifile = cfg['PATH']['ipath']
        self.ofile = cfg['PATH']['opath']

        self.cmd = cfg['PROJ']['cmd']
        self.col = cfg['PROJ']['col']
        self.row = cfg['PROJ']['row']
        self.res = cfg['PROJ']['res']


    def proj_fy3d_mersi(self):

        print 'start project %s %s' % (self.sat, self.sensor)
        # 进行数组的初始化
        proj_data_ch = np.array([[[-999] * self.col] * self.row] * 25)
        proj_data_sv = np.array([[[-999.] * self.col] * self.row] * 25)
        proj_data_bb = np.array([[[-999.] * self.col] * self.row] * 25)
        proj_data_satz = np.array([[-999] * self.col] * self.row)
        proj_data_sata = np.array([[-999] * self.col] * self.row)
        proj_data_sunz = np.array([[-999] * self.col] * self.row)
        proj_data_suna = np.array([[-999] * self.col] * self.row)
        proj_LandCover = np.array([[-999] * self.col] * self.row)
        proj_LandSeaMask = np.array([[-999] * self.col] * self.row)
        proj_Cal_Coeff = np.array([[-999.] * 3] * 19)
        print proj_Cal_Coeff.shape

        # 初始化投影参数
#         lookup_table = prj_core(self.cmd, self.res, self.row, self.col)
        for L1File in self.ifile:
            mersi = CLASS_MERSI2_L1_1000M()
            mersi.Load(L1File)

            # 创建投影查找表
            lookup_table = prj_core(self.cmd, self.res, self.row, self.col)

            # 获取投影后网格经纬度信息
            lon_x, lat_y = lookup_table.ij2lonlat()
            # 经纬度转成投影后的数据维度
            proj_lon = lon_x.reshape([self.row, self.col])
            proj_lat = lat_y.reshape([self.row, self.col])
            # 获取源数据经纬度位置与投影后位置的对应关系，并转成与数据大小一致维度
            proj1_i, proj1_j = lookup_table.lonslats2ij(mersi.Lons, mersi.Lats)
            if len(proj1_i.shape) == 1:
                proj1_i = proj1_i.reshape(mersi.Lons.shape)
                proj1_j = proj1_j.reshape(mersi.Lons.shape)
            # 根据投影前数据别分获取源数据维度，制作一个和数据维度一致的数组，分别存放行号和列号
            data1_row, data1_col = mersi.Lons.shape
            data1_i, data1_j = np.mgrid[0:data1_row:1, 0:data1_col:1]


            # 投影方格以外的数据过滤掉，第一块数据原始数据的行列, data1_i, data1_j 第一块数据投影后的行列 proj1_i,proj1_j
            condition = np.logical_and(proj1_i >= 0, proj1_i < self.row)
            condition = np.logical_and(condition, proj1_j >= 0)
            condition = np.logical_and(condition, proj1_j < self.col)
            index = np.where(condition)
            p1_i = proj1_i[index]
            p1_j = proj1_j[index]
            d1_i = data1_i[index]
            d1_j = data1_j[index]

            # 1-4通道的投影
            i = 0
            for key in sorted(mersi.DN.keys()):
                index = np.where(~np.isnan(mersi.DN[key][d1_i, d1_j]))
                pi = p1_i[index]
                pj = p1_j[index]
                di = d1_i[index]
                dj = d1_j[index]
                proj_data_ch[i, pi, pj] = mersi.DN[key][di, dj]

                index = np.where(~np.isnan(mersi.SV[key][d1_i, d1_j]))
                pi = p1_i[index]
                pj = p1_j[index]
                di = d1_i[index]
                dj = d1_j[index]
                proj_data_sv[i, pi, pj] = mersi.SV[key][di, dj]

                index = np.where(~np.isnan(mersi.BB[key][d1_i, d1_j]))
                pi = p1_i[index]
                pj = p1_j[index]
                di = d1_i[index]
                dj = d1_j[index]
                proj_data_bb[i, pi, pj] = mersi.BB[key][di, dj]

                fill_points_2d(proj_data_ch[i], -999)
                fill_points_2d(proj_data_sv[i], -999.)
                fill_points_2d(proj_data_bb[i], -999.)
                fill_points_2d(proj_data_ch[i], -999)
                fill_points_2d(proj_data_sv[i], -999.)
                fill_points_2d(proj_data_bb[i], -999.)

                fill_points_2d(proj_data_ch[i], -999)
                fill_points_2d(proj_data_sv[i], -999.)
                fill_points_2d(proj_data_bb[i], -999.)

                i = i + 1

            # 卫星方位角 天顶角
            index = np.where(~np.isnan(mersi.satZenith[d1_i, d1_j]))
            pi = p1_i[index]
            pj = p1_j[index]
            di = d1_i[index]
            dj = d1_j[index]
            proj_data_satz[ pi, pj] = mersi.satZenith[di, dj] * 100

            index = np.where(~np.isnan(mersi.satAzimuth[d1_i, d1_j]))
            pi = p1_i[index]
            pj = p1_j[index]
            di = d1_i[index]
            dj = d1_j[index]
            proj_data_sata[pi, pj] = mersi.satAzimuth[di, dj] * 100

            # 卫星方位角 天顶角
            index = np.where(~np.isnan(mersi.sunAzimuth[d1_i, d1_j]))
            pi = p1_i[index]
            pj = p1_j[index]
            di = d1_i[index]
            dj = d1_j[index]
            proj_data_suna[pi, pj] = mersi.sunAzimuth[di, dj] * 100

            index = np.where(~np.isnan(mersi.sunZenith[d1_i, d1_j]))
            pi = p1_i[index]
            pj = p1_j[index]
            di = d1_i[index]
            dj = d1_j[index]
            proj_data_sunz[ pi, pj] = mersi.sunZenith[di, dj] * 100

            # 海陆掩码等
            index = np.where(~np.isnan(mersi.LandCover[d1_i, d1_j]))
            pi = p1_i[index]
            pj = p1_j[index]
            di = d1_i[index]
            dj = d1_j[index]
            proj_LandCover[ pi, pj] = mersi.LandCover[di, dj]

            index = np.where(~np.isnan(mersi.LandSeaMask[d1_i, d1_j]))
            pi = p1_i[index]
            pj = p1_j[index]
            di = d1_i[index]
            dj = d1_j[index]
            proj_LandSeaMask[ pi, pj] = mersi.LandSeaMask[di, dj]

            proj_Cal_Coeff = mersi.VIS_Coeff

        fill_points_2d(proj_data_satz, -999)
        fill_points_2d(proj_data_sata, -999)
        fill_points_2d(proj_data_sunz, -999)
        fill_points_2d(proj_data_suna, -999)
        fill_points_2d(proj_data_satz, -999)
        fill_points_2d(proj_data_sata, -999)
        fill_points_2d(proj_data_sunz, -999)
        fill_points_2d(proj_data_suna, -999)
        fill_points_2d(proj_data_satz, -999)
        fill_points_2d(proj_data_sata, -999)
        fill_points_2d(proj_data_sunz, -999)
        fill_points_2d(proj_data_suna, -999)

        # 写入HDF
        opath = os.path.dirname(self.ofile)
        if not os.path.isdir(opath):
            os.makedirs(opath)

        pic_name = self.ofile.split('.hdf')[0] + '_321.png'
        picFile = urljoin(opath, pic_name)
        dv_img.dv_rgb(proj_data_ch[2], proj_data_ch[1], proj_data_ch[0], picFile, 2, 1)

        pic_name2 = self.ofile.split('.hdf')[0] + '_643.png'
        picFile = urljoin(opath, pic_name2)
        dv_img.dv_rgb(proj_data_ch[5], proj_data_ch[3], proj_data_ch[2], picFile, 2, 1)

        h5file_W = h5py.File(self.ofile, 'w')
        h5file_W.create_dataset('L1B_DN_values', dtype='i2', data=proj_data_ch, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('RefSBCoeffcients', dtype='f4', data=proj_Cal_Coeff, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SensorZenith', dtype='i4', data=proj_data_satz, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SensorAzimuth', dtype='i4', data=proj_data_sata, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SolarZenith', dtype='i4', data=proj_data_sunz, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SolarAzimuth', dtype='i4', data=proj_data_suna, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('LandSeaMask', dtype='i2', data=proj_LandSeaMask, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('LandCover', dtype='i2', data=proj_LandCover, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('Longitude', dtype='f4', data=proj_lon, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('Latitude', dtype='f4', data=proj_lat, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SV_DN_average', dtype='f4', data=proj_data_sv, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('BB_DN_average', dtype='f4', data=proj_data_bb, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.close()

def main(args):
    if len(args) == 1:  # 跟参数，则处理输入的时段数据
        in_proj_cfg = args[0]
    else:
        in_proj_cfg = None

    if in_proj_cfg == None:
        print 'input args error exit'
        sys.exit(-1)
    # 初始化投影公共类
    proj = PROJ_COMM(in_proj_cfg)
    if os.path.isfile(proj.ofile):
        print 'file exist :%s' % proj.ofile
        return
    # 根据卫星传感器调用不同的投影函数
    if proj.sensor == 'MERSI2':
        proj.proj_fy3d_mersi()
    else:
        print "not support %s %s" % (proj.sat, proj.sensor)
        sys.exit(-2)

if __name__ == '__main__':
    # 获取python输入参数，进行处理
    args = sys.argv[1:]
    main(args)
