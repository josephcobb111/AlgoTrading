import json
import logging
import os
import pyotp
import requests

import numpy as np
import pandas as pd
import robin_stocks.robinhood as rs

from datetime import datetime, timezone, timedelta
from dateutil import parser
from time import sleep
from urllib.parse import unquote


def robinhood_login(
    robin_user=os.environ.get('robinhood_username'),
    robin_pass=os.environ.get('robinhood_password'),
    robin_mfa_auth=os.environ.get('robinhood_mfa_auth'),
    robin_mfa_code=None,
):
    """Login to Robinhood."""

    if robin_mfa_auth:
        robin_mfa_code = pyotp.TOTP(robin_mfa_auth).now()

    rs.login(
        username=robin_user,
        password=robin_pass,
        expiresIn=86400,
        mfa_code=robin_mfa_code,
        by_sms=True,
    )


def get_implied_volatility_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0"
    }

    url = ("https://www.barchart.com/proxies/core-api/v1/quotes/get")

    payload = {
        'fields': ("symbol,symbolName,"
                   "lastPrice,priceChange,percentChange,optionsTotalVolume,"
                   "optionsWeightedImpliedVolatility,optionsImpliedVolatilityRank1y,"
                   "optionsImpliedVolatilityPercentile1y,optionsWeightedImpliedVolatilityHigh1y,"
                   "tradeTime,symbolCode,symbolType,hasOptions"),
        'list': 'options.mostActive.us,options.mostActive.etf',
        'meta': 'field.shortName,field.type,field.description',
        'hasOptions': 'true',
        'raw': '1',
    }

    with requests.Session() as s:
        # get all cookies
        s.get(
            "https://www.barchart.com",
            headers=headers,
        )
        # use one cookie as HTTP header
        headers["X-XSRF-TOKEN"] = unquote(s.cookies["XSRF-TOKEN"])
        data = s.get(url, params=payload, headers=headers).json()

    output = pd.DataFrame(pd.DataFrame(data['data'])['raw'].tolist())
    output['tradeTime'] = pd.DataFrame(data['data'])['tradeTime']

    # data cleaning
    if output['optionsImpliedVolatilityRank1y'].max() > 1:
        output['optionsImpliedVolatilityRank1y'] = output['optionsImpliedVolatilityRank1y'] / 100

    # data quality check
    for _value in ['optionsImpliedVolatilityRank1y', 'optionsImpliedVolatilityPercentile1y']:
        _min = output[_value].min() >= 0
        _max = output[_value].max() <= 1
        assert _min == _max == True, '{} not bounded by [0,1]'.format(_value)

    return output