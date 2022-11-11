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
            
    #로컬에 사용자 조건식 저장 성공 여부 확인
    def _on_receive_condition_ver(self):
        condition_list = {"index": [], "name": []}
        temporary_condition_list = self.dynamicCall("GetConditionNameList()").split(";")
        print(temporary_condition_list)
    
        for data in temporary_condition_list :
            try:
                a = data.split("^")
                condition_list['index'].append(str(a[0]))
                condition_list['name'].append(str(a[1]))
            except IndexError:
                pass
            
        condition_name = str(condition_list['name'][0])
        nindex = str(condition_list['index'][0])
        
        
        condition_name2 = str(condition_list['name'][1])
        nindex2 = str(condition_list['index'][1])
       
        print(condition_name)
        print(condition_name2)
        print(nindex)
        print(nindex2)
        
        a = self.dynamicCall("SendCondition(QString, QString, int, int)", "0156", str(condition_name), nindex, 1)
        if a==1:
            self.ui.textEdit.append("조건검색 조회요청 성공")
        elif a!=1:
            self.ui.textEdit.append("조건검색 조회요청 실패")
        
    #조건검색 조회 응답
    def _on_receive_tr_condition(self, scrno, codelist, conditionname, nnext):
        self.code_list = []
        codelist_split = codelist.split(';')
        for i in codelist_split:
            self.code_list.append(i)
            
            
        print("실시간x:" , self.code_list)
        

        
        '''
        for i in self.code_list:
            if i != '':
                name = self.get_master_code_name(i)
                self.dic[name + '_ticker'] = i
                self.dic[name + '_status'] = '초기상태'
                self.dic[name + '_buy_count'] = 0
                self.dic[name + '_sell_price'] = 0
                self.dic[name + '_rebuy_count'] = 0
                
                
        print(self.dic)
        '''
    
    #실시간 조건검색 응답(실시간으로 들어왔을때 전략에 들어가게끔만들기)
    def _handler_real_condition(self, code, type, cond_name, cond_index):
        #self.ui.textEdit.append("실시간o: " + str(cond_name) +  str(code) + str(type)) 
        print("실시간o: " + str(cond_name) +  str(code) + str(type)) 
        self.ui.textEdit_2.append("실시간o: " + str(code))
        self.ui.textEdit_2.append("실시간o포트번호: " + str(cond_name))
        
        
        if code not in self.ui.ticker_list:
            self.ui.ticker_list.append(code)

        if code not in self.dic.values() and code != "":
            self.ready_trade(code)
        
        
        
        if self.ui.gudoc_status == 0:
            self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "0")
            self.ui.window_count += 1
            self.ui.gudoc_status = 1
            print('구독성공')
        elif self.ui.gudoc_status != 0 :
            self.SetRealReg(1000 +self.ui.window_count , code, "20;10", "1")
            self.ui.window_count += 1
            print('구독성공2')
        
        print(self.ui.gudoc_status)
        print(self.ui.window_count)
        print(self.dic)
        print(self.ui.ticker_list)

####
    #실시간 조회관련 핸들
    def _handler_real_data(self, trcode, real_type, data):
        
        print("_handler_real_data")
        
        # 체결 시간 
        if real_type == "주식체결":
            time =  self.get_comm_real_data(trcode, 20)
            #date = datetime.datetime.now().strftime("%Y-%m-%d ")
            #time = datetime.datetime.strptime(time, "%H:%M:%S")
            time = time[:2] + ":" + time[2:4] + ":" + time[4:6]

            
            
            print("체결시간 :", time)


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
                        
                    #print("3개 list", self.dic)
                        
                        
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
        self.dic[name + '_init_under'] = 0 
        
        
        #self.plainTextEdit.appendPlainText("거래준비완료 | 종목 :" + name )
        self.ui.textEdit.append("거래준비완료 | 종목 :" + name)
            
        #2%도달 여부(1매수용) (0도달x / 1 도달o )
        self.dic[name + '_reach_two_per'] = 0 

            
        #2%도달 여부(2매수용) (0도달x / 1 도달o )
        self.dic[name + '_reach_two_per2'] = 0 

        #self.pushButton_5.setEnabled(True)

        

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
        
        name = str(self.get_chejan_data(302)).strip()
        
        list_1 = [k for k in self.dic.keys() if name in k ]
  
        print(gubun)
        print(self.get_chejan_data(9203))
        print(self.get_chejan_data(302))
        print(self.get_chejan_data(900))
        print(self.get_chejan_data(901))


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
        initial = self.dic[list_1[list_1.index(name+'_initial')]]             #재매수 조건 때 각 라인의 가격
        buy_count = self.dic[list_1[list_1.index(name+'_buy_count')]]         #얼마큼 산지
        sell_price = self.dic[list_1[list_1.index(name+'_sell_price')]]       #판매 가격
        rebuy_count = self.dic[list_1[list_1.index(name+'_rebuy_count')]]     #재매수 할때 팔고 남은 금맥만큼 사기
        buy_total_price = self.dic[list_1[list_1.index(name+'_buy_total')]]   #입력 총금액
        

        #hoga = self.dic[list_1[list_1.index(name+'_hoga')]]                   #호가
        start_price = self.dic[list_1[list_1.index(name+'_start_price')]]     #시가
        price = self.dic[list_1[list_1.index(name+'_price')]]                 #현재가
        compare = self.dic[list_1[list_1.index(name+'_compare')]]             #현재가 전일대비
        sec_percent = self.dic[list_1[list_1.index(name+'_sec_percent')]]     #compare 넣을 변수
        init_under = self.dic[list_1[list_1.index(name+'_init_under')]]       #2차 매수시 초기값 밑으로 내려갔는지
        
        if name+'_sell_status1' in list_1:
            sell_status_1 = self.dic[list_1[list_1.index(name+'_sell_status1')]]  #매도조건상태1
       
        if name+'_sell_status2' in list_1:
            sell_status_2 = self.dic[list_1[list_1.index(name+'_sell_status2')]]  #매도조건상태2
       
        buy_number = int(int(buy_total_price) / int(price)) #매수할 수량
        
        format_price = format(int(price), ",")
        
        reach_two_per = self.dic[list_1[list_1.index(name+'_reach_two_per')]]  
        reach_two_per2 = self.dic[list_1[list_1.index(name+'_reach_two_per2')]]  

        
        #초기상태
        if status == "초기상태":

            self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, buy_number,  0 ,"03", "" )
            self.dic[list_1[list_1.index(name+'_status')]] = "매수상태"
            self.dic[list_1[list_1.index(name+'_initial')]] = price
            self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_number
            self.ui.textEdit.setFontPointSize(13)
            self.ui.textEdit.setTextColor(QColor(255,0,0))
            self.ui.textEdit.append("매수")
            self.ui.textEdit.setFontPointSize(9)
            self.ui.textEdit.setTextColor(QColor(0,0,0))
            self.ui.textEdit.append("시간 : " + str(time) + " | " + "1매수  :"+ name + " 매수가격 :" + format_price + "원 "+ str(compare) + " 매수수량 : " + str(buy_number))
            self.ui.textEdit.append("-------------------------------")
            self.ui.textEdit.append("도달지점 | 3% => " + str(round((price + price *0.03), 1)) + " 7% => "+ str(round((price + price *0.07), 1)) + " 14% => "+ str(round((price + price *0.14), 1)) )
            self.ui.textEdit.append(" ")
            self.dic[list_1[list_1.index(name+'_sec_percent')]] =  compare


    
        #매수 상태
        elif status == "매수상태":
            #강제 청산 
            #2%도달 못했으면(상승x)
            if reach_two_per == 0  :

                #하단선 밑 1.8%
                if price <= initial - 0.012*initial :
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_status')]] = "재매수대기상태"
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * buy_count
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("◀ 매도 : 매수가 밑 1.2%")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name + " | 매수가 밑 1.2%지점 도달")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 100% " + str(buy_count) + "주")
                    self.ui.textEdit.append(" ")
                    
                    
            #2%익절구간 못찍었으면
            elif reach_two_per == 1 :
                if price <= initial :
                    per_count50 = int(round(buy_count * 0.5, 0))
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, per_count50,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * per_count50 #남은잔고
                    self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_count - per_count50 #남은 수량
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "50익절상태2"
                    self.dic[list_1[list_1.index(name+'_reach_two_per')]] = 5
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ■ : 매수가 매도(회귀)")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수가 매도 | "+ name + " | 매수가 매도(회귀)")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(per_count50) + "주")
                    self.ui.textEdit.append(" ")
    
                    
            #2% 찍고 3% 못찍었을때
            elif reach_two_per == 2 :
                if price <= initial :
                    per_count50 = int(round(buy_count * 0.5, 0))
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, per_count50,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * per_count50 #남은잔고
                    self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_count - per_count50 #남은 수량
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "50익절상태"
                    self.dic[list_1[list_1.index(name+'_reach_two_per')]] = 5
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ■ : 매수가 매도(회귀)")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수 | "+ name + " | 매수가 매도(회귀)")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(per_count50) + "주")
                    self.ui.textEdit.append(" ")
            
            #3% 찍었을때(상승x)
            elif reach_two_per == 3 :
                if price <= initial :
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * buy_count
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                    self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ■ : 매수가 매도(회귀)")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수 | "+ name + " | 매수가 매도(회귀)")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(buy_count) + "주")
                    self.ui.textEdit.append(" ")
                
            
            #3% 찍었을때(상승o)
            elif reach_two_per == 4 :
                if compare <= sec_percent + 3 :
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * buy_count
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                    self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ■ : 3% 익절구간 하락")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수| "+ name + " | 3% 익절구간 하락")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(buy_count) + "주")
                    self.ui.textEdit.append(" ")
                    
            #다시 3% 찍으면 50% 매도
            elif reach_two_per == 5:
                if compare >= sec_percent + 3 :
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * buy_count
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                    self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(255,102,255))
                    self.ui.textEdit.append("매도 ▶ : 3%익절구간 도달")   
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수 | "+ name + " | 3%익절구간 도달")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(buy_count) + "주")
                    self.ui.textEdit.append(" ")
                
                
    
                
    
            #매도 조건 만들기
            #종목별 시가 등락률 계산하기
            #시가등락률 0미만
            if sec_percent < 20 :
                if sell_status_1 =="초기상태" : 
                    if compare > sec_percent  and reach_two_per == 0 :
                        self.dic[list_1[list_1.index(name+'_reach_two_per')]] = 1
                        
                    
                    if compare >= sec_percent + 2 and reach_two_per == 1 :
                        self.dic[list_1[list_1.index(name+'_reach_two_per')]] = 2
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(0,128,0))
                        self.ui.textEdit.append("▲ 2%익절구간 도달")  
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + name +" | 2% 익절구간 도달 ")
                        self.ui.textEdit.append(" ")
                        
                    
                    if compare >= sec_percent + 3 : #기준봉매매 라인의 합이 3% 되었을 때)
                        per_count7 = int(round(buy_count * 0.5, 0))
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, per_count7,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_buy_count')]] = buy_count - per_count7 #남은 수량
                        self.dic[list_1[list_1.index(name+'_sell_price')]] +=  per_count7 *price  #남은 잔고 
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "3도달상태"
                        self.dic[list_1[list_1.index(name+'_reach_two_per')]] = 3
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,102,255))
                        self.ui.textEdit.append("매도 ▶ : 3%익절구간 도달")   
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name +" | 3%익절구간 도달 ")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str( compare )   + " 매도수량 : 50% " + str(per_count7) + "주")
                        self.ui.textEdit.append(" ")

                          
                        
                    else: 
                        self.ui.textEdit_2.append("3%익절구간 도달 대기중 | 종목 : " + name + " " + str( compare))
              
                            
                elif sell_status_1 == "3도달상태":
                    if compare > sec_percent + 3 and reach_two_per == 3 :
                        self.dic[list_1[list_1.index(name+'_reach_two_per')]] = 4
                        
                    if compare >= sec_percent + 7:
 
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count ,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.dic[list_1[list_1.index(name+'_buy_count')]] = 0  #남은 수량
                        self.dic[list_1[list_1.index(name+'_sell_price')]] +=  buy_count *price  #남은 잔고 
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,102,255))
                        self.ui.textEdit.append("매도 ▶ : 7%익절구간 도달")  
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name +" | 7%익절구간 도달  ")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str( compare )   + " 매도수량 : 50% " + str(buy_count) + "주")
                        self.ui.textEdit.append(" ")

                        
                    else: 
                        self.ui.textEdit_2.append("7%익절구간 도달 대기중 | 종목 : " + name +" " +  str( compare))




                #기준선 찍어서 50% 익절했을 때
                elif sell_status_1 == "50익절상태":
                    #하단선 밑 1.8%
                    if price <= initial - 0.012*initial :
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "재매수대기상태"
                        self.dic[list_1[list_1.index(name+'_sell_price')]] = price * buy_count
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(0,0,255))
                        self.ui.textEdit.append("◀ 매도 : 매수가 밑 1.2%")
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name + " | 매수가 밑 1.2%지점 도달")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(buy_count) + "주")
                        self.ui.textEdit.append(" ")
                        
                    #다시 3% 찍으면 50% 매도
                    if compare >= sec_percent + 3 : #기준봉매매 라인의 합이 3% 되었을 때)
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_sell_price')]] +=  buy_count *price  #남은 잔고 
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,102,255))
                        self.ui.textEdit.append("매도 ▶ : 3%익절구간 도달")   
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name +" | 3%익절구간 도달 ")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str( compare )   + " 매도수량 : 50% " + str(buy_count) + "주")
                        self.ui.textEdit.append(" ")
   
                        
                elif sell_status_1 == "50익절상태2":
                    if price <= initial - 0.008*initial :
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "재매수대기상태"
                        self.dic[list_1[list_1.index(name+'_sell_price')]] = price * buy_count
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(0,0,255))
                        self.ui.textEdit.append("◀ 매도 : 매수가 밑 0.8%")
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name + " | 매수가 밑 0.8%지점 도달")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(buy_count) + "주")
                        self.ui.textEdit.append(" ")
                        
                    #다시 3% 찍으면 50% 매도
                    if compare >= sec_percent + 3 : #기준봉매매 라인의 합이 3% 되었을 때)
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, buy_count,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_sell_price')]] +=  buy_count *price  #남은 잔고 
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,102,255))
                        self.ui.textEdit.append("매도 ▶ : 3%익절구간 도달")   
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name +" | 3%익절구간 도달 ")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str( compare )   + " 매도수량 : 50% " + str(buy_count) + "주")
                        self.ui.textEdit.append(" ")

                    
        

            
        #재매수상태
        elif status == "재매수대기상태":
            sell_count = int(int(sell_price) / int(price))
            #현재가가 각 라인에 도달하면 매수
            
            if price <= initial and init_under == 0 : 
                self.dic[list_1[list_1.index(name+'_init_under')]] = 1
            
            if price >= initial + initial*0.008 and init_under == 1:
                self.send_order('send_order', "0101", self.ui.account_number, 1, trcode, sell_count,  0 ,"03", "" )
                self.dic[list_1[list_1.index(name+'_status')]] = "매수상태2"
                self.dic[list_1[list_1.index(name+'_initial')]] = price
                self.dic[list_1[list_1.index(name+'_rebuy_count')]] = sell_count
                self.ui.textEdit.setFontPointSize(13)
                self.ui.textEdit.setTextColor(QColor(255,0,0))
                self.ui.textEdit.append("매수")
                self.ui.textEdit.setFontPointSize(9)
                self.ui.textEdit.setTextColor(QColor(0,0,0))
                self.ui.textEdit.append("시간 : " + str(time) + " | " + "2매수 :"+ name + " 2매수가격 :" + format_price + "원 "+ str(compare) + " 2매수수량 : " + str(sell_count))
                self.ui.textEdit.append("-------------------------------")
                self.ui.textEdit.append("도달지점 | 3% => " + str(round((price + price *0.03), 1)) + " 7% => "+ str(round((price + price *0.07), 1)) + " 14% => "+ str(round((price + price *0.14), 1)) )
                self.ui.textEdit.append(" ")
                self.dic[list_1[list_1.index(name+'_sec_percent')]] =  compare
         #매수상태2
                 #매수 상태
        #매수 상태
        elif status == "매수상태2":
            #강제 청산 
            #2%도달 못했으면(상승x)
            if reach_two_per2 == 0  :

                #하단선 밑 1.8%
                if price <= initial - 0.012*initial :
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_status')]] = "재매수대기상태"
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * rebuy_count
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("◀ 매도 : 매수가 밑 1.2%")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name + " | 매수가 밑 1.2%지점 도달")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 100% " + str(rebuy_count) + "주")
                    self.ui.textEdit.append(" ")
                    
                    
            #2%익절구간 못찍었으면
            elif reach_two_per2 == 1 :
                if price <= initial :
                    per_count50 = int(round(rebuy_count * 0.5, 0))
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, per_count50,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * per_count50 #남은잔고
                    self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count - per_count50 #남은 수량
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "50익절상태2"
                    self.dic[list_1[list_1.index(name+'_reach_two_per2')]] = 5
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ■ : 매수가 매도(회귀)")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수가 매도 | "+ name + " | 매수가 매도(회귀)")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(per_count50) + "주")
            
                    
            #2% 찍고 3% 못찍었을때
            elif reach_two_per2 == 2 :
                if price <= initial :
                    per_count50 = int(round(rebuy_count * 0.5, 0))
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, per_count50,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * per_count50 #남은잔고
                    self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count - per_count50 #남은 수량
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "50익절상태"
                    self.dic[list_1[list_1.index(name+'_reach_two_per2')]] = 5
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ■ : 매수가 매도(회귀)")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수 | "+ name + " | 매수가 매도(회귀)")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(per_count50) + "주")
                    self.ui.textEdit.append(" ")
            
            #3% 찍었을때(상승x)
            elif reach_two_per2 == 3 :
                if price <= initial :
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * rebuy_count
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                    self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ■ : 매수가 매도(회귀)")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수 | "+ name + " | 매수가 매도(회귀)")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(rebuy_count) + "주")
                    self.ui.textEdit.append(" ")
                
            
            #3% 찍었을때(상승o)
            elif reach_two_per2 == 4 :
                if compare <= sec_percent + 3 :
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * rebuy_count
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                    self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(0,0,255))
                    self.ui.textEdit.append("매도 ■ : 3% 익절구간 하락")
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수| "+ name + " | 3% 익절구간 하락")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(rebuy_count) + "주")
                    self.ui.textEdit.append(" ")
                    
            #다시 3% 찍으면 50% 매도
            elif reach_two_per2 == 5:
                if compare >= sec_percent + 3 :
                    self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                    self.dic[list_1[list_1.index(name+'_sell_price')]] = price * rebuy_count
                    self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                    self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                    self.ui.textEdit.setFontPointSize(13)
                    self.ui.textEdit.setTextColor(QColor(255,102,255))
                    self.ui.textEdit.append("매도 ▶ : 3%익절구간 도달")   
                    self.ui.textEdit.setFontPointSize(9)
                    self.ui.textEdit.setTextColor(QColor(0,0,0))
                    self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매수 | "+ name + " | 3%익절구간 도달")
                    self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(rebuy_count) + "주")
                    self.ui.textEdit.append(" ")
                
                
    
                
    
            #매도 조건 만들기
            #종목별 시가 등락률 계산하기
            #시가등락률 0미만
            if sec_percent < 20 :
                if sell_status_1 =="초기상태" : 
                    if compare > sec_percent  and reach_two_per2 == 0 :
                        self.dic[list_1[list_1.index(name+'_reach_two_per2')]] = 1
                        
                    
                    if compare >= sec_percent + 2 and reach_two_per2 == 1 :
                        self.dic[list_1[list_1.index(name+'_reach_two_per2')]] = 2
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(0,128,0))
                        self.ui.textEdit.append("▲ 2%익절구간 도달")  
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + name +" | 2% 익절구간 도달 ")
                        self.ui.textEdit.append(" ")
                        
                    
                    if compare >= sec_percent + 3 : #기준봉매매 라인의 합이 3% 되었을 때)
                        per_count7 = int(round(rebuy_count * 0.5, 0))
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, per_count7,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_rebuy_count')]] = rebuy_count - per_count7 #남은 수량
                        self.dic[list_1[list_1.index(name+'_sell_price')]] +=  per_count7 *price  #남은 잔고 
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "3도달상태"
                        self.dic[list_1[list_1.index(name+'_reach_two_per2')]] = 3
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,102,255))
                        self.ui.textEdit.append("매도 ▶ : 3%익절구간 도달")   
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name +" | 3%익절구간 도달 ")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str( compare )   + " 매도수량 : 50% " + str(per_count7) + "주")
                        self.ui.textEdit.append(" ")

                          
                        
                    else: 
                        self.ui.textEdit_2.append("3%익절구간 도달 대기중 | 종목 : " + name + " " + str( compare))
              
                            
                elif sell_status_1 == "3도달상태":
                    if compare > sec_percent + 3 and reach_two_per2 == 3 :
                        self.dic[list_1[list_1.index(name+'_reach_two_per2')]] = 4
                        
                    if compare >= sec_percent + 7:
 
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count ,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.dic[list_1[list_1.index(name+'_rebuy_count')]] = 0  #남은 수량
                        self.dic[list_1[list_1.index(name+'_sell_price')]] +=  rebuy_count *price  #남은 잔고 
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,102,255))
                        self.ui.textEdit.append("매도 ▶ : 7%익절구간 도달")  
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name +" | 7%익절구간 도달  ")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str( compare )   + " 매도수량 : 50% " + str(rebuy_count) + "주")
                        self.ui.textEdit.append(" ")

                        
                    else: 
                        self.ui.textEdit_2.append("7%익절구간 도달 대기중 | 종목 : " + name +" " +  str( compare))




                #기준선 찍어서 50% 익절했을 때
                elif sell_status_1 == "50익절상태":
                    #하단선 밑 1.8%
                    if price <= initial - 0.012*initial :
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "재매수대기상태"
                        self.dic[list_1[list_1.index(name+'_sell_price')]] = price * rebuy_count
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(0,0,255))
                        self.ui.textEdit.append("◀ 매도 : 매수가 밑 1.2%")
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name + " | 매수가 밑 1.2%지점 도달")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(rebuy_count) + "주")
                        self.ui.textEdit.append(" ")
                        
                    #다시 3% 찍으면 50% 매도
                    if compare >= sec_percent + 3 : #기준봉매매 라인의 합이 3% 되었을 때)
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_sell_price')]] +=  rebuy_count *price  #남은 잔고 
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,102,255))
                        self.ui.textEdit.append("매도 ▶ : 3%익절구간 도달")   
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name +" | 3%익절구간 도달 ")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str( compare )   + " 매도수량 : 50% " + str(rebuy_count) + "주")
                        self.ui.textEdit.append(" ")
   
                        
                elif sell_status_1 == "50익절상태2":
                    if price <= initial - 0.008*initial :
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_status')]] = "재매수대기상태"
                        self.dic[list_1[list_1.index(name+'_sell_price')]] = price * rebuy_count
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(0,0,255))
                        self.ui.textEdit.append("◀ 매도 : 매수가 밑 0.8%")
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name + " | 매수가 밑 0.8%지점 도달")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str(compare)   + " 매도수량 : 50% " + str(rebuy_count) + "주")
                        self.ui.textEdit.append(" ")
                        
                    #다시 3% 찍으면 50% 매도
                    if compare >= sec_percent + 3 : #기준봉매매 라인의 합이 3% 되었을 때)
                        self.send_order('send_order', "0101", self.ui.account_number, 2, trcode, rebuy_count,  0 ,"03", "" )
                        self.dic[list_1[list_1.index(name+'_sell_price')]] +=  rebuy_count *price  #남은 잔고 
                        self.dic[list_1[list_1.index(name+'_sell_status1')]] = "초기상태"
                        self.dic[list_1[list_1.index(name+'_status')]] = "거래끝"
                        self.ui.textEdit.setFontPointSize(13)
                        self.ui.textEdit.setTextColor(QColor(255,102,255))
                        self.ui.textEdit.append("매도 ▶ : 3%익절구간 도달")   
                        self.ui.textEdit.setFontPointSize(9)
                        self.ui.textEdit.setTextColor(QColor(0,0,0))
                        self.ui.textEdit.append("->시간 : " + str(time) + " | " + "1매도 | "+ name +" | 3%익절구간 도달 ")
                        self.ui.textEdit.append("매도가격 :" + format_price + " 원 " + str( compare )   + " 매도수량 : 50% " + str(rebuy_count) + "주")
                        self.ui.textEdit.append(" ")

                    
        


  
   
        elif status == "거래끝":
            self.ui.textEdit.append("거래종료 | 종목 : " + name )
            self.ui.textEdit.append(" ")
            self.dic[list_1[list_1.index(name+'_status')]] = ""

            

  
                 
  
            

    
        



if __name__ == "__main__":
    app = QApplication(sys.argv)
    kiwoom = Kiwoom()
    kiwoom.comm_connect() #연결
    

    
    
