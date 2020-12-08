## Very first algorithmic trading strategy
## Date: 12/04/2020
## Authors: Joseph Cobb
## Contributors: Jeffrey Wubbenhorst

## Strategy
## Find stocks within 99.9% of their 52 week high
## Open long positions
## Set take profit and stop loss levels

## TO DO:
## Implement logic to assess multiple tickers for trades
## Implement logic to limit open positions per ticker to 1
## Implement logic to limit position size

import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from dateutil import parser
from time import sleep
import logging
import robin_stocks as rs

def robinhood_login(robin_user=os.environ.get('robinhood_username'), robin_pass=os.environ.get('robinhood_password')):
    """Login to Robinhood."""
    rs.login(username=robin_user,
             password=robin_pass,
             expiresIn=86400,
             by_sms=True)

def get_next_market_open_hours(market='XNYS'):
    """Get next market open hours. Default market is NYSE for US market hours."""
    today_market_open_dict = rs.markets.get_market_today_hours(market=market)
    current_time = parser.parse(datetime.now(timezone.utc).isoformat())
    if today_market_open_dict['is_open'] and current_time < parser.parse(today_market_open_dict['closes_at']):
        print('today open')
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

def check_for_day_trades():
    """Get number of day trades used on the account"""
    # check we have at least one day trade available
    account = rs.profiles.load_account_profile('account_number')
    url = rs.urls.daytrades(account)

    headers = rs.globals.SESSION.headers
    rs.globals.SESSION.headers['X-Robinhood-API-Version'] = '1.315.0'

    results = rs.helper.request_get(url)
    stock_day_trades = results['equity_day_trades']
    options_day_trades = results['option_day_trades']
    day_trades = len(stock_day_trades) + len(options_day_trades)

    rs.globals.SESSION.headers = headers

    return day_trades


# create logger'
logger = logging.getLogger('seed.py')
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler('seed.log')
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


### some parameters ###
ticker = 'TTD'
take_profit = 0.015 # as a percentage
stop_loss = -0.005 # as a percentage
cash_allocation = 0.1
proximity_to_new_high_52_weeks = 0.999 # right at 52 week high
#######################

while True:
    # login to Robinhood
    try:
        robinhood_login()
        logger.info('Robinhood login successful.')
    except:
        logger.info('Robinhood login failed.')

    # get next market open and close times
    try:
        market_opens, market_closes = get_next_market_open_hours()
        logger.info('Market opens {} and closes {}.'.format(market_opens, market_closes))
    except:
        logger.info('Get market times failed.')
    current_time = parser.parse(datetime.now(timezone.utc).isoformat())

    day_trades = check_for_day_trades()
    if day_trades < 0 or day_trades > 2:
        logger.info("WARNING: Must have less at least 1 day trades available to trade.")
        break
    # while market is open, execute trading strategy
    while (current_time >= market_opens) & (current_time < market_closes):
        # get current portfolio and uninvested cash values
        try:
            total_portfolio_value = float(rs.profiles.load_portfolio_profile()['equity'])
        except:
            logger.info('Failed to get total portfolio value.')
        try:
            uninvested_cash = float(rs.account.load_phoenix_account()['uninvested_cash']['amount'])
        except:
            logger.info('Failed to get uninvested cash.')
        # get latest price and 52 week high prices
        try:
            latest_price = float(rs.stocks.get_latest_price(inputSymbols=ticker)[0])
        except:
            logger.info('Failed to get latest ticker price.')
        try:
            high_52_weeks = float(rs.stocks.get_fundamentals(inputSymbols=ticker,info='high_52_weeks')[0])
        except:
            logger.info('Failed to get 52 week high.')
        # if <10% of portfolio is cash, do nothing
        if uninvested_cash/total_portfolio_value < cash_allocation:
            logger.info('Do nothing. Less than 10% of portfolio in cash.')
            pass
        else:
            # if day high within 99% of 52 week high then place buy order
            if (latest_price/high_52_weeks) >= proximity_to_new_high_52_weeks:
                rs.orders.order_buy_fractional_by_price(symbol=ticker,
                                                        amountInDollars=uninvested_cash,
                                                        timeInForce='gfd',
                                                        extendedHours=False)
                logger.info('Submit buy order. Ticker: {} Amount: {}'.format(ticker, uninvested_cash))

        # build current portfolio holdings
        holdings = rs.account.build_holdings()
        for symbol in holdings.keys():
            percentchange = float(holdings[symbol]['percent_change'])
            # take profit
            if percentchange >= take_profit:
                quantity = float(holdings[symbol]['quantity'][0])
                rs.orders.order_sell_fractional_by_quantity(symbol=symbol,
                                                            quantity=quantity,
                                                            timeInForce='gtc',
                                                            extendedHours=False)
                logger.info('Submit take profit sell order. Ticker: {} Percent Gain: {}'.format(
                symbol, percentchange))
            # stop loss
            elif percentchange <= stop_loss:
                quantity = float(holdings[symbol]['quantity'][0])
                rs.orders.order_sell_fractional_by_quantity(symbol=symbol,
                                                            quantity=quantity,
                                                            timeInForce='gtc',
                                                            extendedHours=False)
                logger.info('Submit stop loss profit sell order. Ticker: {} Percent Loss: {}'.format(
                symbol, percentchange))
        # delay to prevent overwhelming Robinhood API
        sleep(15)

        ### get new current time
        current_time = parser.parse(datetime.now(timezone.utc).isoformat())
        pass

    # logout while market closed
    rs.logout()

    # seconds until next market open
    wait_time = max(seconds_until_market_open(market_opens),0)
    logger.info('Market closed. Waiting {} until next market open.'.format(timedelta(seconds=wait_time)))
    sleep(wait_time)
