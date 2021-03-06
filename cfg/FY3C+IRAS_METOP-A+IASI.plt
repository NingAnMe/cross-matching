sensor1: IRAS
sensor2: IASI

##########日匹配结果的分布图 ###############
collocation_map:
  chan: [CH_01, CH_02, CH_03,CH_04, CH_05,CH_06,CH_07,CH_08,CH_09,CH_10,CH_11,CH_12,CH_13,CH_14,CH_15,CH_16,CH_17,CH_18,CH_19,CH_20]
  maptype: [polar, area]  # area=区域分布图，polar=两极分布图 暂时支持两种
  area: [-90, 90, -180, 180] # 区域范围
  polar:
   - [60, 60, -180, 180]  # 北极范围
   - [-60, -60, -180, 180] # 南极范围
  nadir: None
  days: 1


regression: [rad-rad, tbb-tbb]  # 需要绘图的物理元素对
monthly_staistics: [tbb-tbb]  # 如果以前的配置文件有 bias 项，画月统计
time_series: [tbb-tbb]  # 如果以前的配置文件有 bias 项，画 TBBias

#------physical quantity info------
#----------------------------------
rad-rad:
  chan: [CH_01, CH_02, CH_03,CH_04, CH_05,CH_06,CH_07,CH_08,CH_09,CH_10,CH_11,CH_12,CH_13,CH_14,CH_15,CH_16,CH_17,CH_18,CH_19,CH_20]
  x_name: Radiance
  y_name: Radiance
  x_unit: 'mw/m^2/sr/cm^{-1}'
  y_unit: 'mw/m^2/sr/cm^{-1}'
  x_range: [0-180, 0-180, 0-180,0-180,0-180,0-180,0-180,0-180,0-180,0-180,0-180,0-20,0-10,0-2,0-2,0-2,0-2,0-2,0-2,0-2]
  y_range: [0-180, 0-180, 0-180,0-180,0-180,0-180,0-180,0-180,0-180,0-180,0-180,0-20,0-10,0-2,0-2,0-2,0-2,0-2,0-2,0-2]
  slope_range: [0.98-1.02, 0.98-1.02, 0.98-1.02]
  days: 2  # 针对当前日期向前滚动天数
  time: [all, day, night] # 针对某一天的时间段

tbb-tbb:
  chan: [CH_01, CH_02, CH_03,CH_04, CH_05,CH_06,CH_07,CH_08,CH_09,CH_10,CH_11,CH_12,CH_13,CH_14,CH_15,CH_16,CH_17,CH_18,CH_19,CH_20]
  x_name: TBB
  y_name: TBB
  x_unit: 'K'
  y_unit: 'K'
  x_range: [200-320, 200-320, 200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300]
  y_range: [200-320, 200-320, 200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300,200-300]
  slope_range: [0-2, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02, 0.98-1.02]
  days: 2  # 针对文件日期
  time: [all, day, night] # 针对某一天的时间段
  reference: # each channel has a reference list  长时间序列要计算偏差的物理量是什么
    - [220,]
    - [220,]
    - [220,]
    - [220,]
    - [230,]
    - [240,]
    - [250,]
    - [260,]
    - [260,]
    - [240,]
    - [250,]
    - [250,]
    - [230,]
    - [250,]
    - [240,]
    - [230,]
    - [230,]
    - [250,]
    - [260,]
    - [260,]
