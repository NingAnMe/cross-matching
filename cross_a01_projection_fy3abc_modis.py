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


    def proj_fy3abc_mersi(self):

        print 'start project %s %s' % (self.sat, self.sensor)
        # 进行数组的初始化
        proj_data_ch20 = np.array([[[-999] * self.col] * self.row] * 20)
        proj_data_sv20 = np.array([[[-999.] * self.col] * self.row] * 20)
        proj_data_bb20 = np.array([[[-999.] * self.col] * self.row] * 20)
        proj_data_satz = np.array([[-999] * self.col] * self.row)
        proj_data_sata = np.array([[-999] * self.col] * self.row)
        proj_data_sunz = np.array([[-999] * self.col] * self.row)
        proj_data_suna = np.array([[-999] * self.col] * self.row)
        proj_LandCover = np.array([[-999] * self.col] * self.row)
        proj_LandSeaMask = np.array([[-999] * self.col] * self.row)
        proj_Cal_Coeff = np.array([[-999.] * 3] * 19)

        # 初始化投影参数
        lookup_table = prj_core(self.cmd, self.res, self.row, self.col)
        for L1File in self.ifile:
            if self.sat == 'FY3C':
                # 根据输入的L1文件查找GEO文件
                ipath = os.path.dirname(L1File)
                iname = os.path.basename(L1File)
                geoFile = urljoin(ipath, iname[0:-12] + 'GEO1K_MS.HDF')
                # 读取L1文件
                try:
                    h5File = h5py.File(L1File, 'r')
                    in_data_ch1 = h5File.get('/Data/EV_250_Aggr.1KM_RefSB')[:]
                    in_data_ch5 = h5File.get('/Data/EV_250_Aggr.1KM_Emissive')[:]
                    in_data_ch6 = h5File.get('/Data/EV_1KM_RefSB')[:]
                    in_data_svdn = h5File.get('/Calibration/SV_DN_average')[:]
                    in_data_bbdn = h5File.get('/Calibration/BB_DN_average')[:]
                    in_data_Cal_Coeff = h5File.get('/Calibration/VIS_Cal_Coeff')[:]
                    h5File.close()
                except Exception as e:
                    print str(e)

                try:
                    # 读取GEO文件
                    h5File = h5py.File(geoFile, 'r')
                    in_data_satz = h5File.get('/Geolocation/SensorZenith')[:]
                    in_data_sata = h5File.get('/Geolocation/SensorAzimuth')[:]
                    in_data_sunz = h5File.get('/Geolocation/SolarZenith')[:]
                    in_data_suna = h5File.get('/Geolocation/SolarAzimuth')[:]
                    in_data_LandCover = h5File.get('/Geolocation/LandCover')[:]
                    in_data_LandSeaMask = h5File.get('/Geolocation/LandSeaMask')[:]
                    in_data_lon = h5File.get('/Geolocation/Longitude')[:]
                    in_data_lat = h5File.get('/Geolocation/Latitude')[:]
                    h5File.close()
                except Exception as e:
                    print str(e)

            else:
                # 读取L1文件
                h5File = h5py.File(L1File, 'r')
                try:
                    in_data_lon = h5File.get('/Longitude')[:]
                    in_data_lat = h5File.get('/Latitude')[:]
                    in_data_ch1 = h5File.get('/EV_250_Aggr.1KM_RefSB')[:]
                    in_data_ch5 = h5File.get('/EV_250_Aggr.1KM_Emissive')[:]
                    in_data_ch6 = h5File.get('/EV_1KM_RefSB')[:]
                    in_data_Cal_Coeff = h5File.attrs['VIR_Cal_Coeff']

                    in_data_satz = h5File.get('/SensorZenith')[:]
                    in_data_sata = h5File.get('/SensorAzimuth')[:]
                    in_data_sunz = h5File.get('/SolarZenith')[:]
                    in_data_suna = h5File.get('/SolarAzimuth')[:]
                    in_data_LandCover = h5File.get('/LandCover')[:]
                    in_data_LandSeaMask = h5File.get('/LandSeaMask')[:]

                except Exception as e:
                    print str(e)
                    return
                try:
                    in_data_svdn = h5File.get('/SV_DN_average')[:]
                    in_data_bbdn = h5File.get('/BB_DN_average')[:]

                except Exception as e:
                    print str(e)
                    in_data_svdn = np.full_like(in_data_lon, 0)
                    in_data_bbdn = np.full_like(in_data_lon, 0)
                h5File.close()

            # 获取经度数据集的行和列，制作一个一维的数组长度是 数据集行x列，分别存放行号和列号
            rowh5, colh5 = in_data_lon.shape
            ih5 = np.array([range(rowh5)] * colh5).T.reshape((-1))  # hdf5的行1d序列
            jh5 = np.array([range(colh5)] * rowh5).reshape((-1))  # hdf5的列1d序列
            # 返回投影查找表
            ii, jj = lookup_table.lonslats2ij(in_data_lon, in_data_lat)

            # 投影方格以外的数据过滤掉
            condition = np.logical_and(ii >= 0, ii < self.row)
            condition = np.logical_and(condition, jj >= 0)
            condition = np.logical_and(condition, jj < self.col)
            index = np.where(condition)
            ii = ii[index]
            jj = jj[index]
            ih5 = ih5[index]
            jh5 = jh5[index]

            # 1-4通道的投影
            for i in range(4):
                # 过滤 无效值
                condition = np.logical_and(in_data_ch1[i , ih5, jh5] < 10000, in_data_ch1[i , ih5, jh5] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_ch20[i, tii, tjj] = in_data_ch1[i, tih5, tjh5]

            # 5 通道投影
            condition = np.logical_and(in_data_ch5[ ih5, jh5] < 4095, in_data_ch5[ ih5, jh5] > 0)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_data_ch20[4, tii, tjj] = in_data_ch5[tih5, tjh5]

            # 6-20通道投影
            for i in range(15):
                condition = np.logical_and(in_data_ch6[i , ih5, jh5] < 10000, in_data_ch6[i , ih5, jh5] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_ch20[i + 5, tii, tjj] = in_data_ch6[i, tih5, tjh5]

            for i in range(20):
                # SV 进行过滤无效值投影
                condition = np.logical_and(in_data_svdn[ i, ih5 / 10] < 4095, in_data_svdn[ i, ih5 / 10] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_sv20[i, tii , tjj] = in_data_svdn[i, tih5 / 10]
                # BB 进行过滤无效值投影
                condition = np.logical_and(in_data_bbdn[ i, ih5 / 10] < 4095, in_data_bbdn[ i, ih5 / 10] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_bb20[i, tii , tjj] = in_data_bbdn[i, tih5 / 10]

            # 卫星天顶角
            condition = np.logical_and(in_data_satz[ih5, jh5] < 18000, in_data_satz[ih5, jh5] > 0)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_data_satz[tii, tjj] = in_data_satz[tih5, tjh5]

            # 卫星方位角
            condition = np.logical_and(in_data_sata[ih5, jh5] < 18000, in_data_sata[ih5, jh5] > -18000)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_data_sata[tii, tjj] = in_data_sata[tih5, tjh5]

            # 太阳天顶角
            condition = np.logical_and(in_data_sunz[ih5, jh5] < 18000, in_data_sunz[ih5, jh5] > 0)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_data_sunz[tii, tjj] = in_data_sunz[tih5, tjh5]

            # 太阳方位角
            condition = np.logical_and(in_data_suna[ih5, jh5] < 18000, in_data_suna[ih5, jh5] > -18000)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_data_suna[tii, tjj] = in_data_suna[tih5, tjh5]

            # land cover
            condition = np.logical_and(in_data_LandCover[ih5, jh5] < 17, in_data_LandCover[ih5, jh5] > 0)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_LandCover[tii, tjj] = in_data_LandCover[tih5, tjh5]

            # land sea mask
            condition = np.logical_and(in_data_LandSeaMask[ih5, jh5] < 7, in_data_LandSeaMask[ih5, jh5] > 0)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_LandSeaMask[tii, tjj] = in_data_LandSeaMask[tih5, tjh5]


        # RefSB_Cal_Coefficients这个属性直接写到hdf中，不进行操作，只是把14转成7*2
        if self.sat == 'FY3C':
            proj_Cal_Coeff = in_data_Cal_Coeff
        else:
            for i in range(19):
                for j in range(3):
                    proj_Cal_Coeff[i, j] = in_data_Cal_Coeff[i * 3 + j]

        # 通过行列号计算经纬度
        lon_x, lat_y = lookup_table.ij2lonlat()
        proj_lon = lon_x.reshape([self.row, self.col])
        proj_lat = lat_y.reshape([self.row, self.col])

        # 投影后进行补点操作
        for i in range(20):
            fill_points_2d(proj_data_sv20[i], -999)
            fill_points_2d(proj_data_bb20[i], -999.)
            fill_points_2d(proj_data_ch20[i], -999.)

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
        dv_img.dv_rgb(proj_data_ch20[2], proj_data_ch20[1], proj_data_ch20[0], picFile, 2, 1)

        pic_name2 = self.ofile.split('.hdf')[0] + '_643.png'
        picFile = urljoin(opath, pic_name2)
        dv_img.dv_rgb(proj_data_ch20[5], proj_data_ch20[3], proj_data_ch20[2], picFile, 3, 1)

        h5file_W = h5py.File(self.ofile, 'w')
        h5file_W.create_dataset('20bands_L1B_DN_values', dtype='i2', data=proj_data_ch20, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('RefSBCoeffcients', dtype='f4', data=proj_Cal_Coeff, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SensorZenith', dtype='i2', data=proj_data_satz, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SensorAzimuth', dtype='i2', data=proj_data_sata, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SolarZenith', dtype='i2', data=proj_data_sunz, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SolarAzimuth', dtype='i2', data=proj_data_suna, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('LandSeaMask', dtype='i2', data=proj_LandSeaMask, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('LandCover', dtype='i2', data=proj_LandCover, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('Longitude', dtype='f4', data=proj_lon, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('Latitude', dtype='f4', data=proj_lat, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SV_DN_average', dtype='f4', data=proj_data_sv20, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('BB_DN_average', dtype='f4', data=proj_data_bb20, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.close()

    def proj_fy3abc_virr(self):
        # 进行数组的初始化
        proj_data_ch10 = np.array([[[-999] * self.col] * self.row] * 10)
        proj_data_sv10 = np.array([[[-999] * self.col] * self.row] * 10)
        proj_data_rad = np.array([[[-999.] * self.col] * self.row] * 3)
        proj_Cal_Coeff = np.array([[-999.] * 2] * 7)
        proj_data_satz = np.array([[-999] * self.col] * self.row)
        proj_data_sata = np.array([[-999] * self.col] * self.row)
        proj_data_sunz = np.array([[-999] * self.col] * self.row)
        proj_data_suna = np.array([[-999] * self.col] * self.row)
        proj_LandCover = np.array([[-999] * self.col] * self.row)
        proj_LandSeaMask = np.array([[-999] * self.col] * self.row)
#         proj_src_row = np.array([[-999] * self.col] * self.row)
#         proj_src_col = np.array([[-999] * self.col] * self.row)

        # 初始化投影参数
        lookup_table = prj_core(self.cmd, self.res, self.row, self.col)
        for L1File in self.ifile:
            if self.sat == 'FY3C':
                # 根据输入的L1文件自动拼接GEO文件
                ipath = os.path.dirname(L1File)
                iname = os.path.basename(L1File)
                geoFile = urljoin(ipath, iname[0:-12] + 'GEOXX_MS.HDF')
                obcFile = urljoin(ipath, iname[0:-12] + 'OBCXX_MS.HDF')

                # 读取L1文件
                try:
                    h5File = h5py.File(L1File, 'r')
                    in_data_ch3 = h5File.get('/Data/EV_Emissive')[:]
                    in_data_ch7 = h5File.get('/Data/EV_RefSB')[:]
                    in_data_offsets = h5File.get('/Data/Emissive_Radiance_Offsets')[:]
                    in_data_scales = h5File.get('/Data/Emissive_Radiance_Scales')[:]
                    in_data_ref_cal = h5File.attrs['RefSB_Cal_Coefficients']
                    in_data_Nonlinear = h5File.attrs['Prelaunch_Nonlinear_Coefficients']
                    h5File.close()
                except Exception as e:
                    print str(e)

                try:
                    # 读取GEO文件
                    h5File = h5py.File(geoFile, 'r')
                    in_data_satz = h5File.get('/Geolocation/SensorZenith')[:]
                    in_data_sata = h5File.get('/Geolocation/SensorAzimuth')[:]
                    in_data_sunz = h5File.get('/Geolocation/SolarZenith')[:]
                    in_data_suna = h5File.get('/Geolocation/SolarAzimuth')[:]
                    in_data_lon = h5File.get('/Geolocation/Longitude')[:]
                    in_data_lat = h5File.get('/Geolocation/Latitude')[:]
                    in_data_LandCover = h5File.get('/Geolocation/LandCover')[:]
                    in_data_LandSeaMask = h5File.get('/Geolocation/LandSeaMask')[:]
                    h5File.close()
                except Exception as e:
                    print str(e)
                try:
                    # 读取OBC文件
                    h5File = h5py.File(obcFile, 'r')
                    in_data_sv = h5File.get('/Calibration/Space_View')[:]
                    h5File.close()
                except Exception as e:
                    print str(e)

            else:  # FY3A FY3B
                # 根据输入的L1文件自动拼接OBC文件
                ipath = os.path.dirname(L1File)
                iname = os.path.basename(L1File)
                obcFile = urljoin(ipath, iname[0:-12] + 'OBCXX_MS.HDF')

                # 读取L1文件
                h5File = h5py.File(L1File, 'r')
                in_data_ch3 = h5File.get('/EV_Emissive')[:]
                in_data_ch7 = h5File.get('/EV_RefSB')[:]
                in_data_offsets = h5File.get('/Emissive_Radiance_Offsets')[:]
                in_data_scales = h5File.get('/Emissive_Radiance_Scales')[:]
                in_data_ref_cal = h5File.attrs['RefSB_Cal_Coefficients']
                in_data_Nonlinear = h5File.attrs['Prelaunch_Nonlinear_Coefficients']
                in_data_satz = h5File.get('/SensorZenith')[:]
                in_data_sata = h5File.get('/SensorAzimuth')[:]
                in_data_sunz = h5File.get('/SolarZenith')[:]
                in_data_suna = h5File.get('/SolarAzimuth')[:]
                in_data_lon = h5File.get('/Longitude')[:]
                in_data_lat = h5File.get('/Latitude')[:]
                in_data_LandCover = h5File.get('/LandCover')[:]
                in_data_LandSeaMask = h5File.get('/LandSeaMask')[:]
                h5File.close()
                # 读取OBC文件
                h5File = h5py.File(obcFile, 'r')
                in_data_sv = h5File.get('Space_View')[:]
                h5File.close()

            # 获取经度数据集的行和列，制作一个一维的数组长度是 数据集行x列，分别存放行号和列号
            rowh5, colh5 = in_data_lon.shape
            ih5 = np.array([range(rowh5)] * colh5).T.reshape((-1))  # hdf5的行1d序列
            jh5 = np.array([range(colh5)] * rowh5).reshape((-1))  # hdf5的列1d序列
            # 返回投影查找表
#             ii, jj, ih5, jh5 = lookup_table.lonslats2ij(in_data_lon, in_data_lat, ih5, jh5)
            ii, jj = lookup_table.lonslats2ij(in_data_lon, in_data_lat)
            # 投影方格以外的数据过滤掉
            condition = np.logical_and(ii >= 0, ii < self.row)
            condition = np.logical_and(condition, jj >= 0)
            condition = np.logical_and(condition, jj < self.col)
            index = np.where(condition)

            ii = ii[index]
            jj = jj[index]
            ih5 = ih5[index]
            jh5 = jh5[index]

            # 通道信息进行投影  1-2通道
            for i in range(0, 2, 1):
                # 过滤EV_RefSB的无效值
                condition = np.logical_and(in_data_ch7[i, ih5, jh5] < 32767, in_data_ch7[i, ih5, jh5] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_ch10[i, tii, tjj] = in_data_ch7[i, tih5, tjh5]
            # 通道信息进行投影  3-5通道
            for i in range(2, 5, 1):
                # 过滤 EV_Emissive的无效值
                condition = np.logical_and(in_data_ch3[i - 2, ih5, jh5] < 32767, in_data_ch3[i - 2, ih5, jh5] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                # 把3-5通道用EV_Emissive来进行赋值
                proj_data_ch10[i, tii, tjj] = in_data_ch3[i - 2, tih5, tjh5]

                # 用定标系数修正EV_Emissive的值
                proj_data_rad[i - 2, tii, tjj] = in_data_ch3[i - 2, tih5, tjh5] * in_data_scales[tih5, i - 2] + in_data_offsets[tih5, i - 2]
                k0 = in_data_Nonlinear[3 * (i - 2)]
                k1 = in_data_Nonlinear[3 * (i - 2) + 1] + 1
                k2 = in_data_Nonlinear[3 * (i - 2) + 2]
                proj_data_rad[i - 2, tii, tjj] = proj_data_rad[i - 2, tii, tjj] ** 2 * k2 + proj_data_rad[i - 2, tii, tjj] * k1 + k0
            # 通道信息进行投影  6-10通道
            for i in range(5, 10, 1):
                condition = np.logical_and(in_data_ch7[i - 3, ih5, jh5] < 32767, in_data_ch7[i - 3, ih5, jh5] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_ch10[i, tii, tjj] = in_data_ch7[i - 3, tih5, tjh5]

            # SV 投影
            for i in range(0, 10, 1):
                condition = np.logical_and(in_data_sv[i, ih5, 0] < 1023, in_data_sv[i , ih5, 0] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_sv10[i, tii , tjj] = in_data_sv[i, tih5, 0]

            # 卫星天顶角
            condition = np.logical_and(in_data_satz[ih5, jh5] < 18000, in_data_satz[ih5, jh5] > 0)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_data_satz[tii, tjj] = in_data_satz[tih5, tjh5]

            # 卫星方位角
            condition = np.logical_and(in_data_sata[ih5, jh5] < 18000, in_data_sata[ih5, jh5] > -18000)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_data_sata[tii, tjj] = in_data_sata[tih5, tjh5]

            # 太阳天顶角
            condition = np.logical_and(in_data_sunz[ih5, jh5] < 18000, in_data_sunz[ih5, jh5] > 0)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_data_sunz[tii, tjj] = in_data_sunz[tih5, tjh5]

            # 太阳方位角
            condition = np.logical_and(in_data_suna[ih5, jh5] < 18000, in_data_suna[ih5, jh5] > -18000)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_data_suna[tii, tjj] = in_data_suna[tih5, tjh5]

            # land cover
            condition = np.logical_and(in_data_LandCover[ih5, jh5] < 17, in_data_LandCover[ih5, jh5] > 0)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_LandCover[tii, tjj] = in_data_LandCover[tih5, tjh5]

            # land sea mask
            condition = np.logical_and(in_data_LandSeaMask[ih5, jh5] < 7, in_data_LandSeaMask[ih5, jh5] > 0)
            index = np.where(condition)
            tii = ii[index]
            tjj = jj[index]
            tih5 = ih5[index]
            tjh5 = jh5[index]
            proj_LandSeaMask[tii, tjj] = in_data_LandSeaMask[tih5, tjh5]

        # RefSB_Cal_Coefficients这个属性直接写到hdf中，不进行操作，只是把14转成7*2
        for i in range(7):
            for j in range(2):
                if j == 0:
                    proj_Cal_Coeff[i, j] = in_data_ref_cal[i * 2 + j + 1]
                if j == 1:
                    proj_Cal_Coeff[i, j] = in_data_ref_cal[i * 2 + j - 1]
        # 通过行列号计算经纬度
        lon_x, lat_y = lookup_table.ij2lonlat()
        proj_lon = lon_x.reshape([self.row, self.col])
        proj_lat = lat_y.reshape([self.row, self.col])
        # 原始数据行列号
#         proj_src_row[ii, jj] = ih5
#         proj_src_col[ii, jj] = jh5
#         fill_points_2d(proj_src_row, -999)
#         fill_points_2d(proj_src_col, -999)

        # 进行补点
        for i in range(10):
            fill_points_2d(proj_data_ch10[i], -999)
            fill_points_2d(proj_data_sv10[i], -999)
        for i in range(3):
            fill_points_2d(proj_data_rad[i], -999.)

        fill_points_2d(proj_data_satz, -999)
        fill_points_2d(proj_data_sata, -999)
        fill_points_2d(proj_data_sunz, -999)
        fill_points_2d(proj_data_suna, -999)
#         fill_points_2d(proj_LandCover, -999)
#         fill_points_2d(proj_LandSeaMask, -999)

        # 写入HDF
        opath = os.path.dirname(self.ofile)
        if not os.path.isdir(opath):
            os.makedirs(opath)


        pic_name = self.ofile.split('.hdf')[0] + '.png'
        picFile = urljoin(opath, pic_name)
        dv_img.dv_rgb(proj_data_ch10[0], proj_data_ch10[8], proj_data_ch10[6], picFile, 2, 1)

        h5file_W = h5py.File(self.ofile, 'w')
        h5file_W.create_dataset('10bands_L1B_DN_values', dtype='i2', data=proj_data_ch10, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('RAD_Emissive', dtype='f4', data=proj_data_rad, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('RefSBCoeffcients', dtype='f4', data=proj_Cal_Coeff, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SensorZenith', dtype='i2', data=proj_data_satz, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SensorAzimuth', dtype='i2', data=proj_data_sata, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SolarZenith', dtype='i2', data=proj_data_sunz, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SolarAzimuth', dtype='i2', data=proj_data_suna, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('LandSeaMask', dtype='i2', data=proj_LandSeaMask, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('LandCover', dtype='i2', data=proj_LandCover, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('Longitude', dtype='f4', data=proj_lon, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('Latitude', dtype='f4', data=proj_lat, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SV_DN_average', dtype='i2', data=proj_data_sv10, compression='gzip', compression_opts=5, shuffle=True)
#         h5file_W.create_dataset('IdxRow', dtype='i4', data=proj_src_row, compression='gzip', compression_opts=5, shuffle=True)
#         h5file_W.create_dataset('IdxCol', dtype='i4', data=proj_src_col, compression='gzip', compression_opts=5, shuffle=True)

    def proj_modis(self):

        # 进行数组的初始化
        proj_data_ch38 = np.array([[[-999.] * self.col] * self.row] * 38)
        proj_data_satz = np.array([[-999.] * self.col] * self.row)
        proj_data_sata = np.array([[-999.] * self.col] * self.row)
        proj_data_sunz = np.array([[-999.] * self.col] * self.row)
        proj_data_suna = np.array([[-999.] * self.col] * self.row)
        proj_LandSeaMask = np.array([[-999] * self.col] * self.row)

        proj_src_row = np.array([[-999] * self.col] * self.row)
        proj_src_col = np.array([[-999] * self.col] * self.row)

        # 初始化投影参数
        lookup_table = prj_core(self.cmd, self.res, self.row, self.col)
        for L1File in self.ifile:
            geoFile = find_modis_geo_file(L1File)

            # 读取L1文件
            try:
                h4File = SD(L1File, SDC.READ)
                # 读取1-2通道数据
                in_data_r250 = h4File.select('EV_250_Aggr1km_RefSB').get()
                in_data_r250_s = h4File.select('EV_250_Aggr1km_RefSB').attributes()['reflectance_scales']
                in_data_r250_o = h4File.select('EV_250_Aggr1km_RefSB').attributes()['reflectance_offsets']
                # 读取 3-7通道数据
                in_data_r500 = h4File.select('EV_500_Aggr1km_RefSB').get()
                in_data_r500_s = h4File.select('EV_500_Aggr1km_RefSB').attributes()['reflectance_scales']
                in_data_r500_o = h4File.select('EV_500_Aggr1km_RefSB').attributes()['reflectance_offsets']
                # 读取8-20通道， 包含26通道
                in_data_r1km = h4File.select('EV_1KM_RefSB').get()
                in_data_r1km_s = h4File.select('EV_1KM_RefSB').attributes()['reflectance_scales']
                in_data_r1km_o = h4File.select('EV_1KM_RefSB').attributes()['reflectance_offsets']
                # 读取20-36通道 不包含26通道
                in_data_t1km = h4File.select('EV_1KM_Emissive').get()
                in_data_t1km_s = h4File.select('EV_1KM_Emissive').attributes()['radiance_scales']
                in_data_t1km_o = h4File.select('EV_1KM_Emissive').attributes()['radiance_offsets']
                h4File.end()
            except Exception as e:
                print str(e)
            # 读取GEO文件
            try:
                h4File = SD(geoFile, SDC.READ)
                in_data_lon = h4File.select('Longitude').get()
                in_data_lat = h4File.select('Latitude').get()
                in_data_LandSeaMask = h4File.select('Land/SeaMask').get()  # 多个/不知道是bug还是就这样
                in_data_satz = h4File.select('SensorZenith').get()
                in_data_satz_s = h4File.select('SensorZenith').attributes()['scale_factor']
                in_data_sata = h4File.select('SensorAzimuth').get()
                in_data_sata_s = h4File.select('SensorAzimuth').attributes()['scale_factor']
                in_data_sunz = h4File.select('SolarZenith').get()
                in_data_sunz_s = h4File.select('SolarZenith').attributes()['scale_factor']
                in_data_suna = h4File.select('SolarAzimuth').get()
                in_data_suna_s = h4File.select('SolarAzimuth').attributes()['scale_factor']
                h4File.end()

            except Exception as e:
                print str(e)
            # 获取经度数据集的行和列，制作一个一维的数组长度是 数据集行x列，分别存放行号和列号
            rowh5, colh5 = in_data_lon.shape
            ih5 = np.array([range(rowh5)] * colh5).T.reshape((-1))  # hdf5的行1d序列
            jh5 = np.array([range(colh5)] * rowh5).reshape((-1))  # hdf5的列1d序列
            # 返回投影查找表
#             ii, jj, ih5, jh5 = lookup_table.lonslats2ij(in_data_lon, in_data_lat, ih5, jh5)
            ii, jj = lookup_table.lonslats2ij(in_data_lon, in_data_lat)
            # 投影方格以外的数据过滤掉
            condition = np.logical_and(ii >= 0, ii < self.row)
            condition = np.logical_and(condition, jj >= 0)
            condition = np.logical_and(condition, jj < self.col)
            index = np.where(condition)

            ii = ii[index]
            jj = jj[index]
            ih5 = ih5[index]
            jh5 = jh5[index]

            # 角度和其他信息的投影和补点
            proj_data_satz[ii, jj] = in_data_satz[ih5, jh5] * in_data_satz_s
            proj_data_sata[ii, jj] = in_data_sata[ih5, jh5] * in_data_sata_s
            proj_data_sunz[ii, jj] = in_data_sunz[ih5, jh5] * in_data_sunz_s
            proj_data_suna[ii, jj] = in_data_suna[ih5, jh5] * in_data_suna_s
            proj_LandSeaMask[ii, jj] = in_data_LandSeaMask[ih5, jh5]
            # 1-2通道
            for i in  range(0, 2, 1):
                # 过滤 无效值
                condition = np.logical_and(in_data_r250[i, ih5, jh5] < 32767, in_data_r250[i, ih5, jh5] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_ch38[i, tii, tjj] = (in_data_r250[i, tih5, tjh5] - in_data_r250_o[i]) * in_data_r250_s[i]
            # 3-7通道
            for i in range(2, 7, 1):
                # 过滤 无效值
                condition = np.logical_and(in_data_r500[i - 2, ih5, jh5] < 32767, in_data_r500[i - 2, ih5, jh5] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_ch38[i, tii, tjj] = (in_data_r500[i - 2, tih5, tjh5] - in_data_r500_o[i - 2]) * in_data_r500_s[i - 2]
            # 8-19 外加一个 26通道
            for i in range(7, 22, 1):
                # 过滤 无效值
                condition = np.logical_and(in_data_r1km[i - 7, ih5, jh5] < 32767, in_data_r1km[i - 7, ih5, jh5] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]
                proj_data_ch38[i, tii, tjj] = (in_data_r1km[i - 7, tih5, tjh5] - in_data_r1km_o[i - 7]) * in_data_r1km_s[i - 7]
            # 20-36通道  不包括26通道
            for i in range(22, 38, 1):
                # 过滤 无效值
                condition = np.logical_and(in_data_t1km[i - 22, ih5, jh5] < 32767, in_data_t1km[i - 22, ih5, jh5] > 0)
                index = np.where(condition)
                tii = ii[index]
                tjj = jj[index]
                tih5 = ih5[index]
                tjh5 = jh5[index]

                proj_data_ch38[i, tii, tjj] = (in_data_t1km[i - 22, tih5, tjh5] - in_data_t1km_o[i - 22]) * in_data_t1km_s[i - 22]



        # 删除通道13hi 和  14 hi
        proj_data_ch36 = np.delete(proj_data_ch38, (13, 15), 0)
        # 把rad转亮温
        radiance2tbb(proj_data_ch36)
        # 进行补点
        for i in range(36):
            fill_points_2d(proj_data_ch36[i], -999.)

        fill_points_2d(proj_data_satz, -999.)
        fill_points_2d(proj_data_sata, -999.)
        fill_points_2d(proj_data_sunz, -999.)
        fill_points_2d(proj_data_suna, -999)
#         fill_points_2d(proj_LandSeaMask, -999)

        # 整理通道顺序，把26通道放在对应的26通道
        del26_proj_data_ch35 = np.delete(proj_data_ch36, 19, 0)
        order_proj_data_ch36 = np.insert(del26_proj_data_ch35, 25, proj_data_ch36[19], 0)

        # 通过行列号计算经纬度
        lon_x, lat_y = lookup_table.ij2lonlat()
        proj_lon = lon_x.reshape([self.row, self.col])
        proj_lat = lat_y.reshape([self.row, self.col])

        # 原始数据行列号
        proj_src_row[ii, jj] = ih5
        proj_src_col[ii, jj] = jh5
        fill_points_2d(proj_src_row, -999)
        fill_points_2d(proj_src_col, -999)


        # 写入HDF
        opath = os.path.dirname(self.ofile)
        if not os.path.isdir(opath):
            os.makedirs(opath)
        pic_name = self.ofile.split('.hdf')[0] + '.png'
        picFile = urljoin(opath, pic_name)
        dv_img.dv_rgb(order_proj_data_ch36[0], order_proj_data_ch36[3], order_proj_data_ch36[2], picFile, 2, 1)

        h5file_W = h5py.File(self.ofile, 'w')
        h5file_W.create_dataset('36bands_L1B_Ref_BT_values', dtype='f4', data=order_proj_data_ch36, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SensorZenith', dtype='f4', data=proj_data_satz, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SensorAzimuth', dtype='f4', data=proj_data_sata, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SolarZenith', dtype='f4', data=proj_data_sunz, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('SolarAzimuth', dtype='f4', data=proj_data_suna, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('LandSeaMask', dtype='i2', data=proj_LandSeaMask, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('Longitude', dtype='f4', data=proj_lon, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('Latitude', dtype='f4', data=proj_lat, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('IdxRow', dtype='i4', data=proj_src_row, compression='gzip', compression_opts=5, shuffle=True)
        h5file_W.create_dataset('IdxCol', dtype='i4', data=proj_src_col, compression='gzip', compression_opts=5, shuffle=True)

def find_modis_geo_file(L1File):

    # 根据输入的L1文件自动拼接GEO文件
    ipath = os.path.dirname(L1File)
    iname = os.path.basename(L1File)

    part1 = iname.split('.')[1]
    part2 = iname.split('.')[2]
    pat = u'\w{5}.%s.%s.\d{3}.\d+.hdf$' % (part1, part2)

    if os.path.isdir(ipath):
        Lst = sorted(os.listdir(ipath), reverse=False)
        for line in Lst:
            m = re.match(pat, line)
            if m :
                geoFile = urljoin(ipath, line)
                break
    else:
        print '%s not found' % ipath
        sys.exit(-1)

    return geoFile

def radiance2tbb(r):
    '''
    function radiance2tbb: convert radiance data into brightness temperature (i.e., equivalent blackbody temperature)
    r: spectral radiance data in w/m2/sr/um
    w: wavelength in micro
    return: reture value, brightness temperature in K (absolute temperature)
    '''

    cwn = [2.647409E+03, 2.511760E+03, 2.517908E+03, 2.462442E+03,
        2.248296E+03, 2.209547E+03, 1.474262E+03, 1.361626E+03,
        1.169626E+03, 1.028740E+03, 9.076813E+02, 8.308411E+02,
        7.482978E+02, 7.307766E+02, 7.182094E+02, 7.035007E+02]

    tcs = [9.993363E-01, 9.998626E-01, 9.998627E-01, 9.998707E-01,
        9.998737E-01, 9.998770E-01, 9.995694E-01, 9.994867E-01,
        9.995270E-01, 9.997382E-01, 9.995270E-01, 9.997271E-01,
        9.999173E-01, 9.999070E-01, 9.999198E-01, 9.999233E-01]

    tci = [4.818401E-01, 9.426663E-02, 9.458604E-02, 8.736613E-02,
        7.873285E-02, 7.550804E-02, 1.848769E-01, 2.064384E-01,
        1.674982E-01, 8.304364E-02, 1.343433E-01, 7.135051E-02,
        1.948513E-02, 2.131043E-02, 1.804156E-02, 1.683156E-02]

    h = 6.62606876e-34  # Planck constant (Joule second)
    c = 2.99792458e+8
    k = 1.3806503e-23

    c1 = 2.0 * h * c * c
    c2 = (h * c) / k

#     ws = 1.0e-6 * w  # Convert wavelength to meters
#     tbb = np.full_like(r, -999.)
    # Compute brightness temperature
    for i in range(20, 36, 1):

        index = np.where(r[i])
        index = np.where(r[i] > 0)
        w = 1.0e+4 / cwn[i - 20]
        ws = 1.0e-6 * w
#         r[i] = c2 / (ws * np.log(c1 / (1.0e+6 * r[i] * ws ** 5) + 1.0))
#         r[i] = (r[i] - tci[i - 20]) / tcs[i - 20]
        r[i, index[0], index[1]] = c2 / (ws * np.log(c1 / (1.0e+6 * r[i, index[0], index[1]] * ws ** 5) + 1.0))
        r[i, index[0], index[1]] = (r[i, index[0], index[1]] - tci[i - 20]) / tcs[i - 20]

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
    if proj.sensor == 'MERSI':
        proj.proj_fy3abc_mersi()
    elif proj.sensor == 'VIRR':
        proj.proj_fy3abc_virr()
    elif proj.sat == 'TERRA' or proj.sat == 'AQUA' and proj.sensor == 'MODIS':
        proj.proj_modis()
    else:
        print "not support %s %s" % (proj.sat, proj.sensor)
        sys.exit(-2)

if __name__ == '__main__':
    # 获取python输入参数，进行处理
    args = sys.argv[1:]
    main(args)
