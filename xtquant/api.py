#!/usr/bin/env python
# -*- coding: gbk -*-
#__author__ = 'gokoushiro'
import sys, traceback, os
from .net.RPCClient import request as rpcRequest

__all__ = [
    'write_file',
    'read_file',
    'get_last_volume',
    'get_sector',
    'get_industry',
    'get_stock_list_in_sector',
    'get_weight_in_index',
    'get_contract_multiplier',
    'get_risk_free_rate',
    'get_financial_data',
    'get_market_data',
    'get_divid_factors',
    'get_main_contract',
    'timetag_to_date_time',
    'get_trading_dates',
    'get_factor_data',
    'get_option_list',
    'get_his_contract_list',
    'get_instrumentdetail',
    'get_option_detail_data',
    'get_option_iv',
    'bsm_price',
    'bsm_iv'
]

def try_except(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            exc_type, exc_instance, exc_traceback = sys.exc_info()
            formatted_traceback = ''.join(traceback.format_tb(exc_traceback))
            message = '\n{0} raise {1}:{2}'.format(
                formatted_traceback,
                exc_type.__name__,
                exc_instance
            )
            # raise exc_type(message)
            print(message)
            return None

    return wrapper


CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), 'config', 'formulaserver', 'formulaserver.ini')
#ADDR = '127.0.0.1:58600'
ADDR = ''


def get_address():
    global ADDR
    if not ADDR:
        import configparser
        config = configparser.ConfigParser()
        if config.read(CONFIG_PATH):
            addr = config.get('server_formula', 'address')
            port = addr.split(':')[1]
            ADDR = '127.0.0.1:{}'.format(port)
        else:
            print('{} not found'.format(CONFIG_PATH))
            raise
    return ADDR

def request(func_name, param_dict):
    import time
    address = get_address()
    resp = rpcRequest(address, func_name, param_dict, timeout=10)
    return resp


def write_file(file_path, file_content):
    '''Write File'''
    return writeFile(file_path, file_content)

@try_except
def writeFile(file_path, file_content):
    with open(file_path, 'w') as f:
        f.write(file_content)
    return True


def read_file(file_path):
    '''Read File'''
    return readFile(file_path)

@try_except
def readFile(file_path):
    with open(file_path, 'r') as f:
        content = f.read()
    return content


def get_last_volume(stock_code):
    '''
    获取最新流通股本
    :param stock_code: (str)股票代码
    :return: float
    '''
    return getLastVolume(stock_code)

@try_except
def getLastVolume(stock_code):
    resp = request('getLastVolume', {'stockCode': stock_code})
    return resp.get('result', 0)


def get_sector(sector_code, realtime=0):
    '''
    取板块成份股，只支持取指数成份股
    :param sector_code: (str)板块 '[STOCK].[MARKET]'形式,如'000300.SH'
    :param realtime: (int)时间戳
    :return: list
    '''
    return getSector(sector_code, realtime)

@try_except
def getSector(sector_code, realtime=0):
    resp = request('getSector', {'sectorCode': sector_code, 'realtime': realtime})
    return resp.get('result', [])


def get_industry(industry_name):
    '''
    获取行业成份股，支持申万行业和证监会行业
    :param industry_name: (str)行业名称
    :return: list
    '''
    return getIndustry(industry_name)

@try_except
def getIndustry(industry_name):
    resp = request('getIndustry', {'industryName': industry_name})
    return resp.get('result', [])


def get_stock_list_in_sector(sector_name, realtime=0):
    '''
    获取板块成份股，支持客户端左侧板块列表中任意的板块，包括自定义板块
    :param sector_name: (str)板块名称
    :param realtime: (int)时间戳
    :return: list
    '''
    return getStockListInSector(sector_name, realtime)

@try_except
def getStockListInSector(sector_name, realtime=0):
    resp = request('getStockListInSector', {'sectorName': sector_name, 'realtime': realtime})
    return resp.get('result', [])


def get_weight_in_index(index_code, stock_code):
    '''
    获取某只股票在某指数中的绝对权重
    :param index_code: (str)指数名称
    :param stock_code: (str)股票代码
    :return: float
    '''
    return getWeightInIndex(index_code, stock_code)

@try_except
def getWeightInIndex(index_code, stock_code):
    resp = request('getWeightInIndex', {'indexCode': index_code, 'stockCode': stock_code})
    return resp.get('result', 0)


def get_contract_multiplier(contract_code):
    '''
    获取合约乘数
    :param contract_code: (str)合约代码
    :return: int
    '''
    return getContractMultiplier(contract_code)

@try_except
def getContractMultiplier(contract_code):
    resp = request('getContractMultiplier', {'contractCode': contract_code})
    return resp.get('result', 0)


def get_risk_free_rate(timetag):
    '''
    取无风险利率，用十年期国债收益率CGB10Y作无风险利率
    :param timetag: (int)时间戳
    :return: float
    '''
    return getRiskFreeRate(timetag)

@try_except
def getRiskFreeRate(timetag):
    resp = request('getRiskFreeRate', {'timetag': timetag})
    return resp.get('result', 0.0)


""""
@try_except
def get_history_data(stock_code, len, period, field, dividtype=0, skip_paused=True):
    '''
    @Deprecated
    获取历史行情数据
    :param stock_code: (str)股票代码
    :param len: (int)数据长度
    :param period: (int)
    :param field: (str)
    :param dividtype: (int)
    :param skip_paused: (bool)
    :return: dict
    '''
    pass
"""


def get_financial_data(field_list, stock_list, start_date, end_date, report_type='announce_time'):
    '''
    获取财务数据
    :param field_list: (list)
    :param stock_list: (list)
    :param start_date: (str)
    :param end_date: (str)
    :param report_type: (str) announce_time / report_time
    :return:
        field: list[str]
        date: list[int]
        stock: list[str]
        value: list[list[float]]
    '''
    return getFinancialData(field_list, stock_list, start_date, end_date, report_type)

@try_except
def getFinancialData(field_list, stock_list, start_date, end_date, report_type='announce_time'):
    import pandas as pd
    from collections import OrderedDict

    pandasData = request('getFinancialData', {'fieldList': field_list, 'stockList': stock_list, 'startDate': start_date,
                                            'endDate': end_date, 'reportType': report_type})
    if not pandasData:
        return
    fields = pandasData['field']
    stocks = pandasData['stock']
    dates = pandasData['date']
    values = pandasData['value']

    if len(stocks) == 1 and len(dates) == 1:  # series
        series_list = []
        for value in values:
            if not value:
                return
            for subValue in value:
                series_list.append(subValue)
        return pd.Series(series_list, index=fields)
    elif len(stocks) == 1 and len(dates) > 1:  # index = dates, col = fields
        dataDict = OrderedDict()
        for n in range(len(values)):
            dataList = []
            if not values[n]:
                return
            for subValue in values[n]:
                dataList.append(subValue)
            dataDict[fields[n]] = pd.Series(dataList, index=dates)
        return pd.DataFrame(dataDict)
    elif len(stocks) > 1 and len(dates) == 1:  # index = stocks col = fields
        dataDict = OrderedDict()
        for n in range(len(values)):
            dataList = []
            if not values[n]:
                return
            for subValue in values[n]:
                dataList.append(subValue)
            dataDict[fields[n]] = pd.Series(dataList, index=stocks)
        return pd.DataFrame(dataDict)
    else:  # item = stocks major = dates minor = fields
        panels = OrderedDict()
        for i in range(len(stocks)):
            dataDict = OrderedDict()
            for j in range(len(values)):
                dataList = []
                value = values[j]
                if not value:
                    return
                for k in range(i * len(dates), (i + 1) * len(dates)):
                    dataList.append(value[k])
                dataDict[fields[j]] = pd.Series(dataList, index=dates)
            panels[stocks[i]] = pd.DataFrame(dataDict)
        return pd.Panel(panels)


def get_market_data(fields, stock_code=[], start_time='', end_time='', period='1d', dividend_type='none', count=-1):
    '''
    获取历史行情数据
    :param fields: ['open', 'high', 'low', 'close', 'volume', 'amount', 'settle']  ['quoter']
    :param stock_code:
    :param start_time:
    :param end_time:
    :param period:
    :param dividend_type:
    :param count:
    :return: dict
        lastPrice, amount, volume, pvolume, openInt, stockStatus, lastSettlementPrice, open, high, low, settlementPrice, lastClose
        askPrice(list), bidPrice(list), askVol(list), bidVol(list)  #level1(五档)/level2(十档)
    '''
    return getMarketData(fields, stock_code, start_time, end_time, period, dividend_type, count)

@try_except
def getMarketData(fields, stock_code=[], start_time='', end_time='', period='1d', dividend_type='none', count=-1):
    if len(fields) < 1 or len(stock_code) < 1:
        return None
    res = request('getMarketData', {'fields': fields, 'stockCodes': stock_code, 'startTime': start_time, 'endTime': end_time,
                                        'period': period, 'dividendType': dividend_type, 'count': count})
    # 返回结构[ 股票代码 , [ 时间戳 , [ 字段名 , 数据]]
    resData = res['result']
    oriData = {resData[i]: {str(resData[i + 1][m]): {resData[i + 1][m + 1][n]: resData[i + 1][m + 1][n + 1] for n in
                                                range(0, len(resData[i + 1][m + 1]), 2)} for m in
                            range(0, len(resData[i + 1]), 2)} for i in range(0, len(resData), 2)}
    if len(fields) == 1 and fields[0] == 'quoter':
        for stk, stkinfo in oriData.items():
            for timenode, quoter in stkinfo.items():
                delete_keys = []
                for level_key in ['askPrice', 'askVol', 'bidPrice', 'bidVol']:
                    quoter_values = []
                    for i in range(1, 11, 1):
                        key = '{}{}'.format(level_key, i)
                        if key in quoter:
                            quoter_values.append(quoter[key])
                            delete_keys.append(key)
                    quoter[level_key] = quoter_values
                for key in delete_keys:
                    quoter.pop(key)
                stkinfo[timenode] = {'quoter': quoter}
    resultDict = {}
    # resultDict = {'股票时间戳': [字段值list]}
    for code in oriData:
        for timenode in oriData[code]:
            values = []
            for field in fields:
                values.append(oriData[code][timenode][field])
            key = code + timenode
            resultDict[key] = values
    if len(fields) == 1 and len(stock_code) == 1 and (
            (start_time == '' and end_time == '') or start_time == end_time) and count == -1:
        for key in resultDict:
            return resultDict[key][0]
        return -1

    import pandas as pd
    if len(stock_code) <= 1 and start_time == '' and end_time == '' and count == -1:
        for key in resultDict:
            result = pd.Series(resultDict[key], index=fields)
            return result.sort_index()
    if len(stock_code) > 1 and start_time == '' and end_time == '' and count == -1:
        values = []
        for code in stock_code:
            if code in oriData:
                for timenode in oriData[code]:
                    key = code + timenode
                    values.append(resultDict[key])
        result = pd.DataFrame(values, index=stock_code, columns=fields)
        return result.sort_index()
    if len(stock_code) <= 1 and ((start_time != '' or end_time != '') or count >= 0):
        values = []
        times = []
        for code in oriData:
            for timenode in oriData[code]:
                key = code + timenode
                times.append(timenode)
                values.append(resultDict[key])
        result = pd.DataFrame(values, index=times, columns=fields)
        return result.sort_index()
    if len(stock_code) > 1 and ((start_time != '' or end_time != '') or count >= 0):
        values = {}
        for code in stock_code:
            times = []
            value = []
            if code in oriData:
                for timenode in oriData[code]:
                    key = code + timenode
                    times.append(timenode)
                    value.append(resultDict[key])
            values[code] = pd.DataFrame(value, index=times, columns=fields).sort_index()
        result = pd.Panel(values)
        return result
    return


def get_divid_factors(stock_code, date):
    '''
    获取除权除息日及对应的权息
    :param stock_code: (str)股票代码
    :param date: (str)日期
    :return: dict {(int)时间戳 : (list)数据}
    '''
    return getDividFactors(stock_code, date)

@try_except
def getDividFactors(stock_code, date):
    resp = request('getDividFactors', {'stockCode': stock_code, 'date': date})
    resData = resp['result']
    res = {resData[i]: [resData[i + 1][j] for j in
                            range(0, len(resData[i + 1]), 1)] for i in range(0, len(resData), 2)}
    if isinstance(res, dict):
        for k, v in res.items():
            if isinstance(v, list) and len(v) > 5:
                v[5] = int(v[5])
    return res


def get_main_contract(code_market):
    '''
    获取当前期货主力合约
    :param code_market: （str)股票代码
    :return: str
    '''
    return getMainContract(code_market)

@try_except
def getMainContract(code_market):
    resp = request('getMainContract', {'codeMarket': code_market})
    return resp.get('result', '')


def timetag_to_date_time(timetag, format):
    '''
    将毫秒时间转换成日期时间
    :param timetag: (int)时间戳毫秒数
    :param format: (str)时间格式
    :return: str
    '''
    return timetagToDateTime(timetag, format)

@try_except
def timetagToDateTime(timetag, format):
    import time
    timetag = timetag / 1000
    time_local = time.localtime(timetag)
    return time.strftime(format, time_local)


def get_total_share(stock_code):
    '''
    获取总股数
    :param stock_code: (str)股票代码
    :return: (int) 总股数
    '''
    return getTotalShare(stock_code)

@try_except
def getTotalShare(stock_code):
    resp = request('getTotalShare', {'stockCode': stock_code})
    return resp.get('result', 0)


def get_trading_dates(stock_code, start_date, end_date, count, period):
    '''
    取指定个股/合约/指数的 K 线(交易日)列表
    :param stock_code: (str)股票代码
    :param start_date: (str)开始日期
    :param end_date: (str)结束日期
    :param count: (int)倒数K线数量
    :param period: (str)K线类型
    :return: list
    '''
    return getTradingDates(stock_code, start_date, end_date, count, period)

@try_except
def getTradingDates(stock_code, start_date, end_date, count, period):
    resp = request('getTradingDates', {'stockCode': stock_code, 'startDate': start_date, 'endDate': end_date,
                                           'period': period, 'count': count})
    return resp.get('result', [])

@try_except
def get_factor_data(field_list, stock_list, start_date, end_date):
    import pandas as pd
    from collections import OrderedDict
    stocks = []
    if type(stock_list) == str:
        stocks.append(stock_list)
    else:
        stocks = stock_list
    pandasData = request('getFactorData', {'fieldList': field_list, 'stockList': stocks, 'startDate': start_date, 'endDate': end_date})
    if not pandasData:
        return
    fields = pandasData['field']
    dates = pandasData['date']
    values = pandasData['value']
    
    if len(stocks) == 1 and len(dates) == 1:    #series
        series_list = []
        for value in values:
            if not value:
                return
            for subValue in value:
                series_list.append(subValue)
        return pd.Series(series_list, index = fields)
    elif len(stocks) == 1 and len(dates) > 1:   #index = dates, col = fields
        dataDict = OrderedDict()
        for n in range(len(values)):
            dataList = []
            if not values[n]:
                return
            for subValue in values[n]:
                dataList.append(subValue)
            dataDict[fields[n]] = pd.Series(dataList, index = dates)
        return pd.DataFrame(dataDict)
    elif len(stocks) > 1 and len(dates) == 1:   #index = stocks col = fields
        dataDict = OrderedDict()
        for n in range(len(values)):
            dataList = []
            if not values[n]:
                return
            for subValue in values[n]:
                dataList.append(subValue)
            dataDict[fields[n]] = pd.Series(dataList, index = stocks)
        return pd.DataFrame(dataDict)
    else:                                       #Key = stocks value = df(index = dates, col = fields)
        panels = OrderedDict()
        for i in range(len(stocks)):
            dataDict = OrderedDict()
            for j in range(len(values)):
                dataList = []
                value = values[j]
                if not value:
                    return
                for k in range(i * len(dates), (i + 1) * len(dates)):
                    dataList.append(value[k])
                dataDict[fields[j]] = pd.Series(dataList, index = dates)
            panels[stocks[i]] = pd.DataFrame(dataDict)
        return panels


@try_except
def get_option_list(object, dedate, opttype = "", isavailavle = False):
    result = []
    undlMarket = ""
    undlCode = ""
    marketcodeList = object.split('.')
    if(len(marketcodeList) == 2):
        undlCode = marketcodeList[0]
        undlMarket = marketcodeList[1];
    undlCode = marketcodeList[0]
    undlMarket = marketcodeList[1];
    market = ""
    optList = []
    if(undlMarket == "SH"):
        optList = get_his_contract_list('SHO')
        optList = optList + get_stock_list_in_sector('上证期权')
    elif(undlMarket == "SZ"):
        optList = get_his_contract_list('SZO')
        optList = optList + get_stock_list_in_sector('深证期权')
    else:
        optList = get_his_contract_list('SHO')
        optList = optList + get_stock_list_in_sector('上证期权')
        optList = optList + get_his_contract_list('SZO')
        optList = optList + get_stock_list_in_sector('深证期权')
    if(opttype.upper() == "C"):
        opttype = "CALL"
    elif(opttype.upper() == "P"):
        opttype = "PUT"
    for opt in optList:
        inst = get_instrumentdetail(opt)
        if('ExtendInfo' not in inst):
            continue;
        if(opttype.upper() != "" and  opttype.upper() != inst['ExtendInfo']["optType"]):
            continue;
        if( (len(dedate) == 6 and str(inst['ExpireDate']).find(dedate) < 0)  ):
            continue;
        if( len(dedate) == 8): #option is trade,guosen demand
            createDate = inst['CreateDate']
            openDate = inst['OpenDate']
            if(openDate is None or createDate is None or openDate <= 19901219):
                openDate = createDate;
            else:
                openDate = min(openDate, createDate);
            if(str(openDate) > dedate):
                continue
            if(isavailavle):
                endDate = inst['ExpireDate']
                if(str(endDate) < dedate):
                    continue
        if(len(marketcodeList) == 2):
            if(inst['ProductID'].find(undlCode) > 0 or inst['ExtendInfo']['OptUndlCode'] == undlCode):
                result.append(opt)
        else:
            result.append(opt)
    return result;


def get_his_contract_list(market):
    return getHisContractList(market)
 
@try_except
def getHisContractList(market):
    resp = request('getHisContractList',{'strCodeMarket': market})
    return resp.get('vResult', [])


def get_instrumentdetail(opt):
    return getInstrumentDetail(opt)

@try_except
def getInstrumentDetail(opt):
    resp = request('getInstrumentDetail',{'strOptionCode': opt})
    return resp.get('result', [])


def get_option_detail_data(stock_code):
    return getOptionDetailData(stock_code)

@try_except
def getOptionDetailData(stock_code):
    resp = request('getOptionDetailData',{'strStockCode': stock_code})
    return resp.get('result', [])


def get_option_iv(opt_code):
    return getImpliedVolatility(opt_code)

@try_except
def getImpliedVolatility(opt_code):
    resp = request('getImpliedVolatility',{'strOptionCode': opt_code}) 
    return resp.get('dResult', 0.0)


def bsm_price(optType, targetPrice, strikePrice, riskFree, sigma, days, dividend = 0):
    return calcBSMPrice(optType, targetPrice, strikePrice, riskFree, sigma, days, dividend)

@try_except
def calcBSMPrice(optType, targetPrice, strikePrice, riskFree, sigma, days, dividend):
    optionType = "";
    if(optType.upper() == "C"):
        optionType = "CALL"
    if(optType.upper() == "P"):
        optionType = "PUT"
    if(type(targetPrice) == list):
        for price in targetPrice:
            resp= request('calcBSMPrice', {'strOptionType': optionType, 'dTargetPrice': float(price), 'dStrikePrice': strikePrice,
                                            'dRiskFree': riskFree, 'dSigma': sigma, 'dDays': days, 'dividend': dividend})
            bsmPrice = resp.get('dResult', 0.0)
            bsmPrice = round(bsmPrice,4)
            return bsmPrice
    else:
        resp = request('calcBSMPrice', {'strOptionType': optionType, 'dTargetPrice': targetPrice, 'dStrikePrice': strikePrice,
                                         'dRiskFree': riskFree, 'dSigma': sigma, 'dDays': days, 'dDividend': dividend})
        bsmPrice = resp.get('dResult', 0.0)
        bsmPrice = round(bsmPrice, 4)
        return bsmPrice
    

def bsm_iv(optType, targetPrice, strikePrice, optionPrice, riskFree, days, dividend = 0):
    return calcBSMIv(optType, targetPrice, strikePrice, optionPrice, riskFree, days, dividend)
    
@try_except   
def calcBSMIv(optType, targetPrice, strikePrice, optionPrice, riskFree, days, dividend):
    if(optType.upper() == "C"):
        optionType = "CALL"
    if(optType.upper() == "P"):
        optionType = "PUT"
    resp = request('calcBSMIv', {'strOptionType': optionType, 'dTargetPrice': targetPrice, 'dStrikePrice': strikePrice,
                                           'dOptionPrice': optionPrice, 'dRiskFree': riskFree,'dDays': days,'dDividend': dividend})
                                           
    bsmPrice = resp.get('dResult', 0.0)
    bsmPrice = round(bsmPrice, 4)
    return bsmPrice