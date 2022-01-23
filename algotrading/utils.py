import os
import pyotp
import requests

import pandas as pd
import robin_stocks.robinhood as rs

from datetime import datetime, timedelta
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


def find_nearest_weekday_date(days_until_expiration_range, weekday_num):
    """

    weekday_num : int
        Integer value corresponding to weekday;
            - Monday: 1
            - Tuesday: 2
            - Wednesday: 3
            - Thursday: 4
            - Friday: 5
            - Saturday: 6
            - Sunday: 7
    """
    now = datetime.now()

    start = now + timedelta(days_until_expiration_range[0])
    end = now + timedelta(days_until_expiration_range[1])

    dates_generated = [start + timedelta(days=x) for x in range(0, (end - start).days)]

    weekday_dates = []
    for _date in dates_generated:
        if _date.weekday() == weekday_num:
            weekday_dates.append(_date)

    nearest_weekday_expiration = min(weekday_dates).strftime("%Y-%m-%d")

    return nearest_weekday_expiration


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
        assert _min, '{} not bounded by [0,1]'.format(_value)
        assert _max, '{} not bounded by [0,1]'.format(_value)

    return output
