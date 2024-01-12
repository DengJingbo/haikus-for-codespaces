# ///////////////////////////////////////////////////////////////
# 主程序
# 用于连接界面控件和相应的槽函数
# 
# ///////////////////////////////////////////////////////////////
import sys
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
sys.path.append(BASE_DIR) 
# IMPORT / GUI AND MODULES AND WIDGETS
# ///////////////////////////////////////////////////////////////
import numpy as np
from time import *
from config.address_read import *
from data_manager.data_manager import *
from data_manager.plc_base import plc_base
from data_manager.sim_base import sim_base
from gui.UI_MainWindow import *
from gui.control_pannel import *
from gui.control_validation import *
from gui.data_monitor import *
from gui.debug_pannel import *
from gui.draw_pannel import *
from gui.log_terminal import *
from gui.sim_pannel import *
from gui.system_connection import *
from middle_interface.cutter_ctrl_interface import *
from middle_interface.thrust_ctrl_interface import *
from middle_interface.conveyer_ctrl_interface import *
from middle_interface.foam_ctrl_interface import *
from middle_interface.sim_ctrl_interface import *
from top_controller.controller1 import *
from top_controller.controller1_1 import *
from top_controller.controller2 import *
from top_controller.controller3 import *
from top_controller.controller3_1 import *
from top_controller.controller4 import *
from top_controller.controller4_1 import *
from top_controller.controller4_2 import *
os.environ["QT_FONT_DPI"] = "196" # FIX Problem for High DPI and Scale above 100%


# 数据刷新周期，单位ms
UI_Refresh_Period = 200
simData_Refresh_Period = 100
# 系统状态刷新周期
Cutter_Refresh_Period = 300
Sys_Sta_Refresh_Period = 500
visualSync_Refresh_Period = 500    
# 目标PLC的地址: str
target_plc_host = get_yaml_data("./StmCtrl_GUI/config/default_stm_config.yaml")['默认PLC地址']
# 报警阈值配置文件
alarm_parameters_file = "./StmCtrl_GUI/config/alarm_parameters.yaml"
# SET AS GLOBAL WIDGETS
def get_dpi_scale_factor():
        # """获取真实的分辨率"""
        hDC = win32gui.GetDC(0)
        # 横向分辨率
        w = win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES)
        # 等效屏幕横向像素个数
        w_scaled = 2160
        scale_factor = round(w/w_scaled, 2)
        if scale_factor<1:
            scale_factor = 1
        return scale_factor

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        # QMainWindow.__init__(self)
        super(MainWindow, self).__init__()
        # 当前日期时间
        self.datetime = QtCore.QDateTime()
        # 创建滤波器缓存数据词典
        self.filter_dict = {}
        self.start_time =  time.time()
        # SET AS GLOBAL WIDGETS
        # ///////////////////////////////////////////////////////////////
        # 创建底层对象
        self.data_manager = data_manager()
        # 创建各状态对象
        self.sys_sta = sysStatus()
        # print(time.time() - self.start_time)
        self.ui = Ui_MainWindow()
        # print(time.time() - self.start_time)
        # # 刀盘系统状态
        # self.cutter_sta = cutter_status()
        # # 推进系统状态
        # self.thrust_sta = thrust_status()
        # # 螺机系统状态
        # self.conveyer_sta = conveyer_status()
        # self.guide_sta = guide_status()
        # USE CUSTOM TITLE BAR | USE AS "False" FOR MAC OR LINUX
        # ///////////////////////////////////////////////////////////////
        # 创建中层控制接口对象
        self.stm_ctrl = sim_ctrl_interface()
        self.thrust_ctrl = thrust_ctrl_interface(self.ui.consolo, self.stm_ctrl)
        self.cutter_ctrl = cutter_ctrl_interface(self.ui.consolo, self.stm_ctrl)
        self.conveyer_ctrl = conveyer_ctrl_interface(self.ui.consolo, self.stm_ctrl)
        self.foam_ctrl = foam_ctrl_interface(self.ui.consolo)


        self.alarm_params = get_yaml_data(alarm_parameters_file)
        self.ui.aps_widget.updateParamList(self.alarm_params)
        self.ui.aps_widget.updateParamList(self.alarm_params)
        
        self.driver = controller3()
        self.ui.cps_widget.updateParamList(self.driver.parm)
        self.ui.cps_widget.updateParamList(self.driver.parm)
        self.ui.cps_widget_2.updateParamList(self.driver.parm)
        self.ui.cps_widget_2.updateParamList(self.driver.parm)
        
        self.ui.dockAttitudeWidget.mannuelCtrlPannel.enableTotalCtrl(False)

        # 设置窗口主题
        QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create('Fusion'))
        self.ui.connectBar.clicked.connect(self.connectBtnClicked)
        
        # 参数管理窗口的相关信号连接
        self.connect(self.ui.cps_widget , QtCore.SIGNAL("readParamsClicked()"), lambda: self.read_params_callack())
        self.connect(self.ui.cps_widget , QtCore.SIGNAL("writeParamsClicked()"),lambda: self.write_params_callack())
        self.connect(self.ui.cps_widget_2 , QtCore.SIGNAL("readParamsClicked()"), lambda: self.read_params_callack())
        self.connect(self.ui.cps_widget_2 , QtCore.SIGNAL("writeParamsClicked()"),lambda: self.write_params_callack())

        # 报警阈值管理窗口的相关信号连接
        self.connect(self.ui.aps_widget , QtCore.SIGNAL("ReadAlarmParamsClicked()"), lambda: self.read_alarm_params_callack())
        self.connect(self.ui.aps_widget , QtCore.SIGNAL("WriteAlarmParamsClicked()"),lambda: self.write_alarm_params_callack())
        
        # 绘图管理窗口相关信号连接
        # 使用按钮的点击事件需要传递参数时用到lambda表达式，添加绘图/删除绘图
        self.connect(self.ui.dockPlotCtrlWidget, QtCore.SIGNAL("addClicked()"), lambda: self.ui.dockPlotCtrlWidget.addPlot2Pw(pw = self.ui.pwidget))
        self.connect(self.ui.dockPlotCtrlWidget, QtCore.SIGNAL("delClicked()"), lambda: self.ui.dockPlotCtrlWidget.deletePlot(pw = self.ui.pwidget))
        # 绘图背景颜色更改，绘图增加删除数据曲线触发信号连接
        self.ui.dockPlotCtrlWidget.colorChanged[str].connect(self.ui.pwidget.setBackgroundColor)
        self.ui.dockPlotCtrlWidget.gridColorChanged[str].connect(self.ui.pwidget.setGridColor)
        self.ui.dockPlotCtrlWidget.legendColorChanged[str].connect(self.ui.pwidget.setLegendColor)
        self.ui.dockPlotCtrlWidget.gridChange[int].connect(self.ui.pwidget.setGrid)

        self.ui.dockPlotCtrlWidget.addCurveTriggered[str].connect(lambda key: self.ui.dockPlotCtrlWidget.addCurve2Plot(curve = key, pw = self.ui.pwidget))
        self.ui.dockPlotCtrlWidget.delCurveTriggered[str].connect(lambda key: self.ui.dockPlotCtrlWidget.delCurvefromPlot(curve = key,pw = self.ui.pwidget))

        # self.connect(self.ui.connectBar2 , QtCore.SIGNAL("simConnectClicked()"), lambda: self.visualSystemConnect())
        # 仿真控制相关信号连接
        # 仿真速度设置按钮绑定函数
        self.connect(self.ui.dockSimControlWidget, QtCore.SIGNAL("simSpeedClicked()"), lambda: self.stm_ctrl.sim_speed_set(int(self.ui.dockSimControlWidget.simSpeedCtrl.spinBox.value()), self.data_manager))
        self.connect(self.ui.dockSimControlWidget, QtCore.SIGNAL("stateShiftClicked()"), lambda: self.stm_ctrl.stm_state_set(self.data_manager))

        self.connect(self.ui.dockSimControlWidget, QtCore.SIGNAL("targetMClicked()"), lambda: self.stm_ctrl.stm_position_set( int(self.ui.dockSimControlWidget.simthrustMode.spinBox.value()),float(self.ui.dockSimControlWidget.simthrustMode.herrorBox.toPlainText()),float(self.ui.dockSimControlWidget.simthrustMode.verrorBox.toPlainText()), self.data_manager))
        self.connect(self.ui.dockSimControlWidget, QtCore.SIGNAL("forceVisualClicked()"), lambda: self.stm_ctrl.simenv_force_show(self.data_manager))
        self.connect(self.ui.dockSimControlWidget, QtCore.SIGNAL("dtaVisualClicked()"), lambda: self.stm_ctrl.simenv_dta_show(self.data_manager))

        # 推进系统控制相关信号连接        
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("startClicked()"), lambda: self.thrust_ctrl.thrust_switch(self.thrust_ctrl.thrust_sta.start, self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("segModeClicked()"), lambda: self.thrust_ctrl.thrust_segmode_set(self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("segInstallClicked()"), lambda: self.stm_ctrl.seg_install(self.data_manager))
        
        # self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("executeClicked()"), lambda: self.mode2TaskExecute())
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("autoControlClicked()"), lambda: self.modeTaskExecute())

        # 刀盘系统相关信号连接
        # self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterStartClicked()"), lambda: self.cutter_ctrl.cutter_switch(self.cutter_ctrl.cutter_sta.start, self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterStartClicked()"), lambda: self.cutter_switch())
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("autoCutterStartClicked()"), lambda: self.cutter_switch())
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterDirClicked()"), lambda: self.cutter_ctrl.cutter_dir_set(dir = 'right', data_manager = self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterVelClicked()"), lambda: self.cutter_ctrl.cutter_vel_mode_set(vel = 'low', data_manager = self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterDirLeftClicked()"), lambda: self.cutter_ctrl.cutter_dir_set(dir = 'left', data_manager = self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterVelRapidClicked()"), lambda: self.cutter_ctrl.cutter_vel_mode_set(vel = 'rapid', data_manager = self.data_manager))
        
        self.ui.dockAttitudeWidget.cutterVelChanged[int].connect(lambda vel: self.cutter_ctrl.cutter_velocity_set(float(vel), self.data_manager))

        # 螺机系统相关信号连接
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("conveyerStartClicked()"), lambda: self.conveyer_ctrl.conveyer_switch(self.conveyer_ctrl.conveyer_sta.start, self.data_manager))
        # self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("conveyerDirClicked()"),   lambda: self.conveyer_dir_set(self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("conveyerVelClicked()"),   lambda: self.conveyer_ctrl.conveyer_vel_mode_set(self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("conveyerModeClicked()"),   lambda: self.conveyer_ctrl.conveyer_pressure_mode_set(self.data_manager))
        self.ui.dockAttitudeWidget.conveyerVelChanged[int].connect(lambda vel: self.conveyer_ctrl.conveyer_velocity_set(float(vel), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("conveyerUpperValveOpenClicked()"), lambda: self.conveyer_ctrl.conveyer_Valve_set('Upper','Open',self.conveyer_ctrl.conveyer_sta.scm_open, self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("conveyerUpperValveCloseClicked()"), lambda: self.conveyer_ctrl.conveyer_Valve_set('Upper','Close',self.conveyer_ctrl.conveyer_sta.scm_close, self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("conveyerLowerValveOpenClicked()"), lambda: self.conveyer_ctrl.conveyer_Valve_set('Lower','Open',self.conveyer_ctrl.conveyer_sta.xcm_open, self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("conveyerLowerValveCloseClicked()"), lambda: self.conveyer_ctrl.conveyer_Valve_set('Lower','Close',self.conveyer_ctrl.conveyer_sta.xcm_close, self.data_manager))
        self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("conveyerSpeedChanged(double)"), lambda speed: self.conveyer_ctrl.conveyer_lower_pressure_speed_set(float(speed), self.conveyer_ctrl, self.data_manager))

        
        # 急停等按钮信号连接，电机急停按钮，调出确认框，确认是否执行急停指令，防止误触。
        # self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("stopAllClicked()"), lambda: self.stop_all_process())
        # self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("ctrlAllConfirmClicked()"), lambda: self.controlConfirm(3))
        # self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("ctrlModeClicked()"), lambda: self.controlModeSwitch())

        self.ui.dockAttitudeWidget.aForceChanged[int].connect(lambda force: self.thrust_ctrl.thrust_force_set(0, float(force), self.data_manager))
        self.ui.dockAttitudeWidget.bForceChanged[int].connect(lambda force: self.thrust_ctrl.thrust_force_set(1, float(force), self.data_manager))
        self.ui.dockAttitudeWidget.cForceChanged[int].connect(lambda force: self.thrust_ctrl.thrust_force_set(2, float(force), self.data_manager))
        self.ui.dockAttitudeWidget.dForceChanged[int].connect(lambda force: self.thrust_ctrl.thrust_force_set(3, float(force), self.data_manager))
        self.ui.dockAttitudeWidget.AVelChanged[int].connect(lambda vel: self.thrust_ctrl.thrust_velocity_set(float(vel), self.data_manager))
        
        self.ui.dockAttitudeWidget.acForceChanged[int].connect(lambda force: self.base_force_set(0, float(force)))
        self.ui.dockAttitudeWidget.bdForceChanged[int].connect(lambda force: self.base_force_set(1, float(force)))

        # 刀盘喷水等信号连接
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterPs1Clicked()"), lambda: self.foam_ctrl.spray_switch(0, not(self.foam_ctrl.spray_sta.spray_start1), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterPs2Clicked()"), lambda: self.foam_ctrl.spray_switch(1, not(self.foam_ctrl.spray_sta.spray_start2), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterPs3Clicked()"), lambda: self.foam_ctrl.spray_switch(2, not(self.foam_ctrl.spray_sta.spray_start3), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterPs4Clicked()"), lambda: self.foam_ctrl.spray_switch(3, not(self.foam_ctrl.spray_sta.spray_start4), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterPs5Clicked()"), lambda: self.foam_ctrl.spray_switch(4, not(self.foam_ctrl.spray_sta.spray_start5), self.data_manager))
        # 搅拌棒喷水按钮按下
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterJbbClicked()"), lambda: self.foam_ctrl.jbbPattern_switch(self.foam_ctrl.spray_sta, self.data_manager))
        # 出渣口喷水按钮按下
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterCzkClicked()"), lambda: self.foam_ctrl.czkPattern_switch(self.foam_ctrl.spray_sta, self.data_manager))
        # 循环喷水按钮按下
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("cutterXhpsClicked()"), lambda: self.foam_ctrl.sprayCirculation_switch(self.foam_ctrl.spray_sta, self.data_manager))

        # 泡沫系统等信号连接
        # 泡沫系统开关按下
        # self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("foamSwitchClicked()"),)
        # 泡沫系统手动开关按下
        self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("foammanualClicked()"), lambda: self.foam_manual_switch(self.data_manager))
        # 泡沫系统半自动开关按下
        self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("foamSemiAutoClicked()"), lambda: self.foam_semi_auto_switch(self.data_manager))
        # 泡沫系统自动开关被按下,暂时不用
        # self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("foamAutoClicked()"), lambda: self.foam_ctrl.foam_mode_set((not self.foam_ctrl.foam_sta.mode2), self.data_manager))
        # self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("foamRemainClicked()"), QtCore.SIGNAL("foamRemainClicked()"))
        self.ui.dockAttitudeWidget.liquid1Changed[int].connect(lambda flow: self.foam_ctrl.foam_flow_set(0, float(flow), self.data_manager))
        self.ui.dockAttitudeWidget.liquid2Changed[int].connect(lambda flow: self.foam_ctrl.foam_flow_set(1, float(flow), self.data_manager))
        self.ui.dockAttitudeWidget.liquid3Changed[int].connect(lambda flow: self.foam_ctrl.foam_flow_set(2, float(flow), self.data_manager))
        self.ui.dockAttitudeWidget.liquid4Changed[int].connect(lambda flow: self.foam_ctrl.foam_flow_set(3, float(flow), self.data_manager))
        self.ui.dockAttitudeWidget.liquid5Changed[int].connect(lambda flow: self.foam_ctrl.foam_flow_set(4, float(flow), self.data_manager))
        self.ui.dockAttitudeWidget.liquid6Changed[int].connect(lambda flow: self.foam_ctrl.foam_flow_set(5, float(flow), self.data_manager))

        self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("expa1Changed(double)"), lambda rate: self.foam_ctrl.foam_swellrate_set(0, float(rate), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("expa2Changed(double)"), lambda rate: self.foam_ctrl.foam_swellrate_set(1, float(rate), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("expa3Changed(double)"), lambda rate: self.foam_ctrl.foam_swellrate_set(2, float(rate), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("expa4Changed(double)"), lambda rate: self.foam_ctrl.foam_swellrate_set(3, float(rate), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("expa5Changed(double)"), lambda rate: self.foam_ctrl.foam_swellrate_set(4, float(rate), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget, QtCore.SIGNAL("expa6Changed(double)"), lambda rate: self.foam_ctrl.foam_swellrate_set(5, float(rate), self.data_manager))
        
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("foamSwitch1Clicked()"), lambda: self.foam_ctrl.foam_loop_switch(0, not(self.foam_ctrl.foam_sta.foam_start1), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("foamSwitch2Clicked()"), lambda: self.foam_ctrl.foam_loop_switch(1, not(self.foam_ctrl.foam_sta.foam_start2), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("foamSwitch3Clicked()"), lambda: self.foam_ctrl.foam_loop_switch(2, not(self.foam_ctrl.foam_sta.foam_start3), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("foamSwitch4Clicked()"), lambda: self.foam_ctrl.foam_loop_switch(3, not(self.foam_ctrl.foam_sta.foam_start4), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("foamSwitch5Clicked()"), lambda: self.foam_ctrl.foam_loop_switch(4, not(self.foam_ctrl.foam_sta.foam_start5), self.data_manager))
        self.connect(self.ui.dockAttitudeWidget , QtCore.SIGNAL("foamSwitch6Clicked()"), lambda: self.foam_ctrl.foam_loop_switch(5, not(self.foam_ctrl.foam_sta.foam_start6), self.data_manager))


        # 现场调试相关信号连接
        self.connect(self.ui.dockFeildDebugWidget , QtCore.SIGNAL("readClicked()"), lambda: self.readDataTest())
        self.connect(self.ui.dockFeildDebugWidget , QtCore.SIGNAL("writeClicked()"), lambda: self.writeDataTest())        
        
        # 创建定时器2，定时刷新界面
        self.UiRefreshTimer = QtCore.QTimer()
        self.UiRefreshTimer.start(UI_Refresh_Period)
        self.UiRefreshTimer.timeout.connect(self.uiRefresh)

        # 创建系统状态刷新定时器
        self.SysStaRefreshTimer = QtCore.QTimer()
        self.SysStaRefreshTimer.start(Sys_Sta_Refresh_Period)
        self.SysStaRefreshTimer.timeout.connect(self.statusUpdate)
        
        # 创建刀盘旋转定时器
        self.CutterStaRefreshTimer = QtCore.QTimer()
        self.CutterStaRefreshTimer.start(Cutter_Refresh_Period)
        self.CutterStaRefreshTimer.timeout.connect(self.cutterRotationUpdate)
        # print(time.time() - self.start_time)

    # 盾构姿态自动控制软件连接/断开
    def connectBtnClicked(self):
        # 处于未连接状态时,连接
        if self.data_manager.connect_status == 0:
            self.ui.consolo.log_operation("连接按钮被按下")
            # 判断连接仿真系统还是PLC
            # 连接仿真
            if self.ui.connectBar.objCombo.currentText() == "仿真":
                # print(self.ui.connectBar.ipEdit.toPlainText(),int(self.ui.connectBar.portEdit.toPlainText()))
                # self.data_manager.connect_to_target(1, target_plc_host)
                self.data_manager.connect_to_target(1, 'localhost')
                print("连接仿真后connect_status状态:"+str(self.data_manager.connect_status))
            # 连接PLC
            elif self.ui.connectBar.objCombo.currentText() == "PLC":
                self.ui.connectBar.ipEdit.setText(target_plc_host)
                self.data_manager.connect_to_target(0, target_plc_host)
                print("连接PLC后connect_status状态:"+str(self.data_manager.connect_status))
            else:
                pass
            
            # 判断是否连接成功
            if self.data_manager.connect_status != 0:
                # 创建数据对象
                self.sys_data = self.data_manager.data_buffer
                # self.sys_sta.connectedTime = time()
                self.ui.dockPlotCtrlWidget.updataComboBoxData(self.data_manager)
                self.ui.connectBar.setAllDisabled()
                self.ui.connectBar.connectBtn.setText('断 开')
                
                # 显示数据
                self.ui.dockDataShowWidget.showSysData(self.sys_data, self.data_manager._address_def)
                # self.dockAttitudeWidget.mannuelCtrlPannel.dialValueSyn(sys_sta = self.sys_sta, thrust_sta=self.plc_sim.thrust_sta)
                self.ui.dockSimControlWidget.setEnabled(True)
        # 当处于连接状态时,断开连接
        else:
            self.ui.consolo.log_operation("断开连接按钮被按下")
            self.data_manager.disconnect()

            self.data_manager.connect_status = 0
            self.ui.connectBar.objChanged()
            self.ui.connectBar.connectBtn.setText('连 接')
            self.ui.dockSimControlWidget.setEnabled(False)
            # self.ui.dockErrorPlot.setVisible(True)
            # 删除默认绘图
            self.ui.dockPlotCtrlWidget.deleteAllPlot(self.ui.pwidget)
            # 更新状态栏显示状态
            self.ui.permit_dispc.setDisabled(True)
            self.ui.permit_disp.setText('推进未授权')

            self.ui.cutter_permit_dispc.setDisabled(True)
            self.ui.cutter_permit_disp.setText('刀盘系统未授权')
                    
            self.ui.conveyer_permit_dispc.setDisabled(True)
            self.ui.conveyer_permit_disp.setText('螺机系统未授权')
            
            # 归位自动控制器相关组件
            self.driver.sta.executing = False
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.btn2.setText("停止")
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.btn2.setBlue()
            # 启用相关组件
            self.ui.dockAttitudeWidget.ctrlMethodBox.setEnabled(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterDirBtn.setEnabled(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterDirLeftBtn.setEnabled(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterVelBtn.setEnabled(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterVelRapidBtn.setEnabled(True)
            
    # 现场测试：读操作
    def readDataTest(self):
        # 当未连接时，连接状态为0；连接上真机时，连接状态为1；连接上仿真系统时，连接状态为2；
        # 当连接上系统时
        if self.data_manager.connect_status == 1 or self.data_manager.connect_status == 2:
            target_address_str = self.ui.dockFeildDebugWidget.targetAddress.toPlainText().split('.')
            target_address = []
            self.ui.consolo.log_operation("读地址测试")
            for i in range(0, len(target_address_str)):
                target_address.append( int(target_address_str[i]))
            try:
                if len(target_address_str) ==2:
                    data = self.data_manager.read_data_from_addr(target_address, 'real')    
                else:
                    data = self.data_manager.read_data_from_addr(target_address, 'bool')   
            except Exception:
                readErrorDialog = QtWidgets.QMessageBox()
                self.ui.consolo.log_error("读数据错误, 请检查读地址格式是否正确!")
                readErrorDialog.about(self, '读错误', '请检查读地址格式是否正确,格式(xxx.xx.x)"')
                readErrorDialog.show()
                return False
            else:
                self.ui.dockFeildDebugWidget.readResult.setText(str(data))
                return True
        else:
            pass
        
    # 现场测试：写操作
    def writeDataTest(self):
        # 当未连接时，连接状态为0；连接上真机时，连接状态为1；连接上仿真系统时，连接状态为2；
        # 当连接上系统时
        if self.data_manager.connect_status == 1 or self.data_manager.connect_status == 2:
            target_address_str = self.ui.dockFeildDebugWidget.targetAddress.toPlainText().split('.')
            target_address = []
            self.ui.consolo.log_operation("写地址测试")
            for i in range(0, len(target_address_str)):
                target_address.append( int(target_address_str[i]))

            data = float(self.ui.dockFeildDebugWidget.dataIn.toPlainText())
            try:
                if len(target_address_str) ==2:
                    data = self.data_manager.write_data_from_addr(target_address, data, 'real')    
                else:
                    data = self.data_manager.write_data_from_addr(target_address, data, 'bool')  
            except Exception:
                writeErrorDialog = QtWidgets.QMessageBox()
                self.ui.consolo.log_error("写数据操作错误,请见差写地址格式是否正确,格式(xxx.xx.x)")
                writeErrorDialog.about(self, '写错误', '请检查写地址格式是否正确')
                writeErrorDialog.show()
                return False
            else:
                self.readDataTest()
                return True
        else:
            pass

    def read_params_callack(self):
        self.ui.cps_widget.updateParamList(self.driver.parm)
        self.ui.cps_widget_2.updateParamList(self.driver.parm)
        self.ui.consolo.log_operation('成功读到控制器参数！')

    def write_params_callack(self):
        res = self.ui.cps_widget.updateParamsDictFromTable(self.driver.parm)
        res = self.ui.cps_widget_2.updateParamsDictFromTable(self.driver.parm)
        if res ==True:
            # 保存配置文件
            address_file = self.driver.parm_path
            with open(address_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.driver.parm, f, allow_unicode=True, sort_keys=False)    #将Python中的字典或者列表转化为yaml格式的数据
                f.close()
            
            current_path = os.path.abspath(".")
            parm_filename = str(self.thrust_ctrl.guide_sta.h1) + time.strftime("_%Y_%m_%d_%H_%M_%S", time.localtime())+'.yaml'
            total_parm_filename = os.path.join(current_path, './StmCtrl_GUI/data/params_record/'+ parm_filename)
            with open(total_parm_filename, 'w', encoding='utf-8') as f:
                yaml.dump(self.driver.parm, f, allow_unicode=True, sort_keys=False)    #将Python中的字典或者列表转化为yaml格式的数据
                f.close()
            self.ui.consolo.log_operation('成功写入控制器参数！')
        else:
            self.ui.consolo.log_warning('写入失败，当前控制器参数中数据格式有误！')

    def read_alarm_params_callack(self):
        self.ui.aps_widget.updateParamList(self.alarm_params)
        self.ui.consolo.log_operation('成功读到报警阈值参数！')

    def write_alarm_params_callack(self):
        res = self.ui.aps_widget.updateParamsDictFromTable(self.alarm_params)
        if res ==True:
            # 保存配置文件
            address_file = alarm_parameters_file
            with open(address_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.alarm_params, f, allow_unicode=True, sort_keys=False)    #将Python中的字典或者列表转化为yaml格式的数据
                f.close()
            
            current_path = os.path.abspath(".")
            parm_filename = str(self.thrust_ctrl.guide_sta.h1) + time.strftime("_%Y_%m_%d_%H_%M_%S", time.localtime())+'.yaml'
            total_parm_filename = os.path.join(current_path, './StmCtrl_GUI/data/alarm_params_record/'+ parm_filename)
            with open(total_parm_filename, 'w', encoding='utf-8') as f:
                yaml.dump(self.driver.parm, f, allow_unicode=True, sort_keys=False)    #将Python中的字典或者列表转化为yaml格式的数据
                f.close()
            self.ui.consolo.log_operation('成功写入报警阈值参数！')
        else:
            self.ui.consolo.log_warning('写入失败，当前报警阈值参数中数据格式有误！')

    def base_force_set(self, base_object:int, base_force:float):
        if base_object == 0:
            self.driver.sta.ac_total_pressure_adjust = base_force
        elif base_object == 1:
            self.driver.sta.bd_total_pressure_adjust = base_force
        
    # 急停按钮处理流程
    # 打开确认对话框，点击yes确认执行。急停完成后，终止自主控制流程
    def stop_all_process(self):
        self.ui.consolo.log_operation("急停按钮被按下")
        # 当连接上系统时
        if self.data_manager.connect_status == 1 or self.data_manager.connect_status == 2:
            cutter_switch = self.cutter_ctrl.cutter_sta.start
            thrust_switch = self.thrust_ctrl.thrust_sta.start
            conveyer_switch = self.conveyer_ctrl.conveyer_sta.start
            #  弹出急停确认窗口
            choice = QtWidgets.QMessageBox.question(self, '确认', '确认急停?')
            if choice == QtWidgets.QMessageBox.Yes:
                self.ui.consolo.log_operation("系统急停")
                if cutter_switch==1:
                    self.cutter_ctrl.cutter_switch(cutter_switch, self.data_manager)  
                if thrust_switch==1:
                    self.thrust_ctrl.thrust_switch(thrust_switch, self.data_manager)
                if conveyer_switch==1:
                    self.conveyer_ctrl.conveyer_switch(conveyer_switch, self.data_manager)
                # 结束自动控制过程。
                self.driver.stopControl()
            elif choice == QtWidgets.QMessageBox.No:
                return
        else:
            return
            
    # 启动/关闭自动控制器
    def modeTaskExecute(self)->None:
        if self.driver.sta.executing==True:
            choice = QtWidgets.QMessageBox.question(self, '确认', '确认关闭自动控制?')
        else:
            choice = QtWidgets.QMessageBox.question(self, '确认', '确认开启自动控制?')

        if choice == QtWidgets.QMessageBox.Yes:
            self.mode2TaskExecute()
        else:
            pass

    # 执行自动运行的任务
    # 自动控制模式
    def mode2TaskExecute(self)->None:
        if self.driver.sta.executing==True:
            self.driver.sta.executing=False
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.btn2.setText("停止")
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.btn2.setBlue()
            # 启用相关组件
            self.ui.dockAttitudeWidget.ctrlMethodBox.setEnabled(True)
            
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterDirBtn.setEnabled(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterDirLeftBtn.setEnabled(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterVelBtn.setEnabled(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterVelRapidBtn.setEnabled(True)
            
            # 连接槽函数
            self.ui.dockAttitudeWidget.aForceChanged[int].connect(lambda force: self.thrust_ctrl.thrust_force_set(0, float(force), self.data_manager))
            self.ui.dockAttitudeWidget.bForceChanged[int].connect(lambda force: self.thrust_ctrl.thrust_force_set(1, float(force), self.data_manager))
            self.ui.dockAttitudeWidget.cForceChanged[int].connect(lambda force: self.thrust_ctrl.thrust_force_set(2, float(force), self.data_manager))
            self.ui.dockAttitudeWidget.dForceChanged[int].connect(lambda force: self.thrust_ctrl.thrust_force_set(3, float(force), self.data_manager))
            self.ui.dockAttitudeWidget.conveyerVelChanged[int].connect(lambda vel: self.conveyer_ctrl.conveyer_velocity_set(float(vel), self.data_manager))

            self.ui.dockAttitudeWidget.mannuelCtrlPannel.enableMannulCtrl(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.enableTotalCtrl(False)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.conveyerModeBtn.setEnabled(False)
            self.ui.consolo.log_operation("停止自动控制程序")
        else:
            
            # 自动控制执行时初始化控制器
            if self.ui.dockAttitudeWidget.ctrlMethodBox.currentText() == '自动控制策略A':
                self.driver = controller1()
            elif self.ui.dockAttitudeWidget.ctrlMethodBox.currentText() == '自动控制策略A_1':
                self.driver = controller1_1()
            elif self.ui.dockAttitudeWidget.ctrlMethodBox.currentText() == '自动控制策略B':
                self.driver = controller2()
            elif self.ui.dockAttitudeWidget.ctrlMethodBox.currentText() == '自动控制策略C':
                self.driver = controller3()
            elif self.ui.dockAttitudeWidget.ctrlMethodBox.currentText() == '自动控制策略C_1':
                self.driver = controller3_1()
            elif self.ui.dockAttitudeWidget.ctrlMethodBox.currentText() == '自动控制策略D':
                self.driver = controller4()
            elif self.ui.dockAttitudeWidget.ctrlMethodBox.currentText() == '自动控制策略D_1':
                self.driver = controller4_1()
            elif self.ui.dockAttitudeWidget.ctrlMethodBox.currentText() == '自动控制策略D_2':
                self.driver = controller4_2()
            else:
                pass
      
            # 自动控制执行时禁用控制器选择框
            self.driver.sta.executing=True
            
            self.driver.controlInit(self.ui.dockAttitudeWidget, self)
            self.ui.consolo.log_operation("启动自动控制程序")
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.btn2.setText("运行")
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.btn2.setGreen()
            # 断联槽函数
            self.ui.dockAttitudeWidget.aForceChanged[int].disconnect()
            self.ui.dockAttitudeWidget.bForceChanged[int].disconnect()
            self.ui.dockAttitudeWidget.cForceChanged[int].disconnect()
            self.ui.dockAttitudeWidget.dForceChanged[int].disconnect()
            self.ui.dockAttitudeWidget.conveyerVelChanged[int].disconnect()

            # 刷新参数表
            self.ui.cps_widget.updateParamList(self.driver.parm)
            self.ui.cps_widget_2.updateParamList(self.driver.parm)
            
            # 禁用相关组件
            self.ui.dockAttitudeWidget.ctrlMethodBox.setEnabled(False)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterDirBtn.setEnabled(False)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterDirLeftBtn.setEnabled(False)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterVelBtn.setEnabled(False)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.cutterVelRapidBtn.setEnabled(False)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.enableMannulCtrl(False)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.enableTotalCtrl(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.conveyerModeBtn.setEnabled(True)

            

    # =====================================================================
    # 刀盘开关启动流程
    def cutter_switch(self):
        switch = self.cutter_ctrl.cutter_sta.start
        # 如果自动驾驶程序未执行
        if self.driver.sta.executing == False:
            self.cutter_ctrl.cutter_switch(switch, self.data_manager)
        # 如果自动驾驶程序已执行
        else:
            # 如果未打开刀盘，启动刀盘的自动启动流程
            if switch == 0:
                self.driver.sta.cutter_stop_triggered = 0
                # 执行过程中单步超时时间
                self.cutter_switch_timeout_period = 5000
                self.cutter_switch_scan_period = 200
                # 第二步, 设定刀盘挡位, 每200ms检测一次是否设置成功
                self.cutter_ctrl.cutter_vel_mode_set('low', self.data_manager)
                self.cutter_gears_timer = QtCore.QTimer()
                self.cutter_gears_timer.start(200)
                self.cutter_gears_timer.timeout.connect(lambda: self.cutter_gears_auto_set_dectect())
            # 如果已经打开了刀盘，启动刀盘的自动停止流程
            else:
                # 执行过程中单步超时时间,20s后检测刀盘速度设定速度是否为0
                self.cutter_switch_timeout_period = 20000
                self.cutter_switch_scan_period = 500
                # 第一步, 判断推进是否关闭，只有推进系统关闭才可以启动刀盘自动关闭的流程
                if self.thrust_ctrl.thrust_sta.start == 0:
                    self.driver.sta.cutter_stop_triggered = 1
                    self.cutter_stop_timer = QtCore.QTimer()
                    self.cutter_stop_timer.start(500)
                    self.cutter_stop_timer.timeout.connect(lambda: self.cutter_auto_stop_dectect())
                else:
                    # 报错
                    self.ui.consolo.log_warning("请先关闭推进系统！")
                    errorDialog = QtWidgets.QMessageBox()
                    errorDialog.about(self, '警告', '请先关闭推进系统！')
                    errorDialog.show()
            
                
    def cutter_gears_auto_set_dectect(self):
        # self.cutter_gears_timer.stop()
        self.cutter_switch_timeout_period = self.cutter_switch_timeout_period - self.cutter_switch_scan_period
        gears_set_res = self.cutter_ctrl.cutter_sta.cutter_low
        # 超时未设置刀盘挡位
        if(self.cutter_switch_timeout_period<=0 and (not gears_set_res)):
            # 报错
            self.ui.consolo.log_warning("刀盘挡位设置失败！")
            gearsSetErrorDialog = QtWidgets.QMessageBox()
            gearsSetErrorDialog.about(self, '警告', '刀盘挡位设置失败！')
            gearsSetErrorDialog.show()
            
            self.cutter_gears_timer.stop()
        else:
            # 刀盘挡位成功设置，则设置刀盘方向，启动刀盘方向设置
            if gears_set_res==1:
                self.cutter_switch_timeout_period = 5000
                # 第二步, 设定刀盘方向, 每200ms检测一次是否设置成功
                if self.driver.parm['掘进参数']['刀盘正转'] == 0:
                    if self.driver.sta.cutter_target_dir == '正':
                        desired_dir = 'right'
                    else:
                        desired_dir = 'left'
                else:
                    if self.driver.sta.cutter_target_dir == '正':
                        desired_dir = 'left'
                    else:
                        desired_dir = 'right'
                    
                self.cutter_ctrl.cutter_dir_set(desired_dir, self.data_manager)
                self.cutter_dir_timer = QtCore.QTimer()
                self.cutter_dir_timer.start(200)
                self.cutter_dir_timer.timeout.connect(lambda: self.cutter_dir_auto_set_dectect())
                self.cutter_gears_timer.stop()
            else:
                pass
    
    def cutter_dir_auto_set_dectect(self):
        # self.cutter_gears_timer.stop()
        self.cutter_switch_timeout_period = self.cutter_switch_timeout_period - self.cutter_switch_scan_period
        dir_set_res = self.cutter_ctrl.cutter_sta.cutter_left or self.cutter_ctrl.cutter_sta.cutter_right
        # 超时未设置刀盘转向
        if(self.cutter_switch_timeout_period<=0 and (not dir_set_res)):
            # 报错
            self.ui.consolo.log_warning("刀盘转向设置失败！")
            dirSetErrorDialog = QtWidgets.QMessageBox()
            dirSetErrorDialog.about(self, '警告', '刀盘转向设置失败！')
            dirSetErrorDialog.show()
            
            self.cutter_dir_timer.stop()
        else:
            # 刀盘转向成功设置，则执行刀盘开关操作
            if dir_set_res==1:
                self.cutter_switch_timeout_period = 5000
                # 第三步, 启动刀盘, 每200ms检测一次是否设置成功
                self.cutter_ctrl.cutter_switch(self.cutter_ctrl.cutter_sta.start, self.data_manager)
                self.cutter_start_timer = QtCore.QTimer()
                self.cutter_start_timer.start(200)
                self.cutter_start_timer.timeout.connect(lambda: self.cutter_auto_start_dectect())
                self.cutter_dir_timer.stop()
            else:
                pass
            
    def cutter_auto_start_dectect(self):
        # self.cutter_gears_timer.stop()
        self.cutter_switch_timeout_period = self.cutter_switch_timeout_period - self.cutter_switch_scan_period
        auto_start_res = self.cutter_ctrl.cutter_sta.start
        # 超时未设置刀盘挡位
        if(self.cutter_switch_timeout_period<=0 and (not auto_start_res)):
            # 报错
            self.ui.consolo.log_warning("刀盘启动失败！")
            startErrorDialog = QtWidgets.QMessageBox()
            startErrorDialog.about(self, '警告', '刀盘启动失败！')
            startErrorDialog.show()
            
            self.cutter_start_timer.stop()
        else:
            # 刀盘启动成功，发出提示
            if auto_start_res==1:
                self.ui.consolo.log_recommond("刀盘启动成功！")
                self.cutter_start_timer.stop()
            else:
                pass
    
    def cutter_auto_stop_dectect(self):
        # self.cutter_gears_timer.stop()
        self.cutter_switch_timeout_period = self.cutter_switch_timeout_period - self.cutter_switch_scan_period
        speed_zero_res = (self.cutter_ctrl.cutter_sta.cp_speed < 1) and (self.cutter_ctrl.cutter_sta.dpzs< 0.1)
        # 超时未设置刀盘挡位
        if(self.cutter_switch_timeout_period<=0 and (not speed_zero_res)):
            # 报错
            self.ui.consolo.log_warning("刀盘速度超时未归0")
            stopErrorDialog = QtWidgets.QMessageBox()
            stopErrorDialog.about(self, '警告', '刀盘停止失败！')
            stopErrorDialog.show()
            
            self.cutter_stop_timer.stop()
        else:
            if speed_zero_res==1:
                self.cutter_switch_timeout_period = 5000
                self.cutter_ctrl.cutter_switch(self.cutter_ctrl.cutter_sta.start, self.data_manager)
                self.cutter_stop_detect_timer = QtCore.QTimer()
                self.cutter_stop_detect_timer.start(500)
                self.cutter_stop_detect_timer.timeout.connect(lambda: self.cutter_auto_stop_res_dectect())
                self.cutter_stop_timer.stop()
            else:
                pass
    
    def cutter_auto_stop_res_dectect(self):
        # self.cutter_gears_timer.stop()
        self.cutter_switch_timeout_period = self.cutter_switch_timeout_period - self.cutter_switch_scan_period
        cutter_stop_res = (not self.cutter_ctrl.cutter_sta.start)
        # 超时未设置刀盘挡位
        if(self.cutter_switch_timeout_period<=0 and (not cutter_stop_res)):
            # 报错
            self.ui.consolo.log_warning("刀盘超时未关闭，请切换手动关闭")
            stopErrorDialog = QtWidgets.QMessageBox()
            stopErrorDialog.about(self, '警告', '刀盘停止失败！')
            stopErrorDialog.show()
            
            self.cutter_stop_detect_timer.stop()
        else:
            if cutter_stop_res==1:
                self.ui.consolo.log_recommond("刀盘停止成功！")                
                self.cutter_stop_detect_timer.stop()
                self.driver.sta.cutter_stop_triggered = 0
            else:
                pass 

    # =====================================================
    # 泡沫系统手动模式启动流程
    def foam_manual_switch(self, data_manager):
        # 获取当前手动状态
        switch = self.foam_ctrl.foam_sta.mode1
        foamSwitchStatue = [self.foam_ctrl.foam_sta.foam_start1, self.foam_ctrl.foam_sta.foam_start2, self.foam_ctrl.foam_sta.foam_start3, self.foam_ctrl.foam_sta.foam_start4, self.foam_ctrl.foam_sta.foam_start5, self.foam_ctrl.foam_sta.foam_start6]
        # 如果当前手动控制状态为0，则打开
        if(switch == 0):
            # 第一步，先启动手动模式
            self.foam_ctrl.foam_mode1_set(1, data_manager)
            self.foam_pump_timeout_period = 5000
            self.foam_pump_scan_period = 200
            self.foam_pump_timer = QtCore.QTimer()
            self.foam_pump_timer.start(200)
            self.foam_pump_timer.timeout.connect(lambda: self.foam_pump_switch_set(data_manager))

        # 如果当前手动控制状态为1，则关闭
        elif(switch == 1):
            for index in range(0, len(foamSwitchStatue)):
                self.foam_ctrl.foam_pump_switch(index, 0, data_manager)
            self.foam_ctrl.foam_mode1_set(0, data_manager)

    # 泡沫系统半自动模式启动流程
    def foam_semi_auto_switch(self, data_manager):
        # 获取当前半自动状态
        switch = self.foam_ctrl.foam_sta.mode3
        foamSwitchStatue = [self.foam_ctrl.foam_sta.foam_start1, self.foam_ctrl.foam_sta.foam_start2, self.foam_ctrl.foam_sta.foam_start3, self.foam_ctrl.foam_sta.foam_start4, self.foam_ctrl.foam_sta.foam_start5, self.foam_ctrl.foam_sta.foam_start6]
        # 如果当前半自动控制状态为0，则打开
        if(switch == 0):
            # 第一步，先启动半自动模式
            self.foam_ctrl.foam_mode3_set(1, data_manager)
            self.foam_pump_timeout_period = 5000
            self.foam_pump_scan_period = 200
            self.foam_pump_timer = QtCore.QTimer()
            self.foam_pump_timer.start(200)
            self.foam_pump_timer.timeout.connect(lambda: self.foam_pump_switch_set(data_manager))
        # 如果当前半自动控制状态为1，则关闭
        elif(switch == 1):
            for index in range(0, len(foamSwitchStatue)):
                self.foam_ctrl.foam_pump_switch(index, 0, data_manager)
            self.foam_ctrl.foam_mode3_set(0, data_manager)

    # 打开泡沫系统开关
    def foam_pump_switch_set(self, data_manager):
        self.foam_pump_timeout_period = self.foam_pump_timeout_period - self.foam_pump_scan_period
        # 根据开关状态启动对应的泵
        foamSwitchStatue = [self.foam_ctrl.foam_sta.foam_start1, self.foam_ctrl.foam_sta.foam_start2, self.foam_ctrl.foam_sta.foam_start3, self.foam_ctrl.foam_sta.foam_start4, self.foam_ctrl.foam_sta.foam_start5, self.foam_ctrl.foam_sta.foam_start6]
        foam_mode = (self.foam_ctrl.foam_sta.mode1 or self.foam_ctrl.foam_sta.mode3)
        # 超时未打开开关
        if((self.foam_pump_timeout_period<=0)):
            # 报错
            self.ui.consolo.log_warning("泵开关设置失败！")
            gearsSetErrorDialog = QtWidgets.QMessageBox()
            gearsSetErrorDialog.about(self, '警告', '泵开关设置失败！')
            gearsSetErrorDialog.show()
            self.foam_pump_timer.stop()
        elif(foam_mode):
            # 第二步，启动相应的泵
            for index in range(0, len(foamSwitchStatue)):
                # 如果泡沫状态为1则打开对应的泵
                if(foamSwitchStatue[index] == 1):
                    self.foam_ctrl.foam_pump_switch(index, 1, data_manager)      
                else:
                    pass
            self.foam_pump_valve_timeout_period = 5000
            self.foam_pump_valve_scan_period = 200
            self.foam_pump_valve_timer = QtCore.QTimer()
            self.foam_pump_valve_timer.start(200)
            self.foam_pump_valve_timer.timeout.connect(lambda: self.foam_pump_valve_set(data_manager))
            self.foam_pump_timer.stop()
        else:
            pass

    # 打开泡沫系统泵开关
    def foam_pump_valve_set(self, data_manager):
        self.foam_pump_valve_timeout_period = self.foam_pump_valve_timeout_period - self.foam_pump_valve_scan_period
        # 根据开关状态启动对应的泵
        foamSwitchStatue = [self.foam_ctrl.foam_sta.foam_start1, self.foam_ctrl.foam_sta.foam_start2, self.foam_ctrl.foam_sta.foam_start3, self.foam_ctrl.foam_sta.foam_start4, self.foam_ctrl.foam_sta.foam_start5, self.foam_ctrl.foam_sta.foam_start6]
        foamPumpStatue = [self.foam_ctrl.foam_sta.foam_pump1, self.foam_ctrl.foam_sta.foam_pump2, self.foam_ctrl.foam_sta.foam_pump3, self.foam_ctrl.foam_sta.foam_pump4, self.foam_ctrl.foam_sta.foam_pump5, self.foam_ctrl.foam_sta.foam_pump6]
        # 超时未打开泵
        if((self.foam_pump_valve_timeout_period<=0)):
            # 报错
            self.ui.consolo.log_warning("泵开关设置失败！")
            gearsSetErrorDialog = QtWidgets.QMessageBox()
            gearsSetErrorDialog.about(self, '警告', '泵开关设置失败！')
            gearsSetErrorDialog.show()
            self.foam_pump_valve_timer.stop()
        # 如果泵的状态和泡沫阀的状态完全相同则启动泵成功
        elif(foamSwitchStatue == foamPumpStatue):
            # 泵开关设置成功 
            self.ui.consolo.log_recommond("泡沫泵停止成功！")
            self.foam_pump_valve_timer.stop()
        else:
            pass
  
    # =====================================================================
    # 界面刷新以及更新系统状态
    def uiRefresh(self):
        # PLC状态同步,在内部已经判断系统的连接状态
        # self.plcStaSync()
        cur_time = self.datetime.currentDateTime().toString(QtCore.Qt.ISODate)
        start_time = time.time()
        self.ui.date_time_label2.setText(cur_time)
        # 如果仿真系统连接且数据不为空
        if self.data_manager.connect_status == 2 and self.data_manager :
            # 使能相关组件
            self.ui.dockAttitude.setEnabled(True)
            self.ui.dockFeildDebug.setEnabled(True)
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.btn4.setEnabled(True)
            # self.topwidget.setHidden(False)
            # self.dockControlConfirm.setEnabled(True)
            # self.dockControlConfirm.setHidden(False)
            # 更新系统状态
            # self.statusUpdate()
            # 绘图更新显示1
            self.ui.pwidget.plotUpdate(self.data_manager, self.data_manager._address_def)
            # 主界面数据更新显示
            self.ui.pwidget1.showUpdate(self.data_manager, self.thrust_ctrl.thrust_sta, self.cutter_ctrl.cutter_sta, self.conveyer_ctrl.conveyer_sta, self.foam_ctrl.spray_sta, self.foam_ctrl.foam_sta, self.thrust_ctrl.guide_sta, self.sys_sta)
            self.ui.pwidget2.showUpdate(self.data_manager, self.thrust_ctrl.thrust_sta, self.cutter_ctrl.cutter_sta, self.conveyer_ctrl.conveyer_sta, self.foam_ctrl.spray_sta, self.foam_ctrl.foam_sta, self.thrust_ctrl.guide_sta, self.sys_sta)
          
            # 铰接系统界面数据更新显示
            self.ui.dockHingeShowWidget.showUpdate(self.data_manager, self.thrust_ctrl.thrust_sta)
            # 盾构机位置更新显示
            self.ui.dockPlaneShowWidget.updateShieldPosition(self.data_manager, self.thrust_ctrl.guide_sta, self.driver.parm)
            # self.ui.pwidget2.updateShieldPosition(self.data_manager, self.thrust_ctrl)
            # self.curve1.setData(x=self.data_manager.sim['时间'][:self.data_manager.record_index], y=self.data_manager.sim['里程'][:self.data_manager.record_index])
            self.ui.dockDataShowWidget.updataSysData(self.data_manager)
            # 刷新仿真控制界面的显示
            self.ui.dockSimControlWidget.uiRefresh(self.stm_ctrl.simenv_sta)
            # 刷新手动控制界面                
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.uiRefresh(self.data_manager, self.thrust_ctrl.thrust_sta, self.cutter_ctrl.cutter_sta, self.conveyer_ctrl.conveyer_sta)
            # 刷新辅料控制界面
            self.ui.dockAttitudeWidget.accessariesCtrlPannel.uiRefresh(self.data_manager, self.foam_ctrl.spray_sta, self.foam_ctrl.foam_sta)
            # 刷新异常显示窗口
            self.ui.warning_widget.uiRefresh(self.sys_sta)
            # 刷新状态栏
            self.ui.sta_message.setText("已连接至：仿真系统")
            # 显示授权状态
            self.ui.permit_dispc.setDisabled(False)
            self.ui.permit_disp.setText('推进系统已授权')
            
            if self.cutter_ctrl.cutter_sta.authorization_permit==1:
                self.ui.cutter_permit_dispc.setDisabled(False)
                self.ui.cutter_permit_disp.setText('刀盘系统已授权')
            else:
                self.ui.cutter_permit_dispc.setDisabled(True)
                self.ui.cutter_permit_disp.setText('刀盘系统未授权')
                
            if self.conveyer_ctrl.conveyer_sta.authorization_permit==1:
                self.ui.conveyer_permit_dispc.setDisabled(False)
                self.ui.conveyer_permit_disp.setText('螺机系统已授权')
            else:
                self.ui.conveyer_permit_dispc.setDisabled(True)
                self.ui.conveyer_permit_disp.setText('螺机系统未授权')
            if self.conveyer_ctrl.conveyer_sta.mode == 1:
                self.ui.dockAttitudeWidget.mannuelCtrlPannel.conveyerSpeedDial.setEnabled(True)
            else:
                self.ui.dockAttitudeWidget.mannuelCtrlPannel.conveyerSpeedDial.setEnabled(False)
        # 连接真机   
        elif self.data_manager.connect_status == 1 :
            # 使能相关组件
            self.ui.dockAttitude.setEnabled(True)
            self.ui.dockFeildDebug.setEnabled(True)
            # 连接真机时禁用管片拼装按钮
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.btn4.setEnabled(False)
            # self.topwidget.setHidden(False)
            # self.dockControlConfirm.setEnabled(True)
            # self.dockControlConfirm.setHidden(False)
            
            try:
                self.ui.pwidget.plotUpdate(self.data_manager, self.data_manager._address_def)
                self.ui.pwidget1.showUpdate(self.data_manager, self.thrust_ctrl.thrust_sta, self.cutter_ctrl.cutter_sta, self.conveyer_ctrl.conveyer_sta, self.foam_ctrl.spray_sta, self.foam_ctrl.foam_sta, self.thrust_ctrl.guide_sta, self.sys_sta)
                self.ui.pwidget2.showUpdate(self.data_manager, self.thrust_ctrl.thrust_sta, self.cutter_ctrl.cutter_sta, self.conveyer_ctrl.conveyer_sta, self.foam_ctrl.spray_sta, self.foam_ctrl.foam_sta, self.thrust_ctrl.guide_sta, self.sys_sta)
                self.ui.dockHingeShowWidget.showUpdate(self.data_manager, self.thrust_ctrl.thrust_sta)
                # self.ui.pwidget2.updateShieldPosition(self.data_manager, self.thrust_ctrl.guide_sta)
                self.ui.dockPlaneShowWidget.updateShieldPosition(self.data_manager, self.thrust_ctrl.guide_sta, self.driver.parm)
                # self.ui.dockDataShowWidget.updataSysData(self.data_manager.data_buffer, self.data_manager._address_def, self.sys_sta)
                self.ui.dockDataShowWidget.updataSysData(self.data_manager)
            except Exception:
                self.ui.consolo.log_error("绘图异常！")
            else:
                pass
            
            # if self.sys_sta.visualConnected== True:
            #     self.ui.dockSimControlWidget.uiRefresh(sim_sta=self.visual_sys.simenv_sta)  # ?
            #     self.thrust_ctrl.thrust_sta.seg_mode=self.visual_sys.thrust_sta.seg_mode   # ?
            # 更新系统状态
            # self.statusUpdate()
            # 刷新姿态控制界面
            self.ui.dockAttitudeWidget.mannuelCtrlPannel.uiRefresh(self.data_manager, self.thrust_ctrl.thrust_sta, self.cutter_ctrl.cutter_sta, self.conveyer_ctrl.conveyer_sta)
            # 刷新辅料控制界面
            self.ui.dockAttitudeWidget.accessariesCtrlPannel.uiRefresh(self.data_manager, self.foam_ctrl.spray_sta, self.foam_ctrl.foam_sta)
            # 刷新异常显示窗口
            self.ui.warning_widget.uiRefresh(self.sys_sta)
            # 刷新状态栏
            self.ui.sta_message.setText("已连接至:真机PLC")
            # 显示授权状态
            if self.thrust_ctrl.thrust_sta.authorization_permit==1:
                self.ui.permit_dispc.setDisabled(False)
                self.ui.permit_disp.setText('推进系统已授权')
            else:
                self.ui.permit_dispc.setDisabled(True)
                self.ui.permit_disp.setText('推进系统未授权')
            if self.cutter_ctrl.cutter_sta.authorization_permit==1:
                self.ui.cutter_permit_dispc.setDisabled(False)
                self.ui.cutter_permit_disp.setText('刀盘系统已授权')
            else:
                self.ui.cutter_permit_dispc.setDisabled(True)
                self.ui.cutter_permit_disp.setText('刀盘系统未授权')
                
            if self.conveyer_ctrl.conveyer_sta.authorization_permit==1:
                self.ui.conveyer_permit_dispc.setDisabled(False)
                self.ui.conveyer_permit_disp.setText('螺机系统已授权')
            else:
                self.ui.conveyer_permit_dispc.setDisabled(True)
                self.ui.conveyer_permit_disp.setText('螺机系统未授权')

            if self.foam_ctrl.foam_sta.authorization_permit==1:
                self.ui.foam_permit_dispc.setDisabled(False)
                self.ui.foam_permit_disp.setText('泡沫系统已授权')
            else:
                self.ui.foam_permit_dispc.setDisabled(True)
                self.ui.foam_permit_disp.setText('泡沫系统未授权')
            if self.conveyer_ctrl.conveyer_sta.mode == 1:
                self.ui.dockAttitudeWidget.mannuelCtrlPannel.conveyerSpeedDial.setEnabled(True)
            else:
                self.ui.dockAttitudeWidget.mannuelCtrlPannel.conveyerSpeedDial.setEnabled(False)
        else:
            # 禁用相关组件
            self.ui.dockAttitude.setEnabled(False)
            # self.dockControlConfirm.setEnabled(False)
            # self.dockControlConfirm.setHidden(True)
            # self.topwidget.setHidden(True)
            self.ui.dockFeildDebug.setEnabled(False)
            self.ui.sta_message.setText("未连接")
            
        # print(time.time()-start_time)  

    def cutterRotationUpdate(self):        
        # 计算刀盘转速
        if self.data_manager.connect_status != 0 :
            cur_angle = self.cutter_ctrl.cutter_sta.dp_angle
            self.ui.pwidget1.cutterRotate(cur_angle)
            
                
    # 定时更新系统的状态变量以及控制器
    def statusUpdate(self):        
        # 更新系统状态
        # 如果仿真系统连接
        if self.data_manager.connect_status == 2 and (not self.data_manager.data_buffer == {}):
            try:
                # 获取刀盘状态
                self.cutter_ctrl.cutter_status_get(self.data_manager)
                # 获取推进系统状态
                self.thrust_ctrl.thrust_status_get(self.data_manager)
                # 获取导向系统状态
                self.thrust_ctrl.guide_status_get(self.data_manager)
                # 获取螺机系统状态
                self.conveyer_ctrl.conveyer_status_get(self.data_manager)
                # 获取仿真状态等
                self.stm_ctrl.simenv_status_get(self.data_manager)
                # 获取泡沫系统状态
                self.foam_ctrl.foam_status_get(self.data_manager)
                # 获取刀盘自动喷水状态
                self.foam_ctrl.spray_status_get(self.data_manager)

            except Exception:
                return
            else:
                pass

        # 如果连接对象为真机
        elif  self.data_manager.connect_status == 1 and (not self.data_manager.data_buffer == {}):
            try:
                # 获取刀盘状态
                try:
                    self.cutter_ctrl.cutter_status_get(self.data_manager)
                except Exception:
                    print("1")
                else:
                    pass
                # 获取推进系统状态
                try:
                    self.thrust_ctrl.thrust_status_get(self.data_manager)
                except Exception:
                    print("2")
                else:
                    pass
                # 获取导向系统状态
                try:
                    self.thrust_ctrl.guide_status_get(self.data_manager)
                except Exception:
                    print("3")
                else:
                    pass
                # 获取螺机系统状态
                try:
                    self.conveyer_ctrl.conveyer_status_get(self.data_manager)
                except Exception:
                    print("4")
                else:
                    pass
                # 获取泡沫系统状态
                try:
                    self.foam_ctrl.foam_status_get(self.data_manager)
                except Exception:
                    print("5")
                else:
                    pass
                # 获取刀盘自动喷水状态
                try:
                    self.foam_ctrl.spray_status_get(self.data_manager)
                except Exception:
                    print("6")
                else:
                    pass
            except Exception:
                self.ui.consolo.log_error("更新状态出错!")
            else:
                pass
        else:
            pass


if __name__ == "__main__":
    import sys
    # 设置界面缩放，匹配高分辨率屏幕
    scale_factor = get_dpi_scale_factor()
    os.putenv("QT_SCALE_FACTOR", str(scale_factor)) # FIX Problem for High DPI and Scale above 100%

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("icon.ico"))
    window = MainWindow()
    window.ui.show()
    sys.exit(app.exec_())




