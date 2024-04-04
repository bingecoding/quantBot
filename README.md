# quantBot

<br>
Fully automated trading bot for binance.

## Insights 
* Classification outperforms Regression
* Simple models such as KNN, Random Forest, Ridge Classifier, etc. outperform deep neural networks
* Feature engineering is the key ingredient to generating alpha

## Tools  
Machine learning models [scikit-learn](https://scikit-learn.org/stable/index.html) from used to make predictions.
<br>
Feature engineering with [pandas](https://pandas.pydata.org/docs/index.html).
Pandas MultiIndex feature is indespensible for data analysis. 
<br>
OHLCV data stored in SQLite.
<br>
Data retrieved from exchange with [python-binance](https://github.com/sammchardy/python-binance).
<br>
Note: the binance folder in this repo contains custom bugfixes that may not be in the offical python-binance repo.