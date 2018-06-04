sensor1: VIRR
sensor2: IASI

##########日匹配结果的分布图 ###############
collocation_map:
  chan: [CH_03,CH_04,CH_05]
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
  chan: [CH_03,CH_04,CH_05]
  x_name: Radiance
  y_name: Radiance
  x_unit: 'mw/m^2/sr/cm^{-1}'
  y_unit: 'mw/m^2/sr/cm^{-1}'
  x_range: [0-1, 0-140, 0-140]
  y_range: [0-1, 0-140, 0-140]
  slope_range: [0.98-1.02, 0.98-1.02, 0.98-1.02]
  days: 1  # 针对当前日期向前滚动天数
  time: [all, day, night] # 针对某一天的时间段

tbb-tbb:
  chan: [CH_03,CH_04,CH_05]
  x_name: TBB
  y_name: TBB
  x_unit: 'K'
  y_unit: 'K'
  x_range: [180-300, 180-300, 180-280]
  y_range: [180-300, 180-300, 180-280]
  slope_range: [0.98-1.02, 0.98-1.02, 0.98-1.02]
  days: 1  # 针对文件日期
  time: [all, day, night] # 针对某一天的时间段
  reference: # each channel has a reference list  长时间序列要计算偏差的物理量是什么
    - [250,]
    - [250,]
    - [250,]
