import asyncio

from tradingUtilities import *
from cryptoHelpers import *

def getStopLoss(regime, bar):
    
    if regime == Regime.LONG:
        sl = bar.Close * (100-SL_PCT)/100
    
    if regime == Regime.SHORT:
        sl = bar.Close * (100+SL_PCT)/100

    return sl

def getQuantity(entryPrice, minQty):

    riskAmountInEur = 100.0 #amount you're willing to lose
    quantity = riskAmountInEur / entryPrice * LEVERAGE #risking x euro for stop loss distance
    rnd = int(quantity / minQty)
    quantity = rnd * minQty
    quantity = float(f'{quantity:.3f}')
    if quantity < minQty:
        print(f'quantity too low: {quantity} min: {minQty}')
        return -1
    
    return quantity

async def setStopLoss(symbol, regime, entryPrice, sldis, pricePrecision, quantity):

    eslOdrId = -1
    while True:
        try:
            if regime == Regime.LONG:
                stopLossEmergency = entryPrice - 2*sldis
                stopLossEmergency = float(f'{stopLossEmergency:.{pricePrecision}f}')
                eslOdr = await retryRequest(lambda client: client.futures_create_order(symbol=symbol, side=Client.SIDE_SELL, type=Client.FUTURE_ORDER_TYPE_STOP_MARKET, quantity=quantity, stopPrice=stopLossEmergency, reduceOnly=True))  
                eslOdrId = eslOdr['orderId']
                stopLoss = entryPrice - sldis
            
            if regime == Regime.SHORT:
                stopLossEmergency = entryPrice + 2*sldis
                stopLossEmergency = float(f'{stopLossEmergency:.{pricePrecision}f}')
                eslOdr = await retryRequest(lambda client: client.futures_create_order(symbol=symbol, side=Client.SIDE_BUY, type=Client.FUTURE_ORDER_TYPE_STOP_MARKET, quantity=quantity, stopPrice=stopLossEmergency, reduceOnly=True))  
                eslOdrId = eslOdr['orderId']
                stopLoss = entryPrice + sldis
                
            break
        except Exception as e:
            print(f'Caught exception in cryptoTrader: "{e}"')

    print(f"{symbol} found entry and setting stop loss: {stopLoss} and emergency SL: {stopLossEmergency} {{getCurrentTime()}}")

    return eslOdrId, stopLoss

async def cancelEmergencyStopLoss(symbol, eslOdrId):

    print(f'Cancelling emergency stop loss order')
    while True:
        try:
            resOdr = await retryRequest(lambda client: client.futures_get_order(symbol=symbol, orderId=eslOdrId))
            if resOdr['status'] == 'CANCELED' or resOdr['status'] == 'FILLED':
                break
            await retryRequest(lambda client: client.futures_cancel_order(symbol=symbol, orderId=eslOdrId))
            print(f'Cancelling emergency stop loss order, succeeded {getCurrentTime()}')
            break
        except Exception as e:
            print(f'Caught exception in cryptoTrader: "{e}" {getCurrentTime()}')

async def enterTrade(symbol, regime, quantity):

    mrkIdOdr = -1
    entryPrice = float(0)
    while True:
        try:
            if regime == Regime.LONG:                
                if mrkIdOdr == -1:
                    resMrkOdr = await retryRequest(lambda client: client.futures_create_order(symbol=symbol, side=Client.SIDE_BUY, type=Client.FUTURE_ORDER_TYPE_MARKET, quantity=quantity))
                    mrkIdOdr = resMrkOdr['orderId']

                resOdr = await retryRequest(lambda client: client.futures_get_order(symbol=symbol, orderId=mrkIdOdr))
                entryPrice = float(resOdr['avgPrice'])

                return entryPrice
            
            if regime == Regime.SHORT:                        
                if mrkIdOdr == -1:
                    resMrkOdr = await retryRequest(lambda client: client.futures_create_order(symbol=symbol, side=Client.SIDE_SELL, type=Client.FUTURE_ORDER_TYPE_MARKET, quantity=quantity))
                    mrkIdOdr = resMrkOdr['orderId']

                resOdr = await retryRequest(lambda client: client.futures_get_order(symbol=symbol, orderId=mrkIdOdr))
                entryPrice = float(resOdr['avgPrice'])

                return entryPrice

        except Exception as e:
            print(f'Caught exception in cryptoTrader: "{e}" {getCurrentTime()}')

async def exitTrade(symbol, regime, quantity):

    riskPosition = await retryRequest(lambda client: client.futures_position_information(symbol=symbol))
    riskQuantity = abs(float(riskPosition[0]['positionAmt']))
    
    if riskQuantity <= 0:
        #manually closing trade will cause it to exit here and cancel emergency stop loss if still open
        return

    if regime == Regime.LONG:
        print(f'{symbol} exiting trade {getCurrentTime()}')
        if riskQuantity >= quantity:
            await retryRequest(lambda client: client.futures_create_order(symbol=symbol, side=Client.SIDE_SELL, type=Client.FUTURE_ORDER_TYPE_MARKET, quantity=quantity, reduceOnly=True))
     

    if regime == Regime.SHORT:   
        print(f'{symbol} exiting trade {getCurrentTime()}')
        if riskQuantity >= quantity:
            await retryRequest(lambda client: client.futures_create_order(symbol=symbol, side=Client.SIDE_BUY, type=Client.FUTURE_ORDER_TYPE_MARKET, quantity=quantity, reduceOnly=True))

async def manageTrade(symbol, regime, stopLoss, quantity, waitLimit):

    #1. monitor trade, if under Stop Loss for 30s consecutively exit trade    
    bsl = 0 #breaches stop loss
    while True:
        try:
            await asyncio.sleep(10)

            if pd.Timestamp.utcnow() >= waitLimit:
                print(f'{symbol} trade rolled over, exiting {getCurrentTime()}')
                return

            res = await readRequest(lambda client: client.futures_symbol_ticker(symbol=symbol))
            riskPosition = await retryRequest(lambda client: client.futures_position_information(symbol=symbol))
            riskQuantity = abs(float(riskPosition[0]['positionAmt']))
            
            if riskQuantity <= 0:
                #manually closing trade will cause it to exit here and cancel emergency stop loss if still open
                return

            currentPrice = round(float(res['price']), 8)
            if regime == Regime.LONG:
                if currentPrice <= stopLoss:
                    bsl+=1
                    if bsl == 3: #30s
                        #exit trade
                        print(f'{symbol} exiting trade price {currentPrice} fell below stop loss {stopLoss} {getCurrentTime()}')
                        if riskQuantity >= quantity:
                            await retryRequest(lambda client: client.futures_create_order(symbol=symbol, side=Client.SIDE_SELL, type=Client.FUTURE_ORDER_TYPE_MARKET, quantity=quantity, reduceOnly=True))
                        return
                else:
                    bsl = 0

            if regime == Regime.SHORT:
                if currentPrice >= stopLoss:
                    bsl+=1
                    if bsl == 3: #30s
                        #exit trade
                        print(f'{symbol} exiting trade price {currentPrice} fell below stop loss {stopLoss} {getCurrentTime()}')
                        if riskQuantity >= quantity:
                            await retryRequest(lambda client: client.futures_create_order(symbol=symbol, side=Client.SIDE_BUY, type=Client.FUTURE_ORDER_TYPE_MARKET, quantity=quantity, reduceOnly=True))
                        return
                else:
                    bsl = 0

        except Exception as e:
            print(f'Caught exception in cryptoTrader: "{e}" {getCurrentTime()}')

async def cryptoTrader(symbolInfo, regime, holdDays=1):

    symbol = symbolInfo['symbol']

    minQty = float(symbolInfo['filters'][1]['minQty'])
    tickSize = float(symbolInfo['filters'][0]['tickSize']) #tick_ size os to big, e.g. SRMUSDT
    pricePrecision = symbolInfo['pricePrecision']

    entryPrice = float(0)
    res = await readRequest(lambda client: client.futures_symbol_ticker(symbol=symbol))
    entryPrice = round(float(res['price']), 8)

    #stop loss
    #sldis, sl = getStopLoss(regime, csym15m)
    quantity =  getQuantity(entryPrice, minQty) #risking x euro for stop loss dis
    if quantity == -1:
        print(f'{symbol} {quantity} amount too small exiting: minimum amount {minQty}')
        return

    print(f"{symbol} entering {regime.name} trade {getCurrentTime()}")

    await enterTrade(symbol, regime, quantity)
    
    # hold for ~ 1 day, exit before rollover of account funding
    await cryptoUtilities.sleep_until_next_trade('1d', toff=-60)

    if holdDays == 2:
        while True:
            try:
                await cryptoUtilities.fetchSingleAsset('15m', symbol)
                break
            except Exception as e:
                pass

        sas = cryptoUtilities.getSingleCryptoData(symbol)
        df = getResampledAssets(sas, '1d') 
        lastBar = df.xs(symbol, level=1).iloc[-1]
        stopLoss = getStopLoss(regime, lastBar)
        waitLimit = lastBar.name + pd.Timedelta(hours=48) #number of bars in
        waitLimit = waitLimit.tz_localize('UTC')

        #avoid managing the trade by setting a hard stop loss, i.e. emergency stop loss
        await manageTrade(symbol, regime, stopLoss, quantity, waitLimit)

    await exitTrade(symbol, regime, quantity)

    # managing trade so no hard stop loss    
    #await cancelEmergencyStopLoss(symbol, eslOdrId)

    print(f"Task exiting: {symbol} {regime.name} {getCurrentTime()}")

    return