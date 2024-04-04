import asyncio
import json
import os
from binance import AsyncClient
from enum import Enum

def getConfig():

    bundle_dir = os.path.dirname(os.path.abspath(__file__))
    configFile = os.path.join(bundle_dir, 'config.json')
    with open(configFile, 'r') as file:
        config = json.load(file)
    
    return config

async def getReadOnlyClient():
    config = getConfig()
    client = await AsyncClient.create(api_key=config['api_key'], api_secret=config['api_secret'])
    return client

async def readRequest(callback):
    client = None
    try:
        client = await getReadOnlyClient()
        res = await callback(client)
    except Exception as e:
        e.add_note("readRequest failed, closing connection")
        raise e
    finally:
        if client is not None:
            await client.close_connection()
    
    return res

async def readRequestTimeout(callback, timeout=10):
    client = None
    try:
        client = await getReadOnlyClient()
        res = await asyncio.wait_for(callback(client), timeout=timeout)
    except Exception as e:
        e.add_note("readRequest failed, closing connection")
        raise e
    finally:
        if client is not None:
            await client.close_connection()
    
    return res

async def getWriteClient():
    client = None
    config = getConfig()
            
    while True:
        try:
            client = await AsyncClient.create(api_key=config['api_key'], api_secret=config['api_secret'])
            #await client.futures_account()
            break
        except Exception as e:
            if client is not None:
                await client.close_connection()
            raise

    return client

async def retryRequest(callback, retries=1):
    res = None
    while True:
        try:
            client = await getWriteClient()
            res = await callback(client)
        except TimeoutError as e:
            print(f'retrying... {e}')
            continue
        except Exception as e:
            if e.code != -2015:
                raise
            print(f'retrying... {e}')
            continue
        finally:
            if client is not None:
                await client.close_connection()
        break

    return res

class ForgivingTaskGroup(asyncio.TaskGroup):
     _abort = lambda self: None

class Regime(Enum):
    SHORT = -1
    LONG = 1

class Trend(Enum):
    START = 1
    WAIT = 2

#10 leverage @ 8.36% greater win but more losses than 7 leverage @ 12.6%
LEVERAGE = 7 # 100/8=12.5 leverage 8 should suffice but it doesn't, stop loss should be 12.5 but liquidates at ~11, i.e. leverage at 7 is 12.6%
SL_PCT = 12.5
