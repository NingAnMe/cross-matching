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

import sys, os, yaml, h5py
# from pyhdf.SD import SD, SDC
from DP.dp_prj import prj_core
import numpy as np
from scipy.interpolate.fitpack2 import UnivariateSpline
# from urlparse import urljoin
import coda

class GOME_COMM():

    def __init__(self):

        self.k = 1.98644746103858e-9

        # 中心 纬度 经度
        self.centre_lat = np.zeros((30, 24))
        self.centre_lon = np.zeros((30, 24))
        self.centre_row = np.zeros((30, 24))
        self.centre_col = np.zeros((30, 24))
        # 角点 纬度 经度
        self.corner_lat = np.zeros((30, 24, 4))
        self.corner_lon = np.zeros((30, 24, 4))
        self.corner_row = np.zeros((30, 24, 4))
        self.corner_col = np.zeros((30, 24, 4))

        self.sun_Z = np.zeros((30, 24))  # 太阳天顶角
        self.sun_A = np.zeros((30, 24))  # 太阳方位角
        self.sat_Z = np.zeros((30, 24))  # 卫星天顶角
        self.sat_A = np.zeros((30, 24))  # 卫星方位角

        self.band3 = np.zeros((30, 24, 1024))  # 辐射值
        self.band4 = np.zeros((30, 24, 1024))
        self.band3_ERR_RAD = np.zeros((30, 24, 1024))
        self.band3_STOKES_FRACTION = np.zeros((30, 24, 1024))
        self.band4_ERR_RAD = np.zeros((30, 24, 1024))
        self.band4_STOKES_FRACTION = np.zeros((30, 24, 1024))
        self.wave3 = np.zeros((30, 1024))  # 波长
        self.wave4 = np.zeros((30, 1024))

#         self.LAMBDA_SMR3 = np.zeros((1, 1024))
#         self.LAMBDA_SMR4 = np.zeros((1, 1024))
#         self.SMR3 = np.zeros((1, 1024))
#         self.SMR4 = np.zeros((1, 1024))
#         self.E_SMR3 = np.zeros((1, 1024))
#         self.E_SMR4 = np.zeros((1, 1024))
#         self.E_REL_SUN3 = np.zeros((1, 1024))
#         self.E_REL_SUN4 = np.zeros((1, 1024))

        self.E_SMR3 = np.zeros((1024))
        self.E_SMR4 = np.zeros((1024))
        self.E_REL_SUN3 = np.zeros((1024))
        self.E_REL_SUN4 = np.zeros((1024))


        self.arr_GOME_L = np.zeros((2048, 30, 24))  # 辐亮度
        self.arr_GOME_WL = np.zeros((2048, 30, 24))  # 辐亮度对应的波长

        self.vec_Solar_L = np.zeros((2, 1024))  # 太阳辐亮度
        self.vec_Solar_WL = np.zeros((2, 1024))  # 太阳辐亮度对应的波长

        # 如下变量是通过卷积计算的
        self.vec_Radiance_Solar = np.zeros(15)
        self.vec_Radiance = np.zeros((15, 30, 24))
        self.arr_Ref = np.zeros((15, 30, 24))

    def init_gome(self, in_proj_cfg, des_sensor):

        '''
        读取yaml格式配置文件
        '''
        if not os.path.isfile(in_proj_cfg):
            print 'Not Found %s' % in_proj_cfg
            sys.exit(-1)

        with open(in_proj_cfg, 'r') as stream:
            cfg = yaml.load(stream)

        self.sat1 = cfg['INFO']['sat']
        self.sensor1 = cfg['INFO']['sensor']
        self.sensor2 = des_sensor
        self.ymd = cfg['INFO']['ymd']

        self.ifile = cfg['PATH']['ipath']
        self.ofile = cfg['PATH']['opath']

        self.cmd = cfg['PROJ']['cmd']
        self.col = cfg['PROJ']['col']
        self.row = cfg['PROJ']['row']
        self.res = cfg['PROJ']['res']

    def read_gome(self, infile):
        # 打开gome文件
        try:
            fp = coda.open(infile)
        except Exception, e:
            print 'Open file error<%s> .' % (e)
            return
        # 获取文件头信息
        product_class = coda.get_product_class(fp)
        product_type = coda.get_product_type(fp)
        product_version = coda.get_product_version(fp)
        product_format = coda.get_product_format(fp)
        product_size = coda.get_product_file_size(fp)
        # EPS = EUMETSAT Polar System atmospheric products (GOME-2 and IASI)
        # EUMETSAT极地大气系统产品（GOME-2和IASI）'
        print 'product_class ', product_class
        print 'product_type', product_type
        print 'product_version' , product_version
        print 'product_format', product_format
        print 'product_size', product_size


        CENTRE = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'GEO_EARTH', 'CENTRE')
        CORNER = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'GEO_EARTH', 'CORNER')
        SUN_Z = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'GEO_EARTH', 'SOLAR_ZENITH')
        SUN_A = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'GEO_EARTH', 'SOLAR_AZIMUTH')
        SAT_Z = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'GEO_EARTH', 'SAT_ZENITH')
        SAT_A = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'GEO_EARTH', 'SAT_AZIMUTH')
        BAND_3 = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'BAND_3')
        BAND_4 = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'BAND_4')
        WAVE_3 = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'WAVELENGTH_3')
        WAVE_4 = coda.fetch(fp, 'MDR', -1, 'Earthshine', 'WAVELENGTH_4')
        LAMBDA_SMR = coda.fetch(fp, 'VIADR_SMR', -1, 'LAMBDA_SMR')
        SMR = coda.fetch(fp, 'VIADR_SMR', -1, 'SMR')
        E_SMR = coda.fetch(fp, 'VIADR_SMR', -1, 'E_SMR')
        E_REL_SUN = coda.fetch(fp, 'VIADR_SMR', -1, 'E_REL_SUN')

#         fp.close()

#         print 'CENTRE', CENTRE.shape, CENTRE[0].shape
#         print 'CORNER', CORNER.shape, CORNER[0].shape
#         print 'SUN_Z', SUN_Z.shape, SUN_Z[0].shape
#         print 'SUN_A', SUN_A.shape, SUN_A[0].shape
#         print 'SAT_Z', SAT_Z.shape, SAT_Z[0].shape
#         print 'SAT_A', SAT_A.shape, SAT_A[0].shape
#         print 'BAND_3', BAND_3.shape, BAND_3[0].shape
#         print 'BAND_4', BAND_4.shape, BAND_4[0].shape
#         print 'WAVE_3', WAVE_3.shape, WAVE_3[0].shape
#         print 'WAVE_4', WAVE_4.shape, WAVE_4[0].shape
#         print 'LAMBDA_SMR', LAMBDA_SMR.shape, LAMBDA_SMR[0].shape
#         print 'SMR', SMR.shape, SMR[0].shape
#         print 'E_SMR', E_SMR.shape, E_SMR[0].shape
#         print 'E_REL_SUN', E_REL_SUN.shape, E_REL_SUN[0].shape
#         print LAMBDA_SMR[0][0][1023]
#         print BAND_3[0][23][1023].RAD
#         print self.band3.shape

        for i in range(30):
            count = coda.get_size(fp, 'MDR', i, 'Earthshine', 'BAND_3')
            for j in range(int(count[0] * 0.75)):
                for m in range(1024):

                    self.band3[i][j][m] = BAND_3[i][j][m].RAD
                    self.band3_ERR_RAD[i][j][m] = BAND_3[i][j][m].ERR_RAD
                    self.band3_STOKES_FRACTION[i][j][m] = BAND_3[i][j][m].STOKES_FRACTION
                    self.band4[i][j][m] = BAND_4[i][j][m].RAD
                    self.band4_ERR_RAD[i][j][m] = BAND_4[i][j][m].ERR_RAD
                    self.band4_STOKES_FRACTION[i][j][m] = BAND_4[i][j][m].STOKES_FRACTION

        for m in range(2048):
            for i in range(30):
                count = coda.get_size(fp, 'MDR', i, 'Earthshine', 'BAND_3')
                for j in range(int(count[0] * 0.75)):
                    if m < 1024:
                        if BAND_3[i][j][m].RAD < 0:
                            BAND_3[i][j][m].RAD = 0
                        self.arr_GOME_L[m][i][j] = (BAND_3[i][j][m].RAD * self.k) / WAVE_3[i][m]
                        self.arr_GOME_WL[m][i][j] = WAVE_3[i][m]

                    else:
                        if BAND_4[i][j][m - 1024].RAD < 0:
                            BAND_4[i][j][m - 1024].RAD = 0
                        self.arr_GOME_L[m][i][j] = (BAND_4[i][j][m - 1024].RAD * self.k) / WAVE_4[i][m - 1024]
                        self.arr_GOME_WL[m][i][j] = WAVE_4[i][m - 1024]

        for i in range(2):
            for j in range(1024):
                if i == 0:
                    self.vec_Solar_L[i][j] = (SMR[0][2][j] * self.k) / LAMBDA_SMR[0][2][j]  # 太阳辐亮度
                    self.vec_Solar_WL[i][j] = LAMBDA_SMR[0][2][j]
                    self.E_SMR3[j] = E_SMR[0][2][j]
                    self.E_REL_SUN3[j] = E_REL_SUN[0][2][j]
                elif i == 1:
                    self.vec_Solar_L[i][j] = (SMR[0][3][j] * self.k) / LAMBDA_SMR[0][3][j]  # 太阳辐亮度
                    self.vec_Solar_WL[i][j] = LAMBDA_SMR[0][3][j]
                    self.E_SMR4[j] = E_SMR[0][3][j]
                    self.E_REL_SUN4[j] = E_REL_SUN[0][3][j]

        for i in range(30):
            for j in range(24):
                self.sun_A[i][j] = SUN_A[i][1][j]
                self.sun_Z[i][j] = SUN_Z[i][1][j]
                self.sat_A[i][j] = SAT_A[i][1][j]
                self.sun_Z[i][j] = SAT_Z[i][1][j]
                self.centre_lat[i][j] = CENTRE[i][j].latitude
                self.centre_lon[i][j] = CENTRE[i][j].longitude

        for i in range(30):
            for j in range(24):
                for m in range(4):
                    self.corner_lat[i][j][m] = CORNER[i][m][j].latitude
                    self.corner_lon[i][j][m] = CORNER[i][m][j].longitude
        coda.close(fp)


    def proj_gome(self):
        # 初始化投影参数
        lookup_table = prj_core(self.cmd, self.res, self.row, self.col)
        # 返回投影查找表,投影中心点
        ii, jj = lookup_table.lonslats2ij(self.centre_lon, self.centre_lat)
        for i in range(30):
            for j in range(24):
                self.centre_row[i][j] = ii[24 * i + j]
                self.centre_col[i][j] = jj[24 * i + j]

        # 投影角点
        ii, jj = lookup_table.lonslats2ij(self.corner_lon, self.corner_lat)
        for i in range(30):
            for j in range(24):
                for m in range(4):
                    self.corner_row[i][j][m] = ii[i * 24 * 4 + j * 4 + m]
                    self.corner_col[i][j][m] = jj[i * 24 * 4 + j * 4 + m]

    def trapz_gome(self):

        MainPath = os.path.split(os.path.realpath(__file__))[0]
        bandFile = os.path.join(MainPath, 'Newband.h5')
        h5File = h5py.File(bandFile, 'r')
        # 把gome的通道做成390-800波段间隔1纳米的响应
        solar_x = np.arange(390, 801, 1)
        solar_y1 = np.interp(solar_x, self.vec_Solar_WL[0], self.vec_Solar_L[0])
        solar_y2 = np.interp(solar_x, self.vec_Solar_WL[1], self.vec_Solar_L[1])

        # 把gome俩头的波段对应的响应值赋值为0
        x_min = int(self.vec_Solar_WL[0][0])
        x_max = int(self.vec_Solar_WL[0][-1])
        condition = np.logical_or(solar_x < x_min, solar_x > x_max)
        idx = np.where(condition)
        solar_y1[idx] = 0

        x_min = int(self.vec_Solar_WL[1][0])
        x_max = int(self.vec_Solar_WL[1][-1])
        condition = np.logical_or(solar_x < x_min, solar_x > x_max)
        idx = np.where(condition)
        solar_y2[idx] = 0

        solar_y = solar_y1 + solar_y2

#         print '1', solar_x
#         print '4', solar_y.shape
        for i in xrange(1, 16):

            if self.sensor2 == 'VIRR':
                if i != 1 and i != 7  and  i != 8 and i != 9:
                    continue
                sdsname = "virr_%d" % (i)
            elif self.sensor2 == 'MERSI':
                if i > 3 and i < 8:
                    continue
                sdsname = "mersi_%d" % (i)

            elif self.sensor2 == 'MERSI2':  # wangpeng add mersi2
                if (i > 3 and i < 8) or (i > 14):
                    continue
                sdsname = "mersi2_%d" % (i)
            elif self.sensor2 == 'MODIS':
                if i > 3 and i < 8:
                    continue
                sdsname = "modis_%d" % (i)
            print sdsname
            indata = h5File.get(sdsname)[:]
            s1 = np.trapz(solar_y * indata[:, 1], indata[:, 0])
            s2 = np.trapz(indata[:, 1], indata[:, 0])
            self.vec_Radiance_Solar[i - 1] = s1 / s2

            for j in xrange(30):
                for m in xrange(24):

                    # 把gome的通道做成390-800波段间隔1纳米的响应
                    gome_x = np.arange(390, 801, 1)
                    gome_wl1 = self.arr_GOME_WL[0:1024, j, m]
                    gome_l1 = self.arr_GOME_L[0:1024:, j, m]
                    gome_y1 = np.interp(gome_x, gome_wl1, gome_l1)

                    gome_wl2 = self.arr_GOME_WL[1024:2048, j, m]
                    gome_l2 = self.arr_GOME_L[1024:2048:, j, m]
                    gome_y2 = np.interp(gome_x, gome_wl2, gome_l2)

                    # 把gome俩头的波段对应的响应值赋值为0
                    x_min = int(gome_wl1[0])
                    x_max = int(gome_wl1[-1])
                    condition = np.logical_or(solar_x < x_min, solar_x > x_max)
                    idx = np.where(condition)
                    gome_y1[idx] = 0

                    x_min = int(gome_wl2[0])
                    x_max = int(gome_wl2[-1])
                    condition = np.logical_or(solar_x < x_min, solar_x > x_max)
                    idx = np.where(condition)
                    gome_y2[idx] = 0
                    gome_y = gome_y1 + gome_y2

                    s1 = np.trapz(gome_y * indata[:, 1], indata[:, 0])
                    s2 = np.trapz(indata[:, 1], indata[:, 0])

                    self.vec_Radiance[i - 1][j][m] = s1 / s2
                    self.arr_Ref[i - 1][j][m] = self.vec_Radiance[i - 1][j][m] / self.vec_Radiance_Solar[i - 1] * np.pi / np.cos(self.sun_Z[j][m] * np.pi / 180.)
        h5File.close()

#         return
#
#         for i in xrange(1, 16):
#             if i > 3 and i < 8:
#                 continue
#             if self.sensor2 == 'MERSI':
#                 sdsname = "Mersi_%d" % (i)
#             elif self.sensor2 == 'MODIS':
#                 sdsname = "Modis_%d" % (i)
#
#             if i == 3 or  i == 13 or i == 14 or i == 15 :
#                 indata = h5File.get(sdsname)[:]
# #                 vec_GOME_Rad_Es = np.interp(indata[:, 0], self.vec_Solar_WL[1], self.vec_Solar_L[1])
#
#                 vec_GOME_Rad_Es = UnivariateSpline(self.vec_Solar_WL[1], self.vec_Solar_L[1])(indata[:, 0])
#                 s1 = np.trapz(vec_GOME_Rad_Es * indata[:, 1], indata[:, 0])
#                 s2 = np.trapz(indata[:, 1], indata[:, 0])
#                 self.vec_Radiance_Solar[i - 1] = s1 / s2
#
#             else:
#                 indata = h5File.get(sdsname)[:]
#                 vec_GOME_Rad_Es = np.interp(indata[:, 0], self.vec_Solar_WL[0], self.vec_Solar_L[0])
#                 vec_GOME_Rad_Es2 = UnivariateSpline(self.vec_Solar_WL[0], self.vec_Solar_L[0])(indata[:, 0])
#                 s1 = np.trapz(vec_GOME_Rad_Es * indata[:, 1], indata[:, 0])
#                 s2 = np.trapz(indata[:, 1], indata[:, 0])
#                 print 'one', i, vec_GOME_Rad_Es
#                 print 'two', i, vec_GOME_Rad_Es2
# #                 if i == 3:
# #                     print s1, s2, i, sdsname
# #                     print 'x', indata[:, 0]
# #                     print 'y', vec_GOME_Rad_Es
#                 self.vec_Radiance_Solar[i - 1] = s1 / s2
# #             print self.vec_Radiance_Solar
#
#         for i in xrange(1, 16):
#             if i > 3 and i < 8:
#                 continue
#             if self.sensor2 == 'MERSI':
#                 sdsname = "Mersi_%d" % (i)
#             elif self.sensor2 == 'MODIS':
#                 sdsname = "Modis_%d" % (i)
#
#             for j in xrange(30):
#                 for m in xrange(24):
#
#                     if i == 3 or  i == 13 or i == 14 or i == 15 :
#                         indata = h5File.get(sdsname)[:]
#                         gome_wl = self.arr_GOME_WL[1024:2048, j, m]
#                         gome_l = self.arr_GOME_L[1024:2048:, j, m]
#                         arr_GOME_Rad_Es = UnivariateSpline(gome_wl, gome_l)(indata[:, 0])
#                         s1 = np.trapz(arr_GOME_Rad_Es * indata[:, 1], indata[:, 0])
#                         s2 = np.trapz(indata[:, 1], indata[:, 0])
#                         self.vec_Radiance[i - 1][j][m] = s1 / s2
#                     else:
#                         indata = h5File.get(sdsname)[:]
#                         gome_wl = self.arr_GOME_WL[:1024, j, m]
#                         gome_l = self.arr_GOME_L[:1024:, j, m]
#                         arr_GOME_Rad_Es = UnivariateSpline(gome_wl, gome_l)(indata[:, 0])
#                         s1 = np.trapz(arr_GOME_Rad_Es * indata[:, 1], indata[:, 0])
#                         s2 = np.trapz(indata[:, 1], indata[:, 0])
#                         self.vec_Radiance[i - 1][j][m] = s1 / s2
#
#
#                     self.arr_Ref[i - 1][j][m] = self.vec_Radiance[i - 1][j][m] / self.vec_Radiance_Solar[i - 1] * np.pi / np.cos(self.sun_Z[j][m] * np.pi / 180.)
#         h5File.close()
# #             print self.vec_Radiance

    def write_gome(self, ofile):

        opath = os.path.dirname(ofile)
        if not os.path.isdir(opath):
            os.makedirs(opath)

        h5file = h5py.File(ofile, 'w')

        h5file.create_group("/Data")
        h5file.create_group("/Geo")
        h5file.create_group("/IdexRowCol")
        h5file.create_group("/SNO")
        h5file.create_group("/VIADR_SMR")
        # 写入数据集 group Data
        h5file.create_dataset('/Data/Radiance', dtype='f4', data=self.arr_GOME_L, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Data/Radiance_Wavelength', dtype='f4', data=self.arr_GOME_WL, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Data/BAND3_ERR_RAD', dtype='f4', data=self.band3_ERR_RAD, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Data/BAND3_STOKES_FRACTION', dtype='f4', data=self.band3_STOKES_FRACTION, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Data/BAND4_ERR_RAD', dtype='f4', data=self.band4_ERR_RAD, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Data/BAND4_STOKES_FRACTION', dtype='f4', data=self.band4_STOKES_FRACTION, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Data/Solar_Radiance', dtype='f4', data=self.vec_Solar_L, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Data/Solar_Radiance_Wavelength', dtype='f4', data=self.vec_Solar_WL, compression='gzip', compression_opts=5, shuffle=True)

        # group VIADR_SMR
        h5file.create_dataset('/VIADR_SMR/E_SMR3', dtype='f4', data=self.E_SMR3, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/VIADR_SMR/E_SMR4', dtype='f4', data=self.E_SMR4, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/VIADR_SMR/E_REL_SUN3', dtype='f4', data=self.E_REL_SUN3, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/VIADR_SMR/E_REL_SUN4', dtype='f4', data=self.E_REL_SUN4, compression='gzip', compression_opts=5, shuffle=True)

        # group Geo
        h5file.create_dataset('/Geo/Zenith_Solar', dtype='f4', data=self.sun_Z, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Geo/Amuzith_Solar', dtype='f4', data=self.sun_A, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Geo/Zenith_Satellite', dtype='f4', data=self.sat_Z, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Geo/Amuzith_Satellite', dtype='f4', data=self.sat_A, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Geo/Lat_Center', dtype='f4', data=self.centre_lat, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Geo/Lon_Center', dtype='f4', data=self.centre_lon, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Geo/Lat_Edge', dtype='f4', data=self.corner_lat, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/Geo/Lon_Edge', dtype='f4', data=self.corner_lon, compression='gzip', compression_opts=5, shuffle=True)

        # group IdexRowCol
        h5file.create_dataset('/IdexRowCol/r_Center', dtype='f4', data=self.centre_row, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/IdexRowCol/c_Center', dtype='f4', data=self.centre_col, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/IdexRowCol/r_Edge', dtype='f4', data=self.corner_row, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/IdexRowCol/c_Edge', dtype='f4', data=self.corner_col, compression='gzip', compression_opts=5, shuffle=True)

        # grop SNO
        h5file.create_dataset('/SNO/Radiance_Conv', dtype='f4', data=self.vec_Radiance, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/SNO/Radiance_Solar_Conv', dtype='f4', data=self.vec_Radiance_Solar, compression='gzip', compression_opts=5, shuffle=True)
        h5file.create_dataset('/SNO/Reflectance_GOME', dtype='f4', data=self.arr_Ref, compression='gzip', compression_opts=5, shuffle=True)

        h5file.close()

def main(args):
    if len(args) == 2:  # 跟参数，则处理输入的时段数据
        in_proj_cfg = args[0]
        des_sensor = args[1]
    else:
        in_proj_cfg = None

    if in_proj_cfg == None:
        print 'input args error exit'
        sys.exit(-1)
    # 初始化投影公共类
    proj = GOME_COMM()
    proj.init_gome(in_proj_cfg, des_sensor)
    for i in xrange(len(proj.ifile)):
        path, filename = os.path.split(proj.ofile)
        newFileName = filename.split('.hdf')[0] + '_%s.hdf' % i
        ofile = os.path.join(path, newFileName)
        proj.__init__()
        proj.read_gome(proj.ifile[i])
        proj.proj_gome()
        proj.trapz_gome()
        proj.write_gome(ofile)
    # 根据卫星传感器调用不同的投影函数

if __name__ == '__main__':
    # 获取python输入参数，进行处理
    args = sys.argv[1:]
    main(args)
