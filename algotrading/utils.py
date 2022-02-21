import logging
import os
import pyotp
import requests

import numpy as np
import pandas as pd
import robin_stocks.robinhood as rs

from datetime import datetime, timedelta, timezone
from dateutil import parser
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


def get_recent_open_option_tickers(option_type, day_lag):
    open_option_positions = pd.DataFrame(rs.get_open_option_positions())

    open_option_positions['option_type'] = 'Unknown'

    for i, row in open_option_positions.iterrows():
        row['option_type'] = rs.options.get_option_instrument_data_by_id(row['option_id'])['type']

    open_option_positions = open_option_positions.loc[open_option_positions.option_type == option_type]

    all_option_positions = pd.DataFrame(rs.get_all_option_positions())

    recent_option_positions = all_option_positions.loc[
        pd.to_datetime(all_option_positions.updated_at) >=
        pd.to_datetime(datetime.now(tz=timezone.utc) - timedelta(days=day_lag))].copy()

    recent_option_positions['option_type'] = 'Unknown'

    for i, row in recent_option_positions.iterrows():
        row['option_type'] = rs.options.get_option_instrument_data_by_id(row['option_id'])['type']

    recent_option_positions = recent_option_positions.loc[recent_option_positions.option_type == option_type]

    recent_open_tickers = list(
        set(open_option_positions['chain_symbol']) & set(recent_option_positions['chain_symbol']))

    return recent_open_tickers


def get_next_market_open_hours(market='XNYS'):
    """Get next market open hours. Default market is NYSE for US market hours."""
    today_market_open_dict = rs.markets.get_market_today_hours(market=market)
    current_time = parser.parse(datetime.now(timezone.utc).isoformat())
    if today_market_open_dict['is_open'] and current_time < parser.parse(today_market_open_dict['closes_at']):
        market_opens = parser.parse(today_market_open_dict['opens_at'])
        market_closes = parser.parse(today_market_open_dict['closes_at'])
    else:
        next_market_open_dict = rs.markets.get_market_next_open_hours(market=market)
        market_opens = parser.parse(next_market_open_dict['opens_at'])
        market_closes = parser.parse(next_market_open_dict['closes_at'])
    return market_opens, market_closes


def seconds_until_market_open(market_opens):
    """Get seconds until market opens."""
    current_time = parser.parse(datetime.now(timezone.utc).isoformat())
    return np.floor((market_opens - current_time).total_seconds())


def create_logger(filename, logname):
    # create logger'
    logger = logging.getLogger(filename)
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler(logname)
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
