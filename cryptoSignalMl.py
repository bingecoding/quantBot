import os
import pandas as pd
import numpy as np

from sklearn.linear_model import RidgeClassifier

from cryptoHelpers import *

def getTrainingData(symbol, df, dfu):

    n_cryptos = len(df.index.levels[1])

    df_train = pd.DataFrame()
    
    #features are the key ingredient to generating alpha, coupled with a simple model
    #just for reference
    df_train['mean'] = df['return_p'].groupby(level="Date").mean()
    df_train['std'] = df['return_p'].groupby(level="Date").std()
    df_train['sign'] = df.xs(symbol, level=1)['return_p'][:].apply(lambda rt: 1 if rt > 0 else (-1 if rt < 0 else 0))

    #target outcome
    df_train['targets'] = df.xs(symbol, level=1)['log_ret'][:].apply(lambda rt: 1 if rt > 0 else (-1 if rt < 0 else 0)).shift(-1)
    df_train.loc[df_train.index[-1], 'targets'] = -1

    return df_train

def cryptoSignalMl(rsadf, rsadfu):

    tpl = rsadfu.iloc[-1].return_p.nlargest(1).index.tolist()
    sym = tpl[0]
    dft = getTrainingData(sym, rsadf, rsadfu)
    
    n_training = 100
    x_train, y_train = dft.iloc[-n_training-1:-1,:-1], dft.iloc[-n_training-1:-1,-1]
    x_predict = dft.iloc[-1:,:-1]

    # Classifiers beat regression
    # Neural networks for example, CNN, RNN, LSTM, etc. cannot match 
    # simple models such as KNN, Ridge Classifier, Random Forest etc.
    clf = RidgeClassifier()
    clf.fit(x_train, y_train)
    regime = clf.predict(x_predict)[0]
    
    return regime