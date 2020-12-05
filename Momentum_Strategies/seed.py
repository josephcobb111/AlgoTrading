## Very first algorithmic trading strategy
## Date: 12/04/2020
## Authors: Joseph Cobb
## Contributors: Jeffrey Wubbenhorst

## Strategy
## Find stocks within 99% of their 52 week high
## Open long positions
## Set trailing stop loss

## TO DO:
## Implement logic to avoid pattern day trader (PDT) label
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
    """Get next market open hours. Default market is NYSE."""
    market_open_dict = rs.markets.get_market_next_open_hours(market=market)
    market_opens = parser.parse(market_open_dict['opens_at'])
    market_closes = parser.parse(market_open_dict['closes_at'])
    return market_opens, market_closes


def seconds_until_market_open(market_opens):
    """Get seconds until market opens."""
    current_time = parser.parse(datetime.now(timezone.utc).isoformat())
    return np.floor((market_opens - current_time).total_seconds())


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
trail_stop_loss_type = 'percentage'
trail_stop_loss_amount = 0.01
cash_allocation = 0.1
proximity_to_new_high_52_weeks = 0.99
#######################

while True:
    # login to Robinhood
    robinhood_login()

    # get next market open and close times
    market_opens, market_closes = get_next_market_open_hours()
    current_time = parser.parse(datetime.now(timezone.utc).isoformat())

    # while market is open, execute trading strategy
    while (current_time >= market_opens) & (current_time < market_closes):
        # get current portfolio and uninvested cash values
        total_portfolio_value = float(rs.profiles.load_portfolio_profile()['equity'])
        uninvested_cash = float(rs.account.load_phoenix_account()['uninvested_cash']['amount'])
        # get high for day and 52 week high prices
        high_today = float(rs.stocks.get_fundamentals(inputSymbols=ticker,info='high')[0])
        high_52_weeks = float(rs.stocks.get_fundamentals(inputSymbols=ticker,info='high_52_weeks')[0])
        # if <10% of portfolio is cash, do nothing
        if uninvested_cash/total_portfolio_value < cash_allocation:
            pass
        else:
            # if day high within 99% of 52 week high then place buy order
            if (high_today/high_52_weeks) >= proximity_to_new_high_52_weeks:
                rs.orders.order_buy_fractional_by_price(symbol=ticker,
                                                        amountInDollars=uninvested_cash,
                                                        timeInForce='gfd',
                                                        extendedHours=False)
                logger.info('submit buy order. ticker: {} amount: {}'.format(ticker, uninvested_cash))

            # build current portfolio holdings
            holdings = rs.account.build_holdings()
            quantity = float(holdings[ticker]['quantity'][0])
            rs.orders.order_trailing_stop(symbol=ticker,
                                          quantity=quantity,
                                          side='sell',
                                          trailAmount=trail_stop_loss_amount,
                                          trailType=trail_stop_loss_type,
                                          timeInForce='gtc',
                                          extendedHours=False)

            logger.info('submit trailing stop sell order. ticker: {} type: {} amount: {}'.format(
                ticker, trail_stop_loss_type, trail_stop_loss_amount))
        # delay to prevent overwhelming Robinhood API
        sleep(15)

        ### get new current time
        current_time = datetime.now(timezone.utc).isoformat()
        pass

    # logout while market closed
    rs.logout()

    # seconds until next market open
    wait_time = max(seconds_until_market_open(market_opens),0)
    sleep(wait_time)