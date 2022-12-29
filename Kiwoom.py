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
        
        
        
        self.dic = {}
        
        self.rebuy = 1 #재매수 횟수 (1번만 가능하도록)
        self.hoga = 0
        self.last_close = 0
        
        self.gudoc_count = 0 #종목 구독시 개수
        
        self.port_name = "" #포트 이름 저장변수
        
        self.stock_held = [] #보유종목리스트
        
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
        self.ui.pushButton_4.setEnabled(True)
        self.ui.pushButton_7.setEnabled(True)
        
        condition_name = str(self.condition_list['name'][0])
        nindex = str(self.condition_list['index'][0])
        
        self.ui.pushButton_2.clicked.connect(self.ui.check_port)
        self.ui.pushButton_3.clicked.connect(self.ui.delete_row)
        self.ui.pushButton_4.clicked.connect(self.ui.check_port2)
        self.ui.pushButton_7.clicked.connect(self.ui.delete_row2)
        
        condition_name2 = str(self.condition_list['name'][1])
        nindex2 = str(self.condition_list['index'][1])
       
        print("dasd" , self.condition_list ) 
       
        print(condition_name)
        print(condition_name2)
        print(nindex)
        print(nindex2)
        
        

    
    #조건검색 조회
    def _condition_search(self):
        self.sec_list = []
        self.sell_list = []
        print(self.ui.row_count)
        for i in range(self.ui.row_count):
            self.sec_list.append(self.ui.tableWidget_3.item(i,0).text())
        
        self.sell_list.append(self.ui.tableWidget_4.item(0,0).text())
       
        print(self.sec_list)
        print(self.sell_list)
   
        
        for i in range(len(self.condition_list['name'])):
            for j in self.sec_list:
                if self.condition_list['name'][i] == j:
                    a = self.dynamicCall("SendCondition(QString, QString, int, int)", "0156", str(self.condition_list['name'][i]), str(self.condition_list['index'][i]), 1)
                    if a==1:
                        self.ui.textEdit.append("조건검색 조회요청 성공 | port이름 : " + str(self.condition_list['name'][i]) )
                    elif a!=1:
                        self.ui.textEdit.append("조건검색 조회요청 실패 | port이름 : " + str(self.condition_list['name'][i]) )
               
            if self.condition_list['name'][i] == self.sell_list[0]:
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
        if self.gudoc_count == 100:
            self.ui.window_count +=1
            self.gudoc_count = 0

        
        for i in self.sec_list:
            if len(self.sec_list) == 1:
                if str(cond_name) == str(i) == self.sec_list[0] and self.ui.checkBox_2.isChecked():
                    self.ui.textEdit_2.append("실시간o: " + str(code))
                    self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
                if str(cond_name) == str(i) == self.sec_list[0] and self.ui.checkBox_2.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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

                       
                elif str(cond_name) == str(i) == self.sec_list[1] and self.ui.checkBox_3.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
                if str(cond_name) == str(i) == self.sec_list[0] and self.ui.checkBox_2.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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

                       
                elif str(cond_name) == str(i) == self.sec_list[1] and self.ui.checkBox_3.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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

                       
                elif str(cond_name) == str(i) == self.sec_list[2] and self.ui.checkBox_4.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
                if str(cond_name) == str(i) == self.sec_list[0] and self.ui.checkBox_2.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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

                       
                elif str(cond_name) == str(i) == self.sec_list[1] and self.ui.checkBox_3.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
                       
                elif str(cond_name) == str(i) == self.sec_list[2] and self.ui.checkBox_4.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
    
                elif str(cond_name) == str(i) == self.sec_list[3] and self.ui.checkBox_5.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
                if str(cond_name) == str(i) == self.sec_list[0] and self.ui.checkBox_2.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
                       
                elif str(cond_name) == str(i) == self.sec_list[1] and self.ui.checkBox_3.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
                       
                elif str(cond_name) == str(i) == self.sec_list[2] and self.ui.checkBox_4.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
    
                elif str(cond_name) == str(i) == self.sec_list[3] and self.ui.checkBox_5.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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
                elif str(cond_name) == str(i) == self.sec_list[4] and self.ui.checkBox_6.isChecked():
                   self.ui.textEdit_2.append("실시간o: " + str(code))
                   self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
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

        if cond_name == self.sell_list[0]:
            
            print("code : ", code)
            print("stock_list : ", self.stock_held)
            if code in self.stock_held:

                name = self.get_master_code_name(code)      
                list_1 = [k for k in self.dic.keys() if name in k ]
                
                trcode = self.dic[list_1[list_1.index(name+'_ticker')]]
                rebuy_count = self.dic[list_1[list_1.index(name+'_rebuy_count')]]
                status = self.dic[list_1[list_1.index(name+'_status')]] 
                self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(0,0,255))
                self.ui.textEdit.append("매도 ■ : 조건식 매도")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append(" | " + "매도 | "+ name + " | 조건식매도")
                self.ui.textEdit.append(" 매도수량 " + str(rebuy_count) + "주")
                self.ui.textEdit.append(" ")
                self.stock_held.remove(code)
                


####
    #실시간 조회관련 핸들
    def _handler_real_data(self, trcode, real_type, data):
        
        
        
        # 체결 시간 
        if real_type == "주식체결":
            time =  self.get_comm_real_data(trcode, 20)
            #date = datetime.datetime.now().strftime("%Y-%m-%d ")
            #time = datetime.datetime.strptime(time, "%H:%M:%S")
            time = time[:2] + ":" + time[2:4] + ":" + time[4:6]

            
            
            #print("체결시간 :", time)

        #호가
        hoga_1 = self.get_comm_real_data(trcode, 27)
        hoga_2 = self.get_comm_real_data(trcode, 28)
        
        
        if hoga_1 != "" and hoga_2 != "":
            hoga = float(hoga_1[1:]) - float(hoga_2[1:]) 
            

        #전일대비
        compare = self.get_comm_real_data(trcode, 12)


        # 현재가 
        price =  self.get_comm_real_data(trcode, 10)
        if price != "":
            price = float(price[1:])
            #print(trcode, ":", price)
            
        #시가
        start_price = self.get_comm_real_data(trcode, 16)
          
        for i in range(len(self.ui.ticker_list)):
            if trcode == self.ui.ticker_list[i]:
                #print(i, "번째 :", self.ui.stock_list[i])
                

                start_price = self.get_comm_real_data(trcode, 16)
                price = self.get_comm_real_data(trcode, 10)
                name = self.get_master_code_name(trcode)
                compare = self.get_comm_real_data(trcode, 12).strip()
                    
                    
                if start_price  == "" or compare == "" :
                    pass
                #self.ui.textEdit_2.append("시가 입력 대기중 :" + name )
                else:
                    start_price  = float(start_price[1:])
                    price = float(price[1:])
                    compare = float(compare)
                    
                    self.dic[name + '_start_price'] = start_price  
                    self.dic[name + '_price'] = price
                    self.dic[name + '_compare'] = compare
                    self.dic[name + '_hoga'] = hoga
                    
                        
                    #print("_handler_real_data :" , name)
                        
                    self.strategy(name, time)
                        
                    
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
        

        
        #매도조건 상태 2가지
        self.dic[name + '_sell_status1'] = '초기상태'
        self.dic[name + '_sell_status2'] = '초기상태'
            
        #재매수시 비율
        self.dic[name + '_sec_percent'] = 0
            
        #각 시점 최고가
        self.dic[name + '_price_avg'] = 0 
        
        
        #self.plainTextEdit.appendPlainText("거래준비완료 | 종목 :" + name )
        self.ui.textEdit.append("거래준비완료 | 종목 :" + name)
            
        #2%도달 여부(1매수용) (0도달x / 1 도달o )
        self.dic[name + '_reach_two_per'] = 0 

            
        #2%도달 여부(2매수용) (0도달x / 1 도달o )
        self.dic[name + '_reach_two_per2'] = 0 

        #self.pushButton_5.setEnabled(True)
        self.dic[name + "_compare_list"] = []
        self.dic[name + "_price_list"] = []

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


    def _opt10081(self, rqname, trcode):
        data_cnt = self._get_repeat_cnt(trcode, rqname) #데이터 갯수 확인

        for i in range(data_cnt): #시고저종 거래량 가져오기
            date = self._comm_get_data(trcode, "", rqname, i, "일자")
            open = self._comm_get_data(trcode, "", rqname, i, "시가")
            high = self._comm_get_data(trcode, "", rqname, i, "고가")
            low = self._comm_get_data(trcode, "", rqname, i, "저가")
            close = self._comm_get_data(trcode, "", rqname, i, "현재가")
            volume = self._comm_get_data(trcode, "", rqname, i, "거래량")

            self.ohlcv['date'].append(date)
            self.ohlcv['open'].append(int(open))
            self.ohlcv['high'].append(int(high))
            self.ohlcv['low'].append(int(low))
            self.ohlcv['close'].append(int(close))
            self.ohlcv['volume'].append(int(volume))
            
        
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
        price_list = self.dic[list_1[list_1.index(name+'_price_list')]]       #현재가 매수 리스트
        compare = self.dic[list_1[list_1.index(name+'_compare')]]             #현재가 전일대비
        compare_list = self.dic[list_1[list_1.index(name+'_compare_list')]]   #현재가 전일대비 평단가 구하는 리스트
        sec_percent = self.dic[list_1[list_1.index(name+'_sec_percent')]]     #compare 넣을 변수
        price_avg = self.dic[list_1[list_1.index(name+'_price_avg')]]       #2차 매수시 초기값 밑으로 내려갔는지
        
        if name+'_sell_status1' in list_1:
            sell_status_1 = self.dic[list_1[list_1.index(name+'_sell_status1')]]  #매도조건상태1
       
        if name+'_sell_status2' in list_1:
            sell_status_2 = self.dic[list_1[list_1.index(name+'_sell_status2')]]  #매도조건상태2
       
        buy_number = int(int(buy_total_price) / int(price)) #매수할 수량
        
        div_count = int(buy_number/5) #5호가 나눠서 매수할 수량
        
        format_price = format(int(price), ",")
        
        reach_two_per = self.dic[list_1[list_1.index(name+'_reach_two_per')]]  
        reach_two_per2 = self.dic[list_1[list_1.index(name+'_reach_two_per2')]]  
        
        
        #print("이름: " +str(name) + "가격 :" + str(initial))
        
        #초기상태
        if status == "초기상태" :
            self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, div_count,  price ,"00", "" )
            self.dic[list_1[list_1.index(name+'_status')]] = "1매수상태"
            self.dic[list_1[list_1.index(name+'_initial')]] = price
            self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_number - div_count
            self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count + div_count
            self.dic[list_1[list_1.index(name+'_compare_list')]].append(compare)
            self.dic[list_1[list_1.index(name+'_price_list')]].append(price)
            compare_list.append(compare)
            price_list.append(price)
            price_avg = sum(price_list) / len(price_list)
            self.dic[list_1[list_1.index(name+'_price_avg')]] = price_avg
            self.ui.textEdit.setFontPointSize(13)
            self.ui.textEdit.setTextColor(QColor(255,0,0))
            self.ui.textEdit.append("매수(5호가)")
            self.ui.textEdit.setFontPointSize(9)
            self.ui.textEdit.setTextColor(QColor(0,0,0))
            self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + format_price + "원 "+ str(compare) + " 매수수량 : " + str(div_count) + " 포트번호 : " + str(self.port_name) )
            self.ui.textEdit.append(" ")
            self.dic[list_1[list_1.index(name+'_sec_percent')]] =  compare
            
        elif status == "1매수상태":
            #4호가 진입시 매수
            if price == initial - hoga :
                self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, div_count,  initial - hoga ,"00", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "2매수상태"
                self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_number - div_count
                self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count + div_count
                self.dic[list_1[list_1.index(name+'_compare_list')]].append(compare)
                self.dic[list_1[list_1.index(name+'_price_list')]].append(price)
                compare_list.append(compare)
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(255,0,0))
                self.ui.textEdit.append("매수(4호가)")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + str(initial - hoga) + "원 "+ str(compare) + " 매수수량 : " + str(div_count) + " 포트번호 : " + str(self.port_name) )
                self.ui.textEdit.append("-------------------------------")
                self.ui.textEdit.append(" ")
            """    
            #안떨어지고 상승시 매수상태로 전환
            elif price >= initial:
                #2익절구간 도달시 표시
                if price >= price_avg + price_avg *0.02 and reach_two_per == 0 :
                    self.dic[list_1[list_1.index(name+'_reach_two_per')]] = 1
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,128,0))
                    self.ui.textEdit.append("▲ 2%익절구간 도달")  
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + name +" | 2% 익절구간 도달 ")
                    self.ui.textEdit.append(" ")
                else: 
                    self.ui.textEdit_2.append("대기중 | 종목 : " + name + " " + str( compare))
                
                #3% 찍었을때(상승x)
                if price >= price_avg + price_avg *0.03 :
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * rebuy_count
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                    self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ■ : 3% 도달")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name + " | 3%익절매도")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 " + str(rebuy_count) + "주")
                    self.ui.textEdit.append(" ")
            """
            
        elif status == "2매수상태":
            #3호가 진입시 매수
            if price == initial - 2*hoga:
                self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, div_count,  initial - 2*hoga ,"00", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "3매수상태"
                self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_number - div_count
                self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count + div_count
                self.dic[list_1[list_1.index(name+'_compare_list')]].append(compare)
                self.dic[list_1[list_1.index(name+'_price_list')]].append(price)
                compare_list.append(compare)
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(255,0,0))
                self.ui.textEdit.append("매수(3호가)")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + str(initial - 2*hoga) + "원 "+ str(compare) + " 매수수량 : " + str(div_count) + " 포트번호 : " + str(self.port_name) )
                self.ui.textEdit.append("-------------------------------")
                self.ui.textEdit.append(" ")
                
            #4호가에서 5호가로 오르면 남은 잔량 매수후 매수 상태로 전환
            elif price >= initial :
                self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, div_count,  initial ,"00", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "매수상태"
                self.dic[list_1[list_1.index(name+'_buy_count')]] = 0
                self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count + div_count
                self.dic[list_1[list_1.index(name+'_compare_list')]].append(compare)
                self.dic[list_1[list_1.index(name+'_price_list')]].append(price)
                compare_list.append(compare)
                price_list.append(price)
                price_avg = sum(price_list) / len(price_list)
                self.dic[list_1[list_1.index(name+'_price_avg')]] = price_avg
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(255,0,0))
                self.ui.textEdit.append("매수(4호가->5호가)")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + str(initial) + "원 "+ str(compare) + " 매수수량 : " + str(div_count) + " 포트번호 : " + str(self.port_name) )
                self.ui.textEdit.append(" ")
            
            
            
        elif status == "3매수상태":
            #2호가 진입시 매수
            if price == initial - 3*hoga:
                self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, div_count,  initial - 3*hoga ,"00", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "4매수상태"
                self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_number - div_count
                self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count + div_count
                self.dic[list_1[list_1.index(name+'_compare_list')]].append(compare)
                self.dic[list_1[list_1.index(name+'_price_list')]].append(price)
                compare_list.append(compare)
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(255,0,0))
                self.ui.textEdit.append("매수(2호가)")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + str(initial - 3*hoga) + "원 "+ str(compare) + " 매수수량 : " + str(div_count) + " 포트번호 : " + str(self.port_name))
                self.ui.textEdit.append("-------------------------------")
                self.ui.textEdit.append(" ")
                
            #3호가에서 4호가로 오르면 남은 잔량 매수후 매수 상태로 전환
            elif price >= initial  :
                self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, div_count,  initial ,"00", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "매수상태"
                self.dic[list_1[list_1.index(name+'_buy_count')]] = 0
                self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count + div_count
                self.dic[list_1[list_1.index(name+'_compare_list')]].append(compare)
                self.dic[list_1[list_1.index(name+'_price_list')]].append(price)
                compare_list.append(compare)
                price_list.append(price)
                price_avg = sum(price_list) / len(price_list)
                self.dic[list_1[list_1.index(name+'_price_avg')]] = price_avg
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(255,0,0))
                self.ui.textEdit.append("매수(3호가->5호가)")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + str(initial) + "원 "+ str(compare) + " 매수수량 : " + str(div_count) + " 포트번호 : " + str(self.port_name))
                self.ui.textEdit.append(" ")
                
        elif status == "4매수상태":
            #1호가 진입시 매수
            if price == initial - 4*hoga:
                self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, div_count,  initial - 4*hoga ,"00", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "매수상태"
                self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_number - div_count
                self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count + div_count
                self.dic[list_1[list_1.index(name+'_compare_list')]].append(compare)
                self.dic[list_1[list_1.index(name+'_price_list')]].append(price)
                compare_list.append(compare)
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(255,0,0))
                self.ui.textEdit.append("매수(1호가)")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + str(initial - 4*hoga) + "원 "+ str(compare) + " 매수수량 : " + str(div_count) + " 포트번호 : " + str(self.port_name))
                self.ui.textEdit.append("-------------------------------")
                self.ui.textEdit.append(" ")
                
            #2호가에서 3호가로 오르면 남은 잔량 매수후 매수 상태로 전환
            elif price >= initial  :
                self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, div_count,  initial ,"00", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "매수상태"
                self.dic[list_1[list_1.index(name+'_buy_count')]] = 0
                self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count + div_count
                self.dic[list_1[list_1.index(name+'_compare_list')]].append(compare)
                self.dic[list_1[list_1.index(name+'_price_list')]].append(price)
                compare_list.append(compare)
                price_list.append(price)
                price_avg = sum(price_list) / len(price_list)
                self.dic[list_1[list_1.index(name+'_price_avg')]] = price_avg
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(255,0,0))
                self.ui.textEdit.append("매수(2호가->5호가)")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + str(initial) + "원 "+ str(compare) + " 매수수량 : " + str(div_count) + " 포트번호 : " + str(self.port_name) )
                self.ui.textEdit.append(" ")
  
        elif status == "거래끝":
            self.ui.textEdit.append("거래종료 | 종목 : " + name )
            self.ui.textEdit.append(" ")
            self.dic[list_1[list_1.index(name+'_status')]] = ""

  

    
        """
        #매수 상태
        elif status == "매수상태":
            #2익절구간 도달시 표시
            if price >= price_avg + price_avg *0.02 and reach_two_per == 0 :
                self.dic[list_1[list_1.index(name+'_reach_two_per')]] = 1
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(0,128,0))
                self.ui.textEdit.append("▲ 2%익절구간 도달")  
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("->시간 : " + str(time) + " | " + name +" | 2% 익절구간 도달 ")
                self.ui.textEdit.append(" ")
            else: 
                self.ui.textEdit_2.append("대기중 | 종목 : " + name + " " + str( compare))
            
            #3% 찍었을때(상승x)
            if price >= price_avg + price_avg *0.03 :
                self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                self.dic[list_1[list_1.index(name+'_sell_price')]] = price * rebuy_count
                self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(0,0,255))
                self.ui.textEdit.append("매도 ■ : 3% 도달")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name + " | 3%익절매도")
                self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 " + str(rebuy_count) + "주")
                self.ui.textEdit.append(" ")
                
            if price <= price_avg *0.97 :
                self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                self.dic[list_1[list_1.index(name+'_sell_price')]] = price * rebuy_count
                self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(0,0,255))
                self.ui.textEdit.append("매도 ■ : 3% 밑도달(강제청산)")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수 | "+ name + " | 강제청산")
                self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 " + str(rebuy_count) + "주")
                self.ui.textEdit.append(" ")
        """


                 
  
            

    
        



if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    kiwoom.comm_connect() #연결
    

    
    
