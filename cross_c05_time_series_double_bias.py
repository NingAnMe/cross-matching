# coding: utf-8
"""
Created on 2016年1月6日
读取匹配后的NC文件，画散点回归图，生成abr文件

@author: duxiang, zhangtao, anning
"""
import os, sys
from configobj import ConfigObj
import netCDF4
import numpy as np
from PB import pb_time, pb_io
from PB.CSC.pb_csc_console import LogServer

from datetime import datetime
from DV.dv_pub_legacy import plt, mdates, set_tick_font, FONT0
from DM.SNO.dm_sno_cross_calc_map import RED, BLUE, EDGE_GRAY, ORG_NAME, mpatches
from matplotlib.ticker import MultipleLocator
import pytz
import calendar

from cross_pb_io import loadYamlCfg


def run(pair1, pair2, date_s, date_e):
    """
    pair: sat1+sensor1_sat2+sensor2
    date_s: datetime of start date
            None  处理 从发星 到 有数据的最后一天
    date_e: datetime of end date
            None  处理 从发星 到 有数据的最后一天
    """
    Log.info(u'开始运行双差统计图绘制程序%s %s-----------------' % (pair1, pair2))
    isLaunch = False
    if date_s is None or date_e is None:
        isLaunch = True

    satsen11, satsen12 = pair1.split("_")
    satsen21, satsen22 = pair2.split("_")

    if satsen11 != satsen21:
        Log.error("%s and %s not the same, can't do double bias" % (satsen11, satsen21))
        return

    # 读取配置文件
    plt_cfg_file = os.path.join(MAIN_PATH, "cfg", "%s.plt" % pair1)
    plt_cfg = loadYamlCfg(plt_cfg_file)

    chans = plt_cfg["rad-rad"]["chan"]

    # change sensor Name
    if "VISSR" in satsen11:  # VISSR -> SVISSR
        satsen11 = satsen11.replace("VISSR", "SVISSR")
        satsen21 = satsen21.replace("VISSR", "SVISSR")
    if "METOP-" in satsen12:  # METOP -> MetOp
        satsen12 = satsen12.replace("METOP-", "MetOp")
    if "METOP-" in satsen22:  # METOP -> MetOp
        satsen22 = satsen22.replace("METOP-", "MetOp")
    flst = [e for e in os.listdir(StdNC_DIR) if os.path.isfile(os.path.join(StdNC_DIR, e))]
    nc1_path = nc2_path = None
    for each in flst:
        if satsen11 in each and satsen12 in each:
            nc1_path = os.path.join(StdNC_DIR, each)
        if satsen21 in each and satsen22 in each:
            nc2_path = os.path.join(StdNC_DIR, each)
    nc1 = stdNC()
    if not nc1.LoadData(nc1_path):
        return
    nc2 = stdNC()
    if not nc2.LoadData(nc2_path):
        return

    time1 = nc1.time[:, 0]
    time2 = nc2.time[:, 0]
    tbbias1 = nc1.tbbias
    tbbias2 = nc2.tbbias
    reftmp = nc1.reftmp

    if date_s is None:  # TODO:
#         timestamp_s = max(time1[0], time2[0])
#         date_s = datetime.fromtimestamp(timestamp_s, tz=pytz.utc)
        sat1, sen1 = satsen11.split("+")
        date_s = pb_time.ymd2date(GLOBAL_CONFIG["LUANCH_DATE"][sat1])
    date_s = pytz.utc.localize(date_s)
    timestamp_s = calendar.timegm(date_s.timetuple())

    if date_e is None:
        timestamp_e = min(time1[-1], time2[-1])
        date_e = datetime.fromtimestamp(timestamp_e, tz=pytz.utc)
    else:
        date_e = pytz.utc.localize(date_e)
        timestamp_e = calendar.timegm(date_e.timetuple())

    days1 = tbbias1.shape[0]
    days2 = tbbias2.shape[0]

    index1 = []
    index2 = []
    date_D = []
    for i in xrange(days1):
        if time1[i] < timestamp_s or time1[i] > timestamp_e:
            continue

        idxs2 = np.where(time2 == time1[i])[0]
        if len(idxs2) != 1:
            continue

        date_D.append(datetime.fromtimestamp(time1[i]))
        index1.append(i)
        index2.append(idxs2[0])

    if len(date_D) == 0:
        return

    for k, ch in enumerate(chans):
        ch = chans[k]
        ref_temp = reftmp[k]
        tb1 = tbbias1[index1, k]
        tb2 = tbbias2[index2, k]
        bias_D = tb1 - tb2

        idx = np.logical_or(tb1 < -998, tb2 < -998)
        bias_D[idx] = None

        date_M, bias_M = month_mean(date_D, bias_D)

        title = 'Time Series of Double Bias \n%s_%s Miuns %s_%s %s %dK' % \
                (satsen11, satsen12, satsen11, satsen22, ch, ref_temp)
        if isLaunch:
            picPath = os.path.join(DBB_DIR, '%s_%s' % (pair1, satsen22),
                        '%s_%s_DoubleBias_%s_Launch_%dK.png' % (pair1, satsen22, ch, ref_temp))
        else:
            # plot latest year
            ymd_s = date_s.strftime("%Y%m%d")
            ymd_e = date_e.strftime("%Y%m%d")
            picPath = os.path.join(DBB_DIR, '%s_%s' % (pair1, satsen22), ymd_s,
                        '%s_%s_DoubleBias_%s_Year_%s_%dK.png' % (pair1, satsen22, ch, ymd_s, ref_temp))
        plot_tbbias(date_D, bias_D, date_M, bias_M, picPath, title, date_s, date_e)

    Log.info(u'Success')


def plot_tbbias(date_D, bias_D, date_M, bias_M, picPath, title, date_s, date_e):
    """
    画偏差时序折线图
    """
    plt.style.use(os.path.join(DV_PATH, 'dv_pub_timeseries.mplstyle'))
    fig = plt.figure(figsize=(6, 4))
#     plt.subplots_adjust(left=0.13, right=0.95, bottom=0.11, top=0.97)

    if (np.isnan(bias_D)).all():
        Log.error('Everything is NaN: %s' % picPath)
        return

    plt.plot(date_D, bias_D, 'x', ms=6,
             markerfacecolor=None, markeredgecolor=BLUE, alpha=0.8,
             mew=0.3, label='Daily')

    plt.plot(date_M, bias_M, 'o-', ms=5, lw=0.6, c=RED,
             mew=0, label='Monthly')
    plt.grid(True)
    plt.ylabel('DTB($K$)', fontsize=11, fontproperties=FONT0)

    xlim_min = date_s
    xlim_max = date_e
    plt.xlim(xlim_min, xlim_max)
    plt.ylim(-1, 1)

    # 画 y=0 线
    plt.plot([xlim_min, xlim_max], [0, 0], color='#808080',
             linewidth=1.0)

    ax = plt.gca()
    # format the ticks
    setXLocator(ax, xlim_min, xlim_max)
    set_tick_font(ax)
    ax.yaxis.set_major_locator(MultipleLocator(0.25))
    ax.yaxis.set_minor_locator(MultipleLocator(0.125))

    # title
    plt.title(title, fontsize=12, fontproperties=FONT0)

    plt.tight_layout()
    #--------------------
    fig.subplots_adjust(bottom=0.2)

    circle1 = mpatches.Circle((74, 15), 6, color=BLUE, ec=EDGE_GRAY, lw=0)
    circle2 = mpatches.Circle((164, 15), 6, color=RED, ec=EDGE_GRAY, lw=0)
    fig.patches.extend([circle1, circle2])

    fig.text(0.15, 0.02, 'Daily', color=BLUE, fontproperties=FONT0)
    fig.text(0.3, 0.02, 'Monthly', color=RED, fontproperties=FONT0)

    ymd_s, ymd_e = date_s.strftime('%Y%m%d'), date_e.strftime('%Y%m%d')
    if ymd_s != ymd_e:
        fig.text(0.50, 0.02, '%s-%s' % (ymd_s, ymd_e), fontproperties=FONT0)
    else:
        fig.text(0.50, 0.02, '%s' % ymd_s, fontproperties=FONT0)

    fig.text(0.8, 0.02, ORG_NAME, fontproperties=FONT0)
    #---------------
    pb_io.make_sure_path_exists(os.path.dirname(picPath))
    plt.savefig(picPath)
    fig.clear()
    plt.close()


def setXLocator(ax, xlim_min, xlim_max):
    day_range = (xlim_max - xlim_min).days
#     if day_range <= 2:
#         days = mdates.HourLocator(interval=4)
#         ax.xaxis.set_major_locator(days)
#         ax.xaxis.set_major_formatter(mdates.DateFormatter('%H'))
    if day_range <= 60:
        days = mdates.DayLocator(interval=(day_range / 6))
        ax.xaxis.set_major_locator(days)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    else:
        month_range = day_range / 30
        if month_range <= 12.:
            months = mdates.MonthLocator()  # every month
            ax.xaxis.set_major_locator(months)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        elif month_range <= 24.:
            months = mdates.MonthLocator(interval=2)
            ax.xaxis.set_major_locator(months)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        elif month_range <= 48.:
            months = mdates.MonthLocator(interval=4)
            ax.xaxis.set_major_locator(months)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b'))
        else:
            years = mdates.YearLocator()
            ax.xaxis.set_major_locator(years)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

        if month_range <= 48:
            add_year_xaxis(ax, xlim_min, xlim_max)


def add_year_xaxis(ax, xlim_min, xlim_max):
    """
    add year xaxis
    """
    if xlim_min.year == xlim_max.year:
        ax.set_xlabel(xlim_min.year, fontsize=11, fontproperties=FONT0)
        return
    newax = ax.twiny()
    newax.set_frame_on(True)
    newax.grid(False)
    newax.patch.set_visible(False)
    newax.xaxis.set_ticks_position('bottom')
    newax.xaxis.set_label_position('bottom')
    newax.set_xlim(xlim_min, xlim_max)
    newax.xaxis.set_major_locator(mdates.YearLocator())
    newax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    newax.spines['bottom'].set_position(('outward', 20))
    newax.spines['bottom'].set_linewidth(0.6)

    newax.tick_params(which='both', direction='in')
    set_tick_font(newax)
    newax.xaxis.set_tick_params(length=5)


class stdNC():
    def __init__(self):
        self.tbbias = None
        self.time = None
        self.reftmp = None

    def LoadData(self, i_file):
        noError = True
        if not os.path.isfile(i_file):
            Log.error("%s not exist!" % i_file)
            return False

        try:
            ncFile = netCDF4.Dataset(i_file, 'r', format='NETCDF4')
            self.tbbias = ncFile["std_scene_tb_bias"][:]
            self.time = ncFile["date"][:]
            self.channel = ncFile["channel_name"][:]
            self.reftmp = ncFile["std_scene_tb"][:]
            ncFile.close()
        except:
            noError = False
            Log.error("NC corrupted: %s" % i_file)
        return noError


def month_mean(dateLst, v):
    v = np.array(v)
    monthLst = []
    meanLst = []
    ym = None
    idx = []
    for i in xrange(len(dateLst)):
        if v[i] is None:
            continue
        dt = dateLst[i]
        if ym is None:
            ym = dt.strftime("%Y%m")
        if ym == dt.strftime("%Y%m"):
            idx.append(i)
        else:
            monthLst.append(datetime.strptime("%s15" % ym, "%Y%m%d"))
            meanLst.append(np.mean(v[idx]))
            idx = [i]
            ym = dt.strftime("%Y%m")
    monthLst.append(datetime.strptime("%s15" % ym, "%Y%m%d"))
    meanLst.append(np.mean(v[idx]))
    return monthLst, meanLst


######################### 程序全局入口 ##############################
if __name__ == "__main__":
    # 获取程序参数接口
    ARGS = sys.argv[1:]
    HELP_INFO = \
        u"""
        [参数1]：group 卫星对组
        [参数2]：yyyymmdd 时间
        [样例]: python app.py group yyyymmdd
        """
    if "-h" in ARGS:
        print HELP_INFO
        sys.exit(-1)

    # 获取程序所在位置，拼接配置文件
    MAIN_PATH, MAIN_FILE = os.path.split(os.path.realpath(__file__))
    CONFIG_FILE = os.path.join(MAIN_PATH, "cfg", "global.cfg")

    PYTHON_PATH = os.environ.get("PYTHONPATH")
    DV_PATH = os.path.join(PYTHON_PATH, "DV")

    # 配置不存在预警
    if not os.path.isfile(CONFIG_FILE):
        print (u"配置文件不存在 %s" % CONFIG_FILE)
        sys.exit(-1)

    GLOBAL_CONFIG = ConfigObj(CONFIG_FILE)
    StdNC_DIR = GLOBAL_CONFIG['PATH']['OUT']['ISN']
    DBB_DIR = GLOBAL_CONFIG['PATH']['OUT']['DBB']
    LogPath = GLOBAL_CONFIG['PATH']['OUT']['LOG']
    Log = LogServer(LogPath)

    if len(ARGS) == 2:
        satPair = ARGS[0]
        str_time = ARGS[1]
        DATE_START, DATE_END = pb_time.arg_str2date(str_time)
        PAIR_1 = GLOBAL_CONFIG['DOUBLE_BIAS'][satPair]['pair1']
        PAIR_2 = GLOBAL_CONFIG['DOUBLE_BIAS'][satPair]['pair2']
        run(PAIR_1, PAIR_2, DATE_START, DATE_END)

    else:
        print HELP_INFO
        sys.exit(-1)
