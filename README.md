# quantBot

Fully automated trading bot for binance.

## Insights 
* Classification outperforms Regression
* Simple models such as KNN, Random Forest, Ridge Classifier, etc. outperform deep neural networks
* Feature engineering is the key ingredient to generating alpha

## Tools  
* Machine learning models from [scikit-learn](https://scikit-learn.org/stable/index.html) used to make predictions.
* Feature engineering with [pandas](https://pandas.pydata.org/docs/index.html).
    <br>
  Pandas MultiIndex feature is indespensible for data analysis.
* OHLCV data stored in SQLite.
* Data retrieved from exchange with [python-binance](https://github.com/sammchardy/python-binance).
  <br>
  Note: the binance folder in this repo contains custom bugfixes that may not be in the offical python-binance repo.