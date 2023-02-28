import sys
from PyQt5.QtWidgets import *
from PyQt5.QAxContainer import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import time as t
import pandas as pd
import sqlite3
import datetime
import numpy as np
import re
from datetime import datetime

TR_REQ_TIME_INTERVAL = 0.2

alertHtml = "<font color=\"DeepPink\">";
notifyHtml = "<font color=\"Lime\">";
infoHtml = "<font color=\"Aqua\">";
endHtml = "</font><br>";


class Kiwoom(QAxWidget):
    def __init__(self, ui):
        super().__init__()
        self._create_kiwoom_instance()
        self._set_signal_slots()
        self.ui = ui
        
        self.today = datetime.today().strftime("%Y%m%d")   
        
        self.dic = {}
        
        self.rebuy = 1 #재매수 횟수 (1번만 가능하도록)
        self.hoga = 0
        self.last_close = 0
        
        self.gudoc_count = 0 #종목 구독시 개수
        
        self.port_name = "" #포트 이름 저장변수
        
        self.stock_held = [] #보유종목리스트
        
        self.window_number = 0 #tableWidget_5 행 카운트
        
    #COM오브젝트 생성
    def _create_kiwoom_instance(self):
        self.setControl("KHOPENAPI.KHOpenAPICtrl.1") #고유 식별자 가져옴

    #이벤트 처리
    def _set_signal_slots(self):
        self.OnEventConnect.connect(self._event_connect) # 로그인 관련 이벤트 (.connect()는 이벤트와 슬롯을 연결하는 역할)
        self.OnReceiveTrData.connect(self._receive_tr_data) # 트랜잭션 요청 관련 이벤트
        self.OnReceiveChejanData.connect(self._receive_chejan_data) #체결잔고 요청 이벤트
        self.OnReceiveRealData.connect(self._handler_real_data) #실시간 데이터 처리
        self.OnReceiveRealCondition.connect(self._handler_real_condition) # 실시간 조건검색 조회 응답 이벤트
        self.OnReceiveConditionVer.connect(self._on_receive_condition_ver) # 로컬 사용자 조건식 저장 성공여부 응답 이벤트
        self.OnReceiveTrCondition.connect(self._on_receive_tr_condition) #조건검색 조회응답 이벤트
        

    #로그인
    def comm_connect(self):
        self.dynamicCall("CommConnect()") # CommConnect() 시그널 함수 호출(.dynamicCall()는 서버에 데이터를 송수신해주는 기능)
        self.login_event_loop = QEventLoop() # 로그인 담당 이벤트 루프(프로그램이 종료되지 않게하는 큰 틀의 루프)
        self.login_event_loop.exec_() #exec_()를 통해 이벤트 루프 실행  (다른데이터 간섭 막기)

    #이벤트 연결 여부
    def _event_connect(self, err_code):
        if err_code == 0:
            print("connected")
        else:
            print("disconnected")

        self.login_event_loop.exit()

    #종목리스트 반환
    def get_code_list_by_market(self, market):
        code_list = self.dynamicCall("GetCodeListByMarket(QString)", market) #종목리스트 호출
        code_list = code_list.split(';')
        return code_list[:-1]

    #종목명 반환
    def get_master_code_name(self, code):
        code_name = self.dynamicCall("GetMasterCodeName(QString)", code) #종목명 호출
        return code_name

    #통신접속상태 반환
    def get_connect_state(self):
        ret = self.dynamicCall("GetConnectState()") #통신접속상태 호출
        return ret

    #로그인정보 반환
    def get_login_info(self, tag):
        ret = self.dynamicCall("GetLoginInfo(QString)", tag) #로그인정보 호출
        return ret

    #TR별 할당값 지정하기
    def set_input_value(self, id, value):
        self.dynamicCall("SetInputValue(QString, QString)", id, value) #SetInputValue() 밸류값으로 원하는값지정 ex) SetInputValue("비밀번호"	,  "")

    #통신데이터 수신(tr)
    def comm_rq_data(self, rqname, trcode, next, screen_no):
        self.dynamicCall("CommRqData(QString, QString, int, QString)", rqname, trcode, next, screen_no) 
        self.tr_event_loop = QEventLoop()
        self.tr_event_loop.exec_()

    #실제 데이터 가져오기
    def _comm_get_data(self, code, real_type, field_name, index, item_name): 
        ret = self.dynamicCall("CommGetData(QString, QString, QString, int, QString)", code, #더이상 지원 안함??
                               real_type, field_name, index, item_name)
        return ret.strip()
    
    #실제 데이터 가져오기 2
    def _get_comm_data(self, trcode, recordname, index, itemname):
        result = self.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, index, itemname)
        return result
    

    #수신받은 데이터 반복횟수
    def _get_repeat_cnt(self, trcode, rqname):
        ret = self.dynamicCall("GetRepeatCnt(QString, QString)", trcode, rqname)
        return ret

    #주문 (주식)
    def send_order(self, rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no):
        self.dynamicCall("SendOrder(QString, QString, QString, int, QString, int, int, QString, QString)",
                         [rqname, screen_no, acc_no, order_type, code, quantity, price, hoga, order_no])
        
    #주문 (선물)    
    def send_order_fo(self, rqname, screen_no, acc_no,  code, order_type, slbytp, hoga, quantity, price, order_no):
        self.dynamicCall("SendOrderFO(QString, QString, QString, QString, int, QString, QString, int, QString, QString)",
                         [rqname, screen_no, acc_no, code, order_type, slbytp, hoga, quantity, price, order_no])


    #실시간 타입 구독신청
    def SetRealReg(self, screen_no, code_list, fid_list, real_type):
        self.dynamicCall("SetRealReg(QString, QString, QString, QString)", 
                              screen_no, code_list, fid_list, real_type)
        
    #실시간 타입 구독해지
    def DisConnectRealData(self, screen_no):
        self.dynamicCall("DisConnectRealData(QString)", screen_no)
    
        
    #서버에 저장되어있는 조건 검색식 리스트 불러오기
    def get_condition_load(self):
        result = self.dynamicCall("GetConditionLoad()")
        
        print(result)
        if result == 1:
            self.ui.textEdit.append("조건검색식이 올바르게 조회되었습니다.")
        elif result != 1 :
            self.ui.textEdit.append("조건검색식 조회중 오류가 발생했습니다.")
            
        price = format(int(self.ui.lineEdit_9.text()), ",")    
        self.ui.lineEdit_10.setText(str(price))   
        self.ui.pushButton_5.setDisabled(True)
        
    #로컬에 사용자 조건식 저장 성공 여부 확인
    def _on_receive_condition_ver(self):
        self.condition_list = {"index": [], "name": []}
        temporary_condition_list = self.dynamicCall("GetConditionNameList()").split(";")
        print(temporary_condition_list)
    
        
        for data in temporary_condition_list :
            try:
                a = data.split("^")
                self.condition_list['index'].append(str(a[0]))
                self.condition_list['name'].append(str(a[1]))
            except IndexError:
                pass
        
        self.ui.comboBox_2.addItems(self.condition_list['name'])
        
        self.ui.pushButton_2.setEnabled(True)
        self.ui.pushButton_3.setEnabled(True)
        
        condition_name = str(self.condition_list['name'][0])
        nindex = str(self.condition_list['index'][0])
        
        self.ui.pushButton_2.clicked.connect(self.ui.check_port)
        self.ui.pushButton_3.clicked.connect(self.ui.delete_row)

        condition_name2 = str(self.condition_list['name'][1])
        nindex2 = str(self.condition_list['index'][1])
       
        print("dasd" , self.condition_list ) 
       
        print(condition_name)
        print(condition_name2)
        print(nindex)
        print(nindex2)
        
        

    
    #조건검색 조회
    def _condition_search(self):
        self.sell_percent = float(self.ui.lineEdit_12.text())
        self.profit_percent = float(self.ui.lineEdit_13.text())
        
        self.sec_list = []
        print(self.ui.row_count)
        for i in range(self.ui.row_count):
            self.sec_list.append(self.ui.tableWidget_3.item(i,0).text())
        

        print(self.sec_list)

   
        
        for i in range(len(self.condition_list['name'])):
            for j in self.sec_list:
                if self.condition_list['name'][i] == j:
                    a = self.dynamicCall("SendCondition(QString, QString, int, int)", "0156", str(self.condition_list['name'][i]), str(self.condition_list['index'][i]), 1)
                    if a==1:
                        self.ui.textEdit.append("조건검색 조회요청 성공 | port이름 : " + str(self.condition_list['name'][i]) )
                    elif a!=1:
                        self.ui.textEdit.append("조건검색 조회요청 실패 | port이름 : " + str(self.condition_list['name'][i]) )
               

    #조건검색 조회 응답
    def _on_receive_tr_condition(self, scrno, codelist, conditionname, nnext):
        self.code_list = []
        codelist_split = codelist.split(';')
        for i in codelist_split:
            self.code_list.append(i)
            
            
        print("실시간x:" , self.code_list)



    
    #실시간 조건검색 응답(실시간으로 들어왔을때 전략에 들어가게끔만들기)
    def _handler_real_condition(self, code, type, cond_name, cond_index):
        #self.ui.textEdit.append("실시간o: " + str(cond_name) +  str(code) + str(type)) 
        print("실시간o: " + str(cond_name) +  str(code) + str(type)) 
        print("윈도우 카운트 : " , self.ui.window_count)
        print("구독종목 : ", self.gudoc_count)
        #구독한 종목 50개 넘어가면 윈도우 카운트 변경
        self.port_name = str(cond_name)
        if self.gudoc_count == 100:
            self.ui.window_count +=1
            self.gudoc_count = 0
            
        name = self.get_master_code_name(code)   


        self.dic[name+'_port_name'] = str(cond_name)
        #if len(self.ui.ticker_list) <= int(self.ui.lineEdit_11.text())-1:
        for i in self.sec_list:
            if len(self.sec_list) == 1:
                if str(cond_name) == str(i) == self.sec_list[0]:
                    if self.ui.checkBox_2.isChecked():
                        continue
                    else :
                        #self.ui.textEdit_2.append("실시간o: " + str(code))
                        #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                        self.port_name = str(cond_name)
                        
                        if code not in self.ui.ticker_list:
                            self.ui.ticker_list.append(code)
                
                        if code not in self.dic.values() and code != "":
                            self.ready_trade(code)  
                        
                        if self.ui.gudoc_status == 0:
                            self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                            self.gudoc_count += 1
                            self.ui.gudoc_status = 1
                            print('구독성공')
                        elif self.ui.gudoc_status != 0 :
                            self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                            self.gudoc_count += 1
                            print('구독성공2')

            elif len(self.sec_list) == 2:
                if str(cond_name) == str(i) == self.sec_list[0] :
                    if self.ui.checkBox_2.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)  
                       
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')

                       
                elif str(cond_name) == str(i) == self.sec_list[1]:
                    if self.ui.checkBox_3.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
                             
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')
                
            elif len(self.sec_list) == 3:
                if str(cond_name) == str(i) == self.sec_list[0]:
                    if self.ui.checkBox_2.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)  
                       
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')

                       
                elif str(cond_name) == str(i) == self.sec_list[1]:
                    if self.ui.checkBox_3.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
                             
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')

                       
                elif str(cond_name) == str(i) == self.sec_list[2]:
                    if self.ui.checkBox_4.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
                                 
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')
                   
            elif len(self.sec_list) == 4:
                if str(cond_name) == str(i) == self.sec_list[0]:
                    if self.ui.checkBox_2.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)  
                       
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')

                       
                elif str(cond_name) == str(i) == self.sec_list[1]:
                    if self.ui.checkBox_3.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
                             
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')
                       
                elif str(cond_name) == str(i) == self.sec_list[2]:
                    if self.ui.checkBox_4.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
                                 
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')
    
                elif str(cond_name) == str(i) == self.sec_list[3]:
                    if self.ui.checkBox_5.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
                       
                 
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')

            elif len(self.sec_list) == 5:
                if str(cond_name) == str(i) == self.sec_list[0]:
                    if self.ui.checkBox_2.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)  
                       
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')
                       
                elif str(cond_name) == str(i) == self.sec_list[1]:
                    if self.ui.checkBox_3.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
                             
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')
                       
                elif str(cond_name) == str(i) == self.sec_list[2]:
                    if self.ui.checkBox_4.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
                                 
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')
    
                elif str(cond_name) == str(i) == self.sec_list[3]:
                    if self.ui.checkBox_5.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
                       
                 
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')
                elif str(cond_name) == str(i) == self.sec_list[4]:
                    if self.ui.checkBox_6.isChecked():
                        continue
                    else :
                       #self.ui.textEdit_2.append("실시간o: " + str(code))
                       #self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
                       self.port_name = str(cond_name)
               
                       if code not in self.ui.ticker_list:
                           self.ui.ticker_list.append(code)
               
                       if code not in self.dic.values() and code != "":
                           self.ready_trade(code)
              
                       if self.ui.gudoc_status == 0:
                           self.SetRealReg(1000 + self.ui.window_count , code, "20;10", "0")
                           self.gudoc_count += 1
                           self.ui.gudoc_status = 1
                           print('구독성공')
                       elif self.ui.gudoc_status != 0 :
                           self.SetRealReg(1000 + self.ui.window_count , code, "20;10", "1")
                           self.gudoc_count += 1
                           print('구독성공2')
    
        #else :
            #print("종목수 초과!")
            #print(self.ui.ticker_list)
                


####
    #실시간 조회관련 핸들
    def _handler_real_data(self, trcode, real_type, data):
        
        try:

            #print(self.dic)
            
            # 체결 시간 
            if real_type == "주식체결":
                time =  self.get_comm_real_data(trcode, 20)
                #date = datetime.datetime.now().strftime("%Y-%m-%d ")
                #time = datetime.datetime.strptime(time, "%H:%M:%S")
                time = time[:2] + ":" + time[2:4] + ":" + time[4:6]
    
            #호가
            hoga_1 = self.get_comm_real_data(trcode, 27)
            hoga_2 = self.get_comm_real_data(trcode, 28)
            
            
            if hoga_1 != "" and hoga_2 != "":
                hoga = float(hoga_1[1:]) - float(hoga_2[1:]) 
                
    
    
            for i in range(len(self.ui.ticker_list)):
                if trcode == self.ui.ticker_list[i]:
                    #print(i, "번째 :", self.ui.stock_list[i])
                    
    
                    start_price = self.get_comm_real_data(trcode, 16) #시가
                    price = self.get_comm_real_data(trcode, 10)       #현재가
                    high = self.get_comm_real_data(trcode, 17)        #고가
                    low = self.get_comm_real_data(trcode, 18)         #저가
                    name = self.get_master_code_name(trcode)          #이름
                    #compare = self.get_comm_real_data(trcode, 12).strip()  #전일대비
                        
                        
                    if start_price  == "" or high == "" or low == "" :
                        pass
                    #self.ui.textEdit_2.append("시가 입력 대기중 :" + name )
                    else:
                        start_price  = float(start_price[1:])
                        price = float(price[1:])
                        high = float(high[1:])
                        low = float(low[1:])
                        
                        #compare = float(compare)
                        
                        div_4 = (int(high)- int(low))/4
                        
                        
                        self.dic[name + '_start_price'] = start_price  
                        self.dic[name + '_price'] = price
                        #self.dic[name + '_compare'] = compare
                        self.dic[name + '_hoga'] = hoga
    
                        if trcode not in self.stock_held:
                            self.stock_held.append(trcode) 
                            print(self.stock_held)
    
                        row_number = self.dic[name+'_window_count'] 
                        
                        self.ui.tableWidget_5.setRowCount(len(self.stock_held))
                        self.ui.tableWidget_5.setColumnCount(7)
                        self.ui.tableWidget_5.setItem(row_number,0,QTableWidgetItem(name.strip()))
                        self.ui.tableWidget_5.setItem(row_number,1,QTableWidgetItem(str(start_price)))
                        self.ui.tableWidget_5.setItem(row_number,2,QTableWidgetItem(str(low)))
                        self.ui.tableWidget_5.setItem(row_number,3,QTableWidgetItem(str(high)))
                        self.ui.tableWidget_5.setItem(row_number,4,QTableWidgetItem(str(low + div_4*3 )))
                        self.ui.tableWidget_5.setItem(row_number,5,QTableWidgetItem(str(low + div_4*2 )))
                        self.ui.tableWidget_5.setItem(row_number,6,QTableWidgetItem(str(low + div_4 )))
                        
    
                        self.dic[name + "_upper"] = low + div_4*3 #상단선
                        self.dic[name + "_middle"] = low + div_4*2 #중단선
                        self.dic[name + "_lower"] = low + div_4 #하단선
    
                        #print("_handler_real_data :" , name)
                            
                        self.strategy(name, time)
                            
        except Exception as e:    # 모든 예외의 에러 메시지를 출력
            print('예외가 발생했습니다.', e)
    #초기 리스트 만들기    
    def ready_trade(self, ticker):
        
        name = self.get_master_code_name(ticker)
        
        self.dic[name + '_name'] = name
        self.dic[name + '_ticker'] = ticker
        self.dic[name + '_status'] = '초기상태' 
        self.dic[name + '_rebuy'] = 1  
        self.dic[name + '_initial'] = 0 
        self.dic[name + '_buy_count'] = 0 
        self.dic[name + '_sell_price'] = 0 
        self.dic[name + '_rebuy_count'] = 0
        self.dic[name + '_buy_total'] = int(self.ui.lineEdit_9.text())
        

        #재매수시 비율
        self.dic[name + '_sec_percent'] = 0
            
        
        #self.dic[name + "_open_5"] = 0 #5분봉 시가
        #self.dic[name + "_low_5"] = 0 #5분봉 저가
        #self.dic[name + "_high_5"] = 0 #5분봉 고가
        self.dic[name + "_window_count"] = self.window_number #행번호
        
        self.window_number += 1

        self.dic[name + "_upper"] = 0 #상단선
        self.dic[name + "_middle"] = 0 #중단선
        self.dic[name + "_lower"] = 0 #하단선
        

        
        self.dic[name + "_reach_upper"] = 0 #현재가격이 상단선 위로 올라갔는지 여부
        self.dic[name + "_reach_middle"] = 0 #현재가격이 중단선 밑으로 떨어졌는지 여부
        self.dic[name + "_reach_low"] = 0   #현재가격이 하단선 밑으로 떨어졌는지 여부


        #self.plainTextEdit.appendPlainText("거래준비완료 | 종목 :" + name )
        self.ui.textEdit.append("거래준비완료 | 종목 :" + name)

        print("ready_trade")
        
      

    #실시간 데이터 가져오기
    def get_comm_real_data(self, trcode, fid):
        ret = self.dynamicCall("GetCommRealData(QString, int)", trcode, fid)
        return ret

    #체결정보
    def get_chejan_data(self, fid):
        ret = self.dynamicCall("GetChejanData(int)", fid)
        return ret
    

    def get_server_gubun(self):
        ret = self.dynamicCall("KOA_Functions(QString, QString)", "GetServerGubun", "")
        return ret

    def _receive_chejan_data(self, gubun, item_cnt, fid_list):
         
        if gubun == "0":
            stock_ticker = self.get_chejan_data(9001)
            
            if stock_ticker[1:] not in self.stock_held:
                self.stock_held.append(stock_ticker[1:])   
                #self.window_number += 1


    #받은 tr데이터가 무엇인지, 연속조회 할수있는지
    def _receive_tr_data(self, screen_no, rqname, trcode, record_name, next, unused1, unused2, unused3, unused4):
        if next == '2': 
            self.remained_data = True
        else:
            self.remained_data = False
            
        #받은 tr에따라 각각의 함수 호출
        if rqname == "opt10081_req": #주식일봉차드 조회
            self._opt10081(rqname, trcode)
        elif rqname == "opw00001_req": #예수금 상세현황 요청
            self._opw00001(rqname, trcode)
        elif rqname == "opw00018_req": #계좌평가잔고 내역 요청
            self._opw00018(rqname, trcode)
        elif rqname == "opt10004_req":
            self._opt10004(rqname, trcode)
        elif rqname == "opt10002_req":
            self._opt10002(rqname, trcode)
        elif rqname == "opt10080_req": #주식분봉차트 조회
            self._opt10080(rqname, trcode)



        try:
            self.tr_event_loop.exit()
        except AttributeError:
            pass

    @staticmethod
    #입력받은데이터 정제    
    def change_format(data):
        strip_data = data.lstrip('-0')
        if strip_data == '' or strip_data == '.00':
            strip_data = '0'

        try:
            format_data = format(int(strip_data), ',d')
        except:
            format_data = format(float(strip_data))
        if data.startswith('-'):
            format_data = '-' + format_data

        return format_data

    #입력받은데이터(수익률) 정제
    @staticmethod
    def change_format2(data):
        strip_data = data.lstrip('-0')

        if strip_data == '':
            strip_data = '0'

        if strip_data.startswith('.'):
            strip_data = '0' + strip_data

        if data.startswith('-'):
            strip_data = '-' + strip_data

        return strip_data

    def _opw00001(self, rqname, trcode):
        d2_deposit = self._comm_get_data(trcode, "", rqname, 0, "d+2추정예수금")
        self.d2_deposit = Kiwoom.change_format(d2_deposit)

    
    def _opt10080(self, rqname, trcode):    
        data_cnt = self._get_repeat_cnt(trcode, rqname) #데이터 갯수 확인

        list_2 = []
    
        for i in range(900):
            date_1 = self._get_comm_data(trcode, "주식분봉차트조회", i, "체결시간")
            high_1 = self._get_comm_data(trcode, "주식분봉차트조회", i, "고가")
            if date_1.strip()[0:8] == self.today:
                list_2.append(int(high_1.strip()[1:]))
        
        #print("max" + str(max(list_2)))

        #ValueError: max() arg is an empty sequence
        
        print("max" + str(max(list_2)))
        print("len" + str(len(list_2)))
        #print(list_2)


        date = self._get_comm_data(trcode, "주식분봉차트조회", 0, "체결시간")
        open = self._get_comm_data(trcode, "주식분봉차트조회", 0, "시가")
        high = self._get_comm_data(trcode, "주식분봉차트조회", 0, "고가")
        low = self._get_comm_data(trcode, "주식분봉차트조회", 0, "저가")
        close = self._get_comm_data(trcode, "주식분봉차트조회", 0, "현재가")
        volume = self._get_comm_data(trcode, "주식분봉차트조회", 0, "거래량")
        code = self._get_comm_data(trcode, "주식분차트", 0, "종목코드")
            
        
        
        name = self.get_master_code_name(code.strip())


        list_1 = [k for k in self.dic.keys() if name in k ]
        
        if list_1 != []:
            
            open_5 = self.dic[list_1[list_1.index(name+'_open_5')]]
            low_5 = self.dic[list_1[list_1.index(name+'_low_5')]] 
            high_5 = self.dic[list_1[list_1.index(name+'_high_5')]] 
            row_number = self.dic[list_1[list_1.index(name+'_window_count')]] 
            
            #처음 값 저장
            if low_5 == 0:
                self.dic[list_1[list_1.index(name+'_low_5')]] = int(low.strip()[1:])
                low_5 = int(low.strip()[1:])
            if high_5 == 0 :
                self.dic[list_1[list_1.index(name+'_high_5')]] = max(list_2)
                high_5 = max(list_2) #최고가
            if open_5 == 0 :
                self.dic[list_1[list_1.index(name+'_open_5')]] = int(open.strip()[1:])
                open_5 = int(open.strip()[1:])
                
            #현재 저가가 초기 시가 보다 낮으면 
            if int(low.strip()[1:]) <= int(open_5):
                self.dic[list_1[list_1.index(name+'_low_5')]] = int(low.strip()[1:])
                low_5 = int(low.strip()[1:])
                
                #고가가 갱신되면
                if int(high.strip()[1:]) >= int(high_5):
                    self.dic[list_1[list_1.index(name+'_high_5')]] = int(high.strip()[1:])
                    high_5 = int(high.strip()[1:])
                    div_4 = (int(high_5)- int(low_5))/4 #4등분 가격
                    
                    self.dic[list_1[list_1.index(name+'_upper')]] = low_5 + div_4*3
                    self.dic[list_1[list_1.index(name+'_middle')]] = low_5 + div_4*2
                    self.dic[list_1[list_1.index(name+'_lower')]] = low_5 + div_4
                    
                    
                    print("div_4 : " + str(div_4))
                    print("name : " + str(name) + "row_number : " + str(row_number))
                    if date.strip()[0:8] == self.today:
                        print("row_number : " + str(row_number))
                        self.ui.tableWidget_5.setRowCount(len(self.stock_held))
                        self.ui.tableWidget_5.setColumnCount(7)
                        self.ui.tableWidget_5.setItem(row_number,0,QTableWidgetItem(name.strip()))
                        self.ui.tableWidget_5.setItem(row_number,1,QTableWidgetItem(str(open_5)))
                        self.ui.tableWidget_5.setItem(row_number,2,QTableWidgetItem(str(low_5)))
                        self.ui.tableWidget_5.setItem(row_number,3,QTableWidgetItem(str(high_5)))
                        self.ui.tableWidget_5.setItem(row_number,4,QTableWidgetItem(str(low_5 + div_4*3 )))
                        self.ui.tableWidget_5.setItem(row_number,5,QTableWidgetItem(str(low_5 + div_4*2 )))
                        self.ui.tableWidget_5.setItem(row_number,6,QTableWidgetItem(str(low_5 + div_4 )))
                    
                    
                else :
                    div_4 = (int(high_5)- int(low_5))/4 #4등분 가격
                    print("div_4 : " + str(div_4))
                    print("name : " + str(name) + "row_number : " + str(row_number))
                    
                    self.dic[list_1[list_1.index(name+'_upper')]] = low_5 + div_4*3
                    self.dic[list_1[list_1.index(name+'_middle')]] = low_5 + div_4*2
                    self.dic[list_1[list_1.index(name+'_lower')]] = low_5 + div_4
                    
                    
                    if date.strip()[0:8] == self.today:
                        print("row_number : " + str(row_number))
                        self.ui.tableWidget_5.setRowCount(len(self.stock_held))
                        self.ui.tableWidget_5.setColumnCount(7)
                        self.ui.tableWidget_5.setItem(row_number,0,QTableWidgetItem(name.strip()))
                        self.ui.tableWidget_5.setItem(row_number,1,QTableWidgetItem(str(open_5)))
                        self.ui.tableWidget_5.setItem(row_number,2,QTableWidgetItem(str(low_5)))
                        self.ui.tableWidget_5.setItem(row_number,3,QTableWidgetItem(str(high_5)))
                        self.ui.tableWidget_5.setItem(row_number,4,QTableWidgetItem(str(low_5 + div_4*3 )))
                        self.ui.tableWidget_5.setItem(row_number,5,QTableWidgetItem(str(low_5 + div_4*2 )))
                        self.ui.tableWidget_5.setItem(row_number,6,QTableWidgetItem(str(low_5 + div_4 )))
     
            #현재 저가가 초기 시가 보다 높으면 
            else:
                #고가가 갱신되면
                if int(high.strip()[1:]) >= int(high_5):
                    self.dic[list_1[list_1.index(name+'_high_5')]] = int(high.strip()[1:])
                    high_5 = int(high.strip()[1:])
                    div_4 = (int(high_5)- int(open_5))/4 #4등분 가격
                    
                    
                    self.dic[list_1[list_1.index(name+'_upper')]] = low_5 + div_4*3
                    self.dic[list_1[list_1.index(name+'_middle')]] = low_5 + div_4*2
                    self.dic[list_1[list_1.index(name+'_lower')]] = low_5 + div_4
                    
                    
                    print("div_4 : " + str(div_4))
                    print("name : " + str(name) + "row_number : " + str(row_number))
                    if date.strip()[0:8] == self.today:
                        print("row_number : " + str(row_number))
                        self.ui.tableWidget_5.setRowCount(len(self.stock_held))
                        self.ui.tableWidget_5.setColumnCount(7)
                        self.ui.tableWidget_5.setItem(row_number,0,QTableWidgetItem(name.strip()))
                        self.ui.tableWidget_5.setItem(row_number,1,QTableWidgetItem(str(open_5)))
                        self.ui.tableWidget_5.setItem(row_number,2,QTableWidgetItem(str(low_5)))
                        self.ui.tableWidget_5.setItem(row_number,3,QTableWidgetItem(str(high_5)))
                        self.ui.tableWidget_5.setItem(row_number,4,QTableWidgetItem(str(open_5 + div_4*3 )))
                        self.ui.tableWidget_5.setItem(row_number,5,QTableWidgetItem(str(open_5 + div_4*2 )))
                        self.ui.tableWidget_5.setItem(row_number,6,QTableWidgetItem(str(open_5 + div_4 )))
                    
                else :
                    div_4 = (int(high_5)- int(open_5))/4 #4등분 가격
                    print("div_4 : " + str(div_4))
                    print("name : " + str(name) + "row_number : " + str(row_number))
                    
                    self.dic[list_1[list_1.index(name+'_upper')]] = low_5 + div_4*3
                    self.dic[list_1[list_1.index(name+'_middle')]] = low_5 + div_4*2
                    self.dic[list_1[list_1.index(name+'_lower')]] = low_5 + div_4
                    
                    if date.strip()[0:8] == self.today:
                        print("row_number : " + str(row_number))
                        self.ui.tableWidget_5.setRowCount(len(self.stock_held))
                        self.ui.tableWidget_5.setColumnCount(7)
                        self.ui.tableWidget_5.setItem(row_number,0,QTableWidgetItem(name.strip()))
                        self.ui.tableWidget_5.setItem(row_number,1,QTableWidgetItem(str(open_5)))
                        self.ui.tableWidget_5.setItem(row_number,2,QTableWidgetItem(str(low_5)))
                        self.ui.tableWidget_5.setItem(row_number,3,QTableWidgetItem(str(high_5)))
                        self.ui.tableWidget_5.setItem(row_number,4,QTableWidgetItem(str(open_5 + div_4*3 )))
                        self.ui.tableWidget_5.setItem(row_number,5,QTableWidgetItem(str(open_5 + div_4*2 )))
                        self.ui.tableWidget_5.setItem(row_number,6,QTableWidgetItem(str(open_5 + div_4 )))
     
            
     

    def _opt10081(self, rqname, trcode):
        data_cnt = self._get_repeat_cnt(trcode, rqname) #데이터 갯수 확인

        for i in range(data_cnt): #시고저종 거래량 가져오기
            date = self._comm_get_data(trcode, "", rqname, i, "일자")
            open = self._comm_get_data(trcode, "", rqname, i, "시가")
            high = self._comm_get_data(trcode, "", rqname, i, "고가")
            low = self._comm_get_data(trcode, "", rqname, i, "저가")
            close = self._comm_get_data(trcode, "", rqname, i, "현재가")
            volume = self._comm_get_data(trcode, "", rqname, i, "거래량")
                
            if date[0:8] == "20230117":
                print('81시가 : ' + str(date))
                print("81고가 : " + str(high))
                print("81저가 : " + str(low))
                print("81종가 : " + str(close))
    
            
        
    #호가 가져오기
    def _opt10004(self, rqname, trcode):
        item_hoga_10 = self._get_comm_data(trcode, rqname, 0, "매도3차선호가")
        item_hoga_9 = self._get_comm_data(trcode, rqname, 0, "매도2차선호가")
        item_hoga_8 = self._get_comm_data(trcode, rqname, 0, "매수최우선호가")
        item_hoga_7 = self._get_comm_data(trcode, rqname, 0, "매수2차선호가")
        
        if item_hoga_10.strip() == "":
            self.hoga = abs(int(item_hoga_8.strip()[1:]) - int(item_hoga_7.strip()[1:]))
        else:
            self.hoga = abs(int(item_hoga_10.strip()[1:]) - int(item_hoga_9.strip()[1:]))

    
    #전일 종가 가져오기
    def _opt10002(self, rqname, trcode):
        last_close = self._get_comm_data(trcode, rqname, 0, "기준가")    
        self.last_close = float(last_close.strip())
    

    #opw박스 초기화 (주식)
    def reset_opw00018_output(self):
        self.opw00018_output = {'single': [], 'multi': []}

    #여러 정보들 저장 (주식)
    def _opw00018(self, rqname, trcode):
        # single data
        total_purchase_price = self._comm_get_data(trcode, "", rqname, 0, "총매입금액")
        total_eval_price = self._comm_get_data(trcode, "", rqname, 0, "총평가금액")
        total_eval_profit_loss_price = self._comm_get_data(trcode, "", rqname, 0, "총평가손익금액")
        total_earning_rate = self._comm_get_data(trcode, "", rqname, 0, "총수익률(%)")
        estimated_deposit = self._comm_get_data(trcode, "", rqname, 0, "추정예탁자산")

        self.opw00018_output['single'].append(Kiwoom.change_format(total_purchase_price))
        self.opw00018_output['single'].append(Kiwoom.change_format(total_eval_price))
        self.opw00018_output['single'].append(Kiwoom.change_format(total_eval_profit_loss_price))

        total_earning_rate = Kiwoom.change_format(total_earning_rate)
        

        if self.get_server_gubun():
            total_earning_rate = float(total_earning_rate) / 100
            total_earning_rate = str(total_earning_rate)

        self.opw00018_output['single'].append(total_earning_rate)

        self.opw00018_output['single'].append(Kiwoom.change_format(estimated_deposit))

        # multi data
        rows = self._get_repeat_cnt(trcode, rqname)
        for i in range(rows):
            name = self._comm_get_data(trcode, "", rqname, i, "종목명")
            quantity = self._comm_get_data(trcode, "", rqname, i, "보유수량")
            purchase_price = self._comm_get_data(trcode, "", rqname, i, "매입가")
            current_price = self._comm_get_data(trcode, "", rqname, i, "현재가")
            eval_profit_loss_price = self._comm_get_data(trcode, "", rqname, i, "평가손익")
            earning_rate = self._comm_get_data(trcode, "", rqname, i, "수익률(%)")

            quantity = Kiwoom.change_format(quantity)
            purchase_price = Kiwoom.change_format(purchase_price)
            current_price = Kiwoom.change_format(current_price)
            eval_profit_loss_price = Kiwoom.change_format(eval_profit_loss_price)
            earning_rate = Kiwoom.change_format2(earning_rate)

            self.opw00018_output['multi'].append([name, quantity, purchase_price, current_price, eval_profit_loss_price,
                                                  earning_rate])


    def strategy(self, name, time):
        try:

            list_1 = [k for k in self.dic.keys() if name in k ]
    
            
            name = self.dic[list_1[list_1.index(name+'_name')]]                   #종목 이름
            trcode = self.dic[list_1[list_1.index(name+'_ticker')]]               #티커 6자리
            status = self.dic[list_1[list_1.index(name+'_status')]]               #현재상태
            rebuy = self.dic[list_1[list_1.index(name+'_rebuy')]]                 #재매수 횟수 확인 상태 (1이면 재매수 상태로 진입)
            initial = self.dic[list_1[list_1.index(name+'_initial')]]             #처음 매수한 가격
            buy_count = self.dic[list_1[list_1.index(name+'_buy_count')]]         #살 가격(남은수량)
            sell_price = self.dic[list_1[list_1.index(name+'_sell_price')]]       #판매 가격
            rebuy_count = self.dic[list_1[list_1.index(name+'_rebuy_count')]]     #얼마만큼살지
            buy_total_price = self.dic[list_1[list_1.index(name+'_buy_total')]]   #입력 총금액
            hoga = self.dic[list_1[list_1.index(name+'_hoga')]]                   #호가
            start_price = self.dic[list_1[list_1.index(name+'_start_price')]]     #시가
            price = self.dic[list_1[list_1.index(name+'_price')]]                 #현재가
            if name+'_upper' in list_1:
                upper= self.dic[list_1[list_1.index(name+'_upper')]]               #5분봉 매수했을때 시가
            if name+'_middle' in list_1:
                middle = self.dic[list_1[list_1.index(name+'_middle')]]               #5분봉 매수했을때 고가
            if name+'_lower' in list_1:
                lower = self.dic[list_1[list_1.index(name+'_lower')]]               #5분봉 매수했을때 고가 
    
            else : return 
            if name+'_reach_upper' in list_1:
                reach_upper = self.dic[list_1[list_1.index(name+'_reach_upper')]]     #현재가 상단선 도달여부
            else : return
            if name+'_reach_middle' in list_1:
                reach_middle = self.dic[list_1[list_1.index(name+'_reach_middle')]]   #현재가 중단선 밑으로 떨어졌는지 여부
            else : return
            if name + '_reach_low' in list_1 :
                reach_low = self.dic[list_1[list_1.index(name+'_reach_low')]]   #현재가 하단선 밑으로 떨어졌는지 여부
                
            port_name = self.dic[list_1[list_1.index(name+'_port_name')]]  #포트이름
            
            
            format_price = format(int(price), ",")
        
            last_close = self.GetMasterLastPrice(trcode) #전일종가 가져오기
            
            #print("종목이름 : " + str(name) + "전일종가:" + str(last_close))
    
            #compare = self.dic[list_1[list_1.index(name+'_compare')]]             #현재가 전일대비       
           
            buy_number = int(int(buy_total_price) / int(price)) #매수할 수량
            
    
            format_price = format(int(price), ",")
            
            #last_close = self.GetMasterLastPrice(trcode) #전일종가 가져오기
            #self.ui.textEdit_2.append("이름: " +str(name) + "가격 :" + str(initial))
            #self.ui.textEdit_2.append("time" + str(time))
            #self.ui.textEdit_2.append("")

            #초기상태
            #포트에서 뜨면 매수
            if status == "초기상태" :
                self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, buy_number,  price ,"00", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "매수상태"
                self.dic[list_1[list_1.index(name+'_initial')]] = price
                self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_number 
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(255,0,0))
                self.ui.textEdit.append("매수")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + format_price + "원 "+ " 매수수량 : " + str(buy_number) + " 포트번호 : " + str(port_name) )
                self.ui.textEdit.append(" ")
                
            #매수 상태일때
            elif status == "매수상태":
                #9시 5분 이전
                if int(time[0:2]) == 9 and int(time[3:5]) <= 5  :
                    #3%이익시 청산
                    if (price - initial)/float(last_close)>= (self.profit_percent /100): 
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count, price ,"00", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.dic[list_1[list_1.index(name+'_reach_upper')]] = 0
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,0,0))
                        self.ui.textEdit.append("매도 ▲ : 매수 익절(1매수)")
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("시간 : " + str(time) + " | " +  "매도 | "+ name + " | 매수가 대비 이익 | " + "매도가격 : " + str(price))
                        self.ui.textEdit.append(" 매도수량 " + str(buy_count) + "주")
                        self.ui.textEdit.append(" ")
                    
                    #-1.5% 손실시 청산
                    elif (price - initial)/float(last_close) < -(self.sell_percent/100):
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count, price ,"00", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.dic[list_1[list_1.index(name+'_reach_upper')]] = 0
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(0,0,255))
                        self.ui.textEdit.append("매도 ▼ : 매수 손실(1매수)")
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("시간 : " + str(time) + " | " +  "매도 | "+ name + " | 매수가 대비 손실 | " + "매도가격 : " + str(price))
                        self.ui.textEdit.append(" 매도수량 " + str(buy_count) + "주")
                        self.ui.textEdit.append(" ")
                        
                #9시 5분이 넘어가면
                else :
                    #1,2번일때
                    #if initial >= middle:
                        #3%이익시 청산
                    if (price - initial)/float(last_close) >= (self.profit_percent /100)  : 
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count, price ,"00", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.dic[list_1[list_1.index(name+'_reach_upper')]] = 0
                        self.dic[list_1[list_1.index(name+'_sell_price')]] = price
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,0,0))
                        self.ui.textEdit.append("매도 ▲ : 매수 익절(1매수)")
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("시간 : " + str(time) + " | " +  "매도 | "+ name + " | 매수가 대비 이익 | " + "매도가격 : " + str(price))
                        self.ui.textEdit.append(" 매도수량 " + str(buy_count) + "주")
                        self.ui.textEdit.append(" ")
                    
                    #-1.5% 손실시 청산
                    elif (price - initial)/float(last_close) < -(self.sell_percent/100):
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count, price ,"00", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.dic[list_1[list_1.index(name+'_reach_upper')]] = 0
                        self.dic[list_1[list_1.index(name+'_sell_price')]] = price
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(0,0,255))
                        self.ui.textEdit.append("매도 ▼ : 매수 손실(1매수)")
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("시간 : " + str(time) + " | " +  "매도 | "+ name + " | 매수가 대비 손실 | " + "매도가격 : " + str(price))
                        self.ui.textEdit.append(" 매도수량 " + str(buy_count) + "주")
                        self.ui.textEdit.append(" ")
                    #3,4번일때
                   
                        """
                        #현재가 상단선 돌파
                        if price > upper and reach_upper == 0 and upper != 0:
                            self.dic[list_1[list_1.index(name+'_reach_upper')]] = 1
                            self.ui.textEdit.setFontPointSize(13)
                            self.ui.textEdit.setTextColor(QColor(255,51,153))
                            self.ui.textEdit.append("현재가 상단선 돌파(1매수) | " )
                            self.ui.textEdit.setFontPointSize(9)
                            self.ui.textEdit.setTextColor(QColor(0,0,0))
                            self.ui.textEdit.append("시간 : " + str(time) + " 종목 ㅣ " + str(name) + " | 현재가격 : " + str(price) + " | 상단선 " + str(upper))
                            self.ui.textEdit.append(" ")
                        #가격이 돌파후 하락하면
                        if price < upper and reach_upper == 1 and upper != 0 :
                            self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count, price ,"00", "" )
                            self.dic[list_1[list_1.index(name+'_status')]] = "재매수대기상태"
                            self.dic[list_1[list_1.index(name+'_reach_upper')]] = 0
                            self.dic[list_1[list_1.index(name+'_sell_price')]] = price
                            self.ui.textEdit.setFontPointSize(13)
                            self.ui.textEdit.setTextColor(QColor(0,0,255))
                            self.ui.textEdit.append("매도 ■ : 상단선 하락 매도(1매수)")
                            self.ui.textEdit.setFontPointSize(9)
                            self.ui.textEdit.setTextColor(QColor(0,0,0))
                            self.ui.textEdit.append("시간 : " + str(time) + " | " +  "매도 | "+ name + " | 상단선 하락 매도 | " + "매도가격 : " + str(price)+ " | 상단선 " + str(upper))
                            self.ui.textEdit.append(" 매도수량 " + str(buy_count) + "주")
                            self.ui.textEdit.append(" ")
                        
                        #-1.5% 손실시 청산
                        if (price - initial)/float(last_close) < -(self.sell_percent/100) and reach_upper == 0:
                            self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count, price ,"00", "" )
                            self.dic[list_1[list_1.index(name+'_status')]] = "재매수대기상태"
                            self.dic[list_1[list_1.index(name+'_reach_upper')]] = 0
                            self.dic[list_1[list_1.index(name+'_sell_price')]] = price
                            self.ui.textEdit.setFontPointSize(13)
                            self.ui.textEdit.setTextColor(QColor(0,0,255))
                            self.ui.textEdit.append("매도 ▼ : 매수 손실(1매수)")
                            self.ui.textEdit.setFontPointSize(9)
                            self.ui.textEdit.setTextColor(QColor(0,0,0))
                            self.ui.textEdit.append("시간 : " + str(time) + " | " +  "매도 | "+ name + " | 매수가 대비 손실 | " + "매도가격 : " + str(price))
                            self.ui.textEdit.append(" 매도수량 " + str(buy_count) + "주")
                            self.ui.textEdit.append(" ")
                        """
            
            elif status == "재매수대기상태":
                #현재가 중단선 밑으로 떨어진 경우
                if price < middle and sell_price > middle  and reach_middle == 0 and middle != 0:
                    self.dic[list_1[list_1.index(name+'_reach_middle')]] = 1
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,128,0))
                    self.ui.textEdit.append("현재가 중단선 밑 하락(재매수대기상태) | ")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("시간 : " + str(time) + " 종목 ㅣ " + str(name) + " | 현재가격 : " + str(price) + " | 중단선 : " + str(middle))
                    self.ui.textEdit.append(" ")
                
                
                    
                
                #현재가 중단선 밑으로 떨어졌다가 다시 상승하는 경우
                if price > middle and reach_middle == 1 and middle != 0:
                    self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, buy_number,  price ,"00", "" )
                    self.dic[list_1[list_1.index(name+'_status')]] = "재매수상태"
                    self.dic[list_1[list_1.index(name+'_initial')]] = price
                    self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_number 
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(255,0,0))
                    self.ui.textEdit.append("중단선 도달 : 재매수")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("시간 : " + str(time) + " | " + "재매수  :"+ name + " 매수가격 :" + format_price + "원 "+ " 매수수량 : " + str(buy_number) + " 포트번호 : " + str(port_name) )
                    self.ui.textEdit.append(" ")
                    
            
            elif status == "재매수상태":
                #3%이익시 청산
                if (price - initial)/float(last_close) >= (self.profit_percent /100)  : 
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count, price ,"00", "" )
                    self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                    self.dic[list_1[list_1.index(name+'_reach_upper')]] = 0
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(255,0,0))
                    self.ui.textEdit.append("매도 ▲ : 매수 익절(재매수)")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("시간 : " + str(time) + " | " +  "매도 | "+ name + " | 매수가 대비 이익 | " + "매도가격 : " + str(price))
                    self.ui.textEdit.append(" 매도수량 " + str(buy_count) + "주")
                    self.ui.textEdit.append(" ")
                
                #-1.5% 손실시 청산
                elif (price - initial)/float(last_close) < -(self.sell_percent/100):
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count, price ,"00", "" )
                    self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                    self.dic[list_1[list_1.index(name+'_reach_upper')]] = 0
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ▼ : 매수 손실(재매수)")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("시간 : " + str(time) + " | " +  "매도 | "+ name + " | 매수가 대비 손실 | " + "매도가격 : " + str(price))
                    self.ui.textEdit.append(" 매도수량 " + str(buy_count) + "주")
                    self.ui.textEdit.append(" ")
            
      
            elif status == "거래끝":
                self.ui.textEdit.append("거래종료 | 종목 : " + name )
                self.ui.textEdit.append(" ")
                self.dic[list_1[list_1.index(name+'_status')]] = ""


        except Exception as e:    # 모든 예외의 에러 메시지를 출력
            print('예외가 발생했습니다.', e)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    kiwoom.comm_connect() #연결
    

    
    
