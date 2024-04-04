# quantBot

Fully automated trading bot for binance.

## Insights 
* Classification outperforms Regression
* Simple models such as KNN, Random Forest, Ridge Classifier, etc. outperform deep neural networks
* Feature engineering is the key ingredient to generating alpha

## Tools  
* Machine learning models from [scikit-learn](https://scikit-learn.org/stable/index.html) used for predictions
* Feature engineering with [pandas](https://pandas.pydata.org/docs/index.html) (MultiIndex feature is indispensable for data analysis)
* OHLCV data stored with SQLite
* Data retrieved from exchange with [python-binance](https://github.com/sammchardy/python-binance)<br>
  Note: the binance folder in this repo contains custom bugfixes

## Debugging
Should not be debugged while running the GUI. <br>
QT launches in another thread, so no breakpoint set will be hit in the core logic. 