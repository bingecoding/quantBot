import concurrent.futures

from cryptoTrader import *
from cryptoSignalMl import *

async def cryptoWatcher(logger):

    #for s in signals:
    background_tasks = {}
    
    while True:
        try:
            # TODO check if data has been retrieved for current day, i.e. we are waking up too early
            # Check if data for previous day is available for all cryptos
            await cryptoUtilities.sleep_until_next_trade('1d', 15)

            playSound()

            for i in range(1,4):
                try:
                    await cryptoUtilities.fetch_assets_tg('15m', tasks=4 if i==1 else 3 if i==2 else 2)
                    break    
                except Exception as e:
                    if i == 3:
                        e.add_note('failed 3x to get assets')
                        raise e
                    print(f'Retrying to fetch assets: {i} "{e}" {getCurrentTime()}') 
                    await asyncio.sleep(5)
            
            cryptoData = cryptoUtilities.getCryptoData()
            #await asyncio.sleep(100)
            rsadf = getResampledAssets(cryptoData, '1d')
            #could use rsadf.index.get_level_values(0) to not have to unstack
            rsadfu = rsadf.unstack()

            tpl = rsadfu.iloc[-1].return_p.nlargest(1).index.tolist()
            symbol = tpl[-1]
            regime = cryptoSignalMl(rsadf, rsadfu)

            # set leverage and margin type to isolated
            for i in range(1,4):
                client = None
                try:
                    client = await getWriteClient()
                    infoLs = await client.futures_position_information(symbol=symbol)
                    info = infoLs[0]
                    leverage = int(info['leverage'])
                    if leverage != LEVERAGE:
                        await client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)

                    if info['marginType'] == 'cross':
                        await client.futures_change_margin_type(symbol=symbol, marginType='ISOLATED')

                    exchange_info = await client.futures_exchange_info()
                    symbolInfo = [sym for sym in exchange_info['symbols'] if sym['symbol'] == symbol][0]
                    #ticker = await client.futures_ticker() #24h rolling prices
                    await client.close_connection()
                    break
                except Exception as e:
                    if client is not None:
                        await client.close_connection()
                    if i == 3:
                        e.add_note('failed 3x to set leverage, margin type and get symbol info')
                        raise e
                    print(f'Retrying to set and get preliminary info: {i} "{e}" {getCurrentTime()}')
                    await asyncio.sleep(10)

            if symbolInfo['status'] != 'TRADING':
                print(f'{symbol} cannot be traded: {symbolInfo["status"]}')
                continue

            #cancel threads waiting for an entry condition on the same asset
            #for _ in background_tasks.values():
            #    queue.put_nowait({'symbol': symbol})

            #playSound()
            #logger.emit(f'{symbol} cannot be traded: {symbolInfo["status"]}')
            if len(background_tasks) < 2: #this should be at most 3 when hold period is 2 days
                queue = asyncio.LifoQueue()
                task = asyncio.create_task(cryptoTrader(symbolInfo, Regime(regime)))

                background_tasks.update({task : queue})
                # Add task to the set. This creates a strong reference.
                #background_tasks.add((task,queue))
                task.add_done_callback(background_tasks.pop)
            #else:
            #    print("max 1 concurrent trades")

        except Exception as e:
            print(f'Caught exception in main: "{e}" {getCurrentTime()}')

def cryptoInit(logger):

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_default_executor(concurrent.futures.ThreadPoolExecutor(max_workers=12))
    loop.run_until_complete(cryptoWatcher(logger))