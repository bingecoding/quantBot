
import asyncio
import time
from datetime import datetime, timezone, timedelta
import math

from sqlalchemy import text, inspect
import pandas as pd
from pandas.tseries.offsets import MonthEnd

from binance import Client
from binance.enums import HistoricalKlinesType
from tradingUtilities import *

time_interval_options = {
            '1m'  : 60*1, 
            '3m'  : 60*3, 
            '5m'  : 60*5, 
            '15m' : 60*15,
            '30m' : 60*30, 
            '1h'  : 60*60, 
            '2h'  : 60*60*2,
            '4h'  : 60*60*4, 
            '6h'  : 60*60*6, 
            '8h'  : 60*60*8, 
            '12h' : 60*60*12, 
            '1d'  : 60*60*24, 
            '1week' : 60*60*24*7 }

#keep as many assets as possible, improves accuracy
cryptos = ['1000SHIBUSDT', 'BTCUSDT', 'ETHUSDT', 'ADAUSDT','MATICUSDT', 'ETCUSDT', 'LINKUSDT', 'SFPUSDT',
 'ZILUSDT','ALPHAUSDT','MTLUSDT','BATUSDT','IOTAUSDT','KSMUSDT','SKLUSDT','RENUSDT','AUDIOUSDT',
 'ANKRUSDT','COTIUSDT','IOTXUSDT','WAVESUSDT','BAKEUSDT','ALGOUSDT','SUSHIUSDT','RLCUSDT','ZECUSDT','HOTUSDT',
 'ICXUSDT','VETUSDT','CELRUSDT','SXPUSDT','LINAUSDT','NKNUSDT','UNIUSDT','DASHUSDT','COMPUSDT','IOSTUSDT',
 'EGLDUSDT','GTCUSDT','EOSUSDT','HBARUSDT','STORJUSDT','ZENUSDT','AAVEUSDT','DOTUSDT','ZRXUSDT','DGBUSDT','STMXUSDT',
 'FILUSDT','FLMUSDT','YFIUSDT','UNFIUSDT','CTKUSDT','RSRUSDT','RVNUSDT','QTUMUSDT','GRTUSDT','ONEUSDT','ENJUSDT',
 'BELUSDT','MANAUSDT','SOLUSDT','BALUSDT','C98USDT','TRBUSDT','KNCUSDT','SANDUSDT','CRVUSDT','MKRUSDT','BANDUSDT',
 'AXSUSDT','THETAUSDT','ALICEUSDT','BTCDOMUSDT','NEOUSDT','OCEANUSDT','SNXUSDT','OMGUSDT','NEARUSDT','DEFIUSDT',
 'XMRUSDT','LRCUSDT','ATOMUSDT','BNBUSDT','RUNEUSDT','OGNUSDT','BCHUSDT','AVAXUSDT','REEFUSDT','XLMUSDT','XRPUSDT',
 'FTMUSDT','XTZUSDT','ONTUSDT','LTCUSDT','CHRUSDT','TRXUSDT','DENTUSDT','1INCHUSDT','DOGEUSDT','KAVAUSDT',
 '1000LUNCUSDT', 'LQTYUSDT', 'GMTUSDT', 'CFXUSDT', 'XEMUSDT', 'AGIXUSDT', 'ENSUSDT', 'TUSDT', 'INJUSDT','OPUSDT',
 'DYDXUSDT', 'CELOUSDT', 'GALAUSDT']

class CryptoUtilities():
    
    def __init__(self, engine, cryptos=cryptos, offline=False) -> None:
        self.offline = offline
        self.engine = engine
        self.cryptos = cryptos

    def setCryptos(self, cryptos) -> None:
        self.cryptos = cryptos

    def getCryptos(self):
        return self.cryptos

    def __get_time_for_next_trade(self, time_interval):
        ct = int(datetime.now(timezone.utc).timestamp())
        ttws = time_interval_options[time_interval]#5*60 # 5 minutes
        time_int = time_interval_options[time_interval]
        current_time = (math.floor(ct / (time_int)) * (time_int)) + ttws
        dt = current_time - ct
        if dt < 0:
            current_time = (math.ceil(ct / (time_int)) * (time_int)) + ttws
        lt = datetime.strptime(self.utc_time(current_time), "%Y-%m-%d %H:%M:%S")
        return lt
    
    def __get_time_for_next_candle(self, time_interval):
        time_int = time_interval_options[time_interval]
        current_time = (math.floor(int(time.time()) / time_int) * (time_int)) + time_int
        lt = datetime.strptime(self.utc_time(current_time), "%Y-%m-%d %H:%M:%S")
        return lt

    def __getLfc(self, time_interval):
        current_time = int(datetime.now(timezone.utc).timestamp())
        lfc_close = math.floor(current_time / time_interval_options[time_interval]) * time_interval_options[time_interval] - time_interval_options[time_interval]

        return lfc_close
    
    async def __getdata(self, symbol, start, end, interval='1m'):
        
        if self.offline:
            print("offline")
            return
        
        try:
            #client = await getWriteClient()
            #data = await client.get_historical_klines(symbol, interval, start, end, klines_type=HistoricalKlinesType.FUTURES)
            data = await readRequestTimeout(lambda client: client.get_historical_klines(symbol, interval, start, end, klines_type=HistoricalKlinesType.FUTURES), timeout=60)
        except Exception as e:
            raise Exception(f"Cannot get data from Binance {e}")
        #finally:
        #    await client.close_connection()
  
        if len(data) == 0:
            return []

        frame = pd.DataFrame(data)

        frame = frame.iloc[:,:6]
        frame.columns= ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        frame.Date = pd.to_datetime(frame.Date, unit='ms')
        frame.set_index('Date', inplace=True)

        frame = frame.astype(float)
        return frame
    
    async def __sql_import(self, symbol, start, end, interval):
        try:
            if not inspect(self.engine).has_table(symbol):
                print(f'Table probably does not exist for {symbol}')
                print(f'processing {start} {end} for {symbol}...') 
                new_data = await self.__getdata(symbol, start, end, interval)
                if len(new_data) == 0:
                    return
                new_data.to_sql(symbol, self.engine, if_exists='append', index=True)
                print(str(len(new_data[:-1])) + ' new rows imported to DB.')
                return
        except Exception as e:
            raise e

        try:
            with self.engine.begin() as conn:
                query = text(f'SELECT MAX(Date) FROM "{symbol}"')
                maxdate = pd.read_sql_query(query, conn).values[0][0]
                query = text(f'SELECT MIN(Date) FROM "{symbol}"')
                mindate = pd.read_sql_query(query, conn).values[0][0]

                #print(f'{mindate} {maxdate}')
            if pd.to_datetime(maxdate) >= pd.to_datetime(end):
                #print(f'no further processing {maxdate} {end} for {symbol}...')
                return

            #print(f'processing {maxdate} {end} for {symbol}...')    
            new_data = await self.__getdata(symbol, maxdate, end, interval)
            if len(new_data) == 0:
                #print(f'no data for {maxdate} {end}')
                return
            new_rows = new_data[new_data.index > maxdate]
            new_rows.to_sql(symbol, self.engine, if_exists='append')
            #new_rows = data[data.index > max_date and data.index < min_date]
            #print(str(len(new_rows[:-1])) + ' new rows imported to DB.')
        except Exception as e:
            raise e
            
        return
    
    def utc_time(self, unixTimestamp):
    
        unix_timestamp  = int(unixTimestamp)
        utc_time = time.gmtime(unix_timestamp)
        local_time = time.localtime(unix_timestamp)

        #time.strftime("%Y-%m-%d %H:%M:%S+00:00 (UTC)", utc_time)

        return time.strftime("%Y-%m-%d %H:%M:%S", utc_time)
    
    async def sleep_until_next_trade(self, time_interval, toff=0):
        nt = datetime.strptime(self.utc_time(int(datetime.now(timezone.utc).timestamp())), "%Y-%m-%d %H:%M:%S")
        lt = self.__get_time_for_next_trade(time_interval)
        time_to_wait = lt - nt
        #print("sleep for: ", time_to_wait.total_seconds()+2+toff)
        await asyncio.sleep(int(time_to_wait.total_seconds()+2+toff)) # add 2 seconds lag, so that the last full candle is available
        #print("awake from sleep: ", datetime.now().strftime("%B %d, %Y %H:%M:%S"))
        return
    
    async def sleep_until_candle_complete(self, time_interval, toff=0):
        nt = datetime.strptime(self.utc_time(int(datetime.now(timezone.utc).timestamp())), "%Y-%m-%d %H:%M:%S")    
        lt = self.__get_time_for_next_candle(time_interval)
        time_to_wait = lt - nt    
        #print("sleep for: ", time_to_wait.total_seconds()+2+toff)
        await asyncio.sleep(int(time_to_wait.total_seconds()+2+toff)) # add 2 seconds lag, so that the last full candle is available
        #print("awake from sleep: ", datetime.now().strftime("%B %d, %Y %H:%M:%S"))   
    
    async def __fetch_assets_func(self, daterange, lfc_close, time_interval, cryptos):

        for crypto in cryptos:
            for i in range(0, len(daterange)):
                try:
                    start = str(daterange[i]) 
                    if(i == len(daterange)-1):
                        end = self.utc_time(lfc_close)
                    else:
                        end = str(daterange[i] + MonthEnd(0))                                                  
                    await self.__sql_import(crypto, start, end, time_interval)
                    #sleep(5)
                except Exception as e:
                    raise e
        
        return

    async def fetch_assets_tg(self, time_interval, tasks=8, sd=''):
    
        dtny = datetime.now(timezone.utc) - timedelta(days=21)

        if sd == '':
            startdate = self.utc_time(int(dtny.timestamp()))
        else:
            startdate = sd

        lfc_close = self.__getLfc(time_interval)

        daterange = pd.date_range(startdate, self.utc_time(lfc_close), freq='MS')
        
        n_tasks = 8 if tasks > 8 else tasks
        n_cryptos = len(self.cryptos)
        n_split = int(n_cryptos / n_tasks)
        
        assert n_split > 0
        
        async with ForgivingTaskGroup() as tg:
            for i in range(0,n_tasks):
                partialCryptos = self.cryptos[i*n_split: n_cryptos if i == n_tasks-1 else (i+1)*n_split]
                tg.create_task(self.__fetch_assets_func(daterange, lfc_close, time_interval, partialCryptos))

        return
    
    async def fetchSingleAsset(self, time_interval, crypto, sd=''):
    
        dtny = datetime.now(timezone.utc) - timedelta(days=21)

        if sd == '':
            startdate = self.utc_time(int(dtny.timestamp()))
        else:
            startdate = sd

        lfc_close = self.__getLfc(time_interval)

        daterange = pd.date_range(startdate, self.utc_time(lfc_close), freq='MS')
        
        await self.__fetch_assets_func(daterange, lfc_close, time_interval, [crypto]) 

        return

    #startdate should be todays date less 1 day
    def getCryptoData(self, sd=''):
        
        # we need more than 1 day of data for Return_1d because resampling, i.e. dropping rows wipes cryptoData clean
        dtny = datetime.now(timezone.utc) - timedelta(days=180)

        if sd == '':
            startdate = self.utc_time(int(dtny.timestamp()))
        else:
            startdate = sd
        
        cryptoData = {}
        with self.engine.begin() as conn:
            for crypto in self.cryptos:
                query = text(f"SELECT * FROM '{crypto}' where Date >= '{startdate}'")
                data = pd.read_sql_query(query, conn)
                data.Date = pd.to_datetime(data.Date)
                data.set_index('Date', inplace=True)
                cryptoData[f"{crypto}"] = data

        return cryptoData

    def getSingleCryptoData(self, crypto, sd=''):
        
        # we need more than 1 day of data for Return_1d because resampling, i.e. dropping rows wipes cryptoData clean
        dtny = datetime.now(timezone.utc) - timedelta(days=14)

        if sd == '':
            startdate = self.utc_time(int(dtny.timestamp()))
        else:
            startdate = sd
        
        cryptoData = {}
        with self.engine.begin() as conn:
            query = text(f"SELECT * FROM '{crypto}' where Date >= '{startdate}'")
            data = pd.read_sql_query(query, conn)
            data.Date = pd.to_datetime(data.Date)
            data.set_index('Date', inplace=True)
            cryptoData[f"{crypto}"] = data

        return cryptoData

    def resampleOHLC_1mdb(self, df, interval):
    
        if interval == '1m':
            #we assume the data is in 1 minute intervals
            dfm = df.resample('1Min').agg({
                'Open':'first',
                'High':'max',
                'Low':'min',
                'Close':'last',
                'Volume': 'sum'
            })

            return dfm

        if interval == '5m':
            iv = '5Min'
        elif interval == '15m':
            iv = '15Min'
        elif interval == '30m':
            iv = '30Min'
        else:
            iv = interval

        dfre = df.resample(iv).agg({
            'Open':'first',
            'High':'max',
            'Low':'min',
            'Close':'last',
            'Volume': 'sum'
        })

        #just drop first row, may be incomplete
        dfre = dfre[1:]

        minutes = int(time_interval_options[interval] / 60) - 1

        checkdate = dfre.index[-1] + pd.Timedelta(minutes=minutes)
        #print(checkdate)
        if len(df[df.index == checkdate]) == 0:
            #drop last row
            dfre = dfre[:-1]

        return dfre

    def resampleOHLC_15mdb(self, df, interval):
    
        if interval == '15m':
            dfm = df.resample('15Min').agg({
                'Open':'first',
                'High':'max',
                'Low':'min',
                'Close':'last',
                'Volume': 'sum'
            })

            return dfm

        if interval == '30m':
            iv = '30Min'
        else:
            iv = interval

        dfre = df.resample(iv).agg({
            'Open':'first',
            'High':'max',
            'Low':'min',
            'Close':'last',
            'Volume': 'sum'
        })

        # we have to remove the first and last row, depending on whether all the data is there
        # have to offset minutes to not include unfinished bars
        minutes = int(time_interval_options[interval] / 60) - 15

        checkdate = dfre.index[0]
        if len(df[df.index == checkdate]) == 0:
            # drop first row
            dfre = dfre[1:]

        checkdate = dfre.index[-1] + pd.Timedelta(minutes=minutes)
        if len(df[df.index == checkdate]) == 0:
            #drop last row
            dfre = dfre[:-1]

        return dfre
    
    def getOffsetStrTime(self, dts, minutes):
        ot = pd.to_datetime(dts) - pd.Timedelta(minutes=minutes)
        return ot.strftime('%Y-%m-%d %X')
    
    def getMask(self, df, minutes, dts=''):
    
        #crypto_asset = df.index.get_level_values(1)[0]
        asset = df.xs(self.cryptos[0], level=1)

        if dts == '':
            ets = asset.iloc[-1].name
            sts = (ets - pd.Timedelta(minutes=minutes))
            mask = (asset.index >= sts.strftime('%Y-%m-%d %X')) & (asset.index <= ets.strftime('%Y-%m-%d %X'))
        else:
            st = self.getOffsetStrTime(dts, minutes)
            mask = (asset.index >= st) & (asset.index <= dts)

        return mask