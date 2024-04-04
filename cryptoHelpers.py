import ta
import numpy as np
import pandas as pd

import subprocess

from sqlalchemy import create_engine

from cryptoUtilities import *

engine = create_engine('sqlite:////Users/labrat/backup/jupyter/trading/env/db/CryptoData_15m.db')
cryptoUtilities = CryptoUtilities(engine, cryptos, offline=False)

def getResampledAssets(cryptoData, time_int):
    
    resampled_assets = pd.DataFrame()
    
    for key, value in cryptoData.items():
        dftmp = cryptoUtilities.resampleOHLC_15mdb(value, time_int)
        df = dftmp.copy()
        df['Symbol'] = key
        df.drop('Volume', axis=1, inplace=True)

        df['ema_9'] = ta.trend.ema_indicator(df.Close, window=9)
        df['ema_21'] = ta.trend.ema_indicator(df.Close, window=21)
        #df['ema_200'] = ta.trend.ema_indicator(df.Close, window=200)
        df['atr_14'] = ta.volatility.AverageTrueRange(df.High, df.Low, df.Close, window=14).average_true_range()
        
        periods = int(time_interval_options['1d'] / time_interval_options[time_int]) #1 days worth of data relative to time_int
        df['return_p'] = df.Close.pct_change(periods=periods) #Simple returns are asset-additive

        df['log_ret'] = np.log(df.Close) - np.log(df.Close.shift(1)) #Log returns are time-additive
        
        df = df.reset_index()
        df = df.set_index(['Date', 'Symbol'])

        resampled_assets = pd.concat([resampled_assets,df],axis=0)
    
    resampled_assets.dropna(inplace=True)
    
    return resampled_assets.sort_index()


def playSound():

    #playsound.playsound("/Users/labrat/backup/jupyter/trading/env/audio/Br2049rt.wav")
    
    cmd = """
        tell application "Music"
	        play track "Br2049rt"
        end tell
    """
    result = subprocess.run(['osascript', '-e', cmd], capture_output=True)
    return result.stdout

def stopSound():
    cmd = """
        tell application "Music"
	        stop track "Br2049rt"
        end tell
    """
    result = subprocess.run(['osascript', '-e', cmd], capture_output=True)
    return result.stdout

def getCurrentTime():
    utct =  datetime.now(timezone.utc)
    loct = datetime.now(datetime.now(timezone.utc).astimezone().tzinfo)
    
    return f"{utct.strftime('%Y-%m-%d %X')} {loct.strftime('%Y-%m-%d %X')}"