import numpy as np
import pandas as pd

from datetime import datetime, timedelta, timezone
from dateutil import parser
from time import sleep

import robin_stocks.robinhood as rs
from algotrading.utils import (robinhood_login, find_nearest_weekday_date, get_implied_volatility_data,
                               get_recent_open_option_tickers, get_next_market_open_hours, seconds_until_market_open,
                               create_logger)


# set parameters of trading strategy
weekday_num = 4
option_type = 'call'
day_lag = 7
max_daily_open_positions = 1
iv_rank_min = 0.5
iv_percentile_min = 0.5
total_option_volume_min = 50000
target_delta = .30
days_until_expiration_range = [30, 45]
delta_tolerance =  0.025
option_volume_min = 10
option_open_interest_min = 100
max_strike_width = 1
min_percent_return = 0.3
profit_target_percent = 0.5
trade_logging_file_path = '../trade_histories/call_credit_spread.csv'

logger = create_logger(filename='call_credit_spread.py', logname='call_credit_spread.log')


def main():
    # login to Robinhood
    robinhood_login()
    logger.info('Robinhood login successful.')

    market_opens, market_closes = get_next_market_open_hours()
    logger.info('Market opens {} and closes {}.'.format(market_opens, market_closes))
    current_time = parser.parse(datetime.now(timezone.utc).isoformat())

    daily_open_positions = 0
    # while market is open, execute trading strategy
    while (current_time >= market_opens) & (current_time < market_closes) & (daily_open_positions < max_daily_open_positions):
        # get nearest Friday expiration
        nearest_friday_expiration = find_nearest_weekday_date(
            days_until_expiration_range=days_until_expiration_range,
            weekday_num=weekday_num,
        )

        # get implied volatility data
        iv_data = get_implied_volatility_data()

        # filter to tickers with high IV and volume
        ticker_list = iv_data.loc[
            (iv_data.optionsImpliedVolatilityRank1y > iv_rank_min) &
            (iv_data.optionsImpliedVolatilityPercentile1y > iv_percentile_min) &
            (iv_data.optionsTotalVolume > total_option_volume_min)
        ]['symbol'].tolist()

        # get recent open positions
        remove_tickers = get_recent_open_option_tickers(option_type, day_lag)

        # remove tickers of positions from list
        for _ticker in remove_tickers:
            if _ticker in ticker_list:
                ticker_list.remove(_ticker)

        # create call credit spread trades dataframe
        call_credit_spread_trades = pd.DataFrame(
            data=[],
            columns=[
                'symbol',
                'type',
                'expiration_date',
                'short_strike_price',
                'short_mark_price',
                'short_ask_price',
                'short_bid_price',
                'short_spread',
                'short_volume',
                'short_open_interest',
                'short_delta',
                'short_gamma',
                'short_rho',
                'short_theta',
                'short_vega',
                'long_strike_price',
                'long_mark_price',
                'long_ask_price',
                'long_bid_price',
                'long_spread',
                'long_volume',
                'long_open_interest',
                'long_delta',
                'long_gamma',
                'long_rho',
                'long_theta',
                'long_vega',
                'trade_strike_width',
                'trade_limit_price',
                'trade_spread',
                'trade_spread_ratio',
                'avg_trade_volume',
                'trade_expected_dollar_return',
                'trade_expected_percent_return'
            ],)

        # sort through each ticker looking for possible trades
        for _ticker in ticker_list:
            try:
                expiration_option_chain_data = pd.DataFrame(
                    rs.options.find_options_by_expiration(
                        inputSymbols=_ticker,
                        expirationDate=nearest_friday_expiration,
                        optionType='call',)
                )
            except TypeError:
                expiration_option_chain_data = pd.DataFrame()

            if not expiration_option_chain_data.empty:
                short_call_df = expiration_option_chain_data.loc[
                    (abs(expiration_option_chain_data.delta.astype(float) - target_delta) <= delta_tolerance) &
                    (expiration_option_chain_data.volume.astype(float) >= option_volume_min) &
                    (expiration_option_chain_data.open_interest.astype(float) >= option_open_interest_min)
                ].copy()

                if short_call_df.shape[0] > 0:
                    if short_call_df.shape[0] > 1:
                        short_call_df.sort_values(by='volume', ascending=False, inplace=True)
                        short_call_df.reset_index(drop=True, inplace=True)
                        short_call_df = short_call_df.loc[short_call_df.index==0]

                    _symbol = short_call_df['symbol'].astype(str).values[0]
                    _type = 'call credit spread'
                    _expiration_date = short_call_df['expiration_date'].astype(str).values[0]
                    _short_strike_price = short_call_df['strike_price'].astype(float).values[0]
                    _short_mark_price = short_call_df['mark_price'].astype(float).values[0]
                    _short_ask_price = short_call_df['ask_price'].astype(float).values[0]
                    _short_bid_price = short_call_df['bid_price'].astype(float).values[0]
                    _short_spread = _short_ask_price - _short_bid_price
                    _short_volume = short_call_df['volume'].astype(float).values[0]
                    _short_open_interest = short_call_df['open_interest'].astype(float).values[0]
                    _short_delta = short_call_df['delta'].astype(float).values[0]
                    _short_gamma = short_call_df['gamma'].astype(float).values[0]
                    _short_rho = short_call_df['rho'].astype(float).values[0]
                    _short_theta = short_call_df['theta'].astype(float).values[0]
                    _short_vega = short_call_df['vega'].astype(float).values[0]

                    # to do: cast expiration_option_chain_data columns to float type
                    expiration_option_chain_data['strike_price'] = expiration_option_chain_data['strike_price'].astype(float)

                    long_call_df = expiration_option_chain_data.loc[
                        expiration_option_chain_data['strike_price'] > _short_strike_price
                    ].sort_values(by='strike_price', ascending=True).head(1)

                    _long_strike_price = long_call_df['strike_price'].astype(float).values[0]
                    _long_mark_price = long_call_df['mark_price'].astype(float).values[0]
                    _long_ask_price = long_call_df['ask_price'].astype(float).values[0]
                    _long_bid_price = long_call_df['bid_price'].astype(float).values[0]
                    _long_spread = _long_ask_price - _long_bid_price
                    _long_volume = long_call_df['volume'].astype(float).values[0]
                    _long_open_interest = long_call_df['open_interest'].astype(float).values[0]
                    _long_delta = long_call_df['delta'].astype(float).values[0]
                    _long_gamma = long_call_df['gamma'].astype(float).values[0]
                    _long_rho = long_call_df['rho'].astype(float).values[0]
                    _long_theta = long_call_df['theta'].astype(float).values[0]
                    _long_vega = long_call_df['vega'].astype(float).values[0]

                    _trade_strike_width = _long_strike_price - _short_strike_price
                    _trade_limit_price = _short_mark_price - _long_mark_price
                    _trade_spread = _short_ask_price - _long_bid_price
                    _trade_spread_ratio = _trade_spread / _trade_strike_width
                    _avg_trade_volume = (_short_volume + _long_volume) / 2
                    _trade_expected_dollar_return = (1 - _short_delta) * _trade_limit_price
                    _trade_expected_percent_return = _trade_expected_dollar_return / (_trade_strike_width - _trade_limit_price)

                    call_credit_spread_trades.loc[-1] = [
                        _symbol,
                        _type,
                        _expiration_date,
                        _short_strike_price,
                        _short_mark_price,
                        _short_ask_price,
                        _short_bid_price,
                        _short_spread,
                        _short_volume,
                        _short_open_interest,
                        _short_delta,
                        _short_gamma,
                        _short_rho,
                        _short_theta,
                        _short_vega,_long_strike_price,
                        _long_mark_price,
                        _long_ask_price,
                        _long_bid_price,
                        _long_spread,
                        _long_volume,
                        _long_open_interest,
                        _long_delta,
                        _long_gamma,
                        _long_rho,
                        _long_theta,
                        _long_vega,
                        _trade_strike_width,
                        _trade_limit_price,
                        _trade_spread,
                        _trade_spread_ratio,
                        _avg_trade_volume,
                        _trade_expected_dollar_return,
                        _trade_expected_percent_return,
                    ]

                    call_credit_spread_trades.index += 1

        # identify possible trades to execute, if any
        possible_call_credit_spread_trades = call_credit_spread_trades.loc[
            (call_credit_spread_trades.trade_strike_width <= max_strike_width) &
            (call_credit_spread_trades.trade_expected_percent_return > min_percent_return)
        ].sort_values(by='avg_trade_volume', ascending=True)

        # select a trade to execute, if any
        if possible_call_credit_spread_trades.shape[0] > 0:
            call_credit_spread_trade = possible_call_credit_spread_trades.iloc[-1]

            # set option orders as list
            call_credit_spread_open_order_list = [
                {'expirationDate': call_credit_spread_trade['expiration_date'],
                 'strike': call_credit_spread_trade['short_strike_price'],
                 'optionType': 'call',
                 'effect': 'open',
                 'action': 'sell',},
                {'expirationDate': call_credit_spread_trade['expiration_date'],
                 'strike': call_credit_spread_trade['long_strike_price'],
                 'optionType': 'call',
                 'effect': 'open',
                 'action': 'buy',},
            ]

            # send order to Robinhood
            call_credit_spread_open_order_receipt = rs.order_option_credit_spread(
                price=call_credit_spread_trade['trade_limit_price'].round(2),
                symbol=call_credit_spread_trade['symbol'],
                quantity=1,
                spread=call_credit_spread_open_order_list,
                timeInForce='gfd',
            )

            # check order status
            updated_call_credit_spread_open_order_receipt = rs.get_option_order_info(
                order_id=call_credit_spread_open_order_receipt['id'],
            )

            # check until trade is executed or canceled
            check_for_trade_execution = True
            while check_for_trade_execution:
                updated_call_credit_spread_open_order_receipt = rs.get_option_order_info(
                    order_id=call_credit_spread_open_order_receipt['id'],
                )
                if updated_call_credit_spread_open_order_receipt['state'] == 'filled':
                    trade_filled = True
                    check_for_trade_execution = False
                elif updated_call_credit_spread_open_order_receipt['state'] == 'cancelled':
                    trade_filled = False
                    check_for_trade_execution = False
                else:
                    # sleep for 5 minutes
                    sleep(300)

            if trade_filled:
                # send closing trade order to Robinhood
                if updated_call_credit_spread_open_order_receipt['state'] == 'filled':
                    call_credit_spread_close_order_list = [
                        {'expirationDate': call_credit_spread_trade['expiration_date'],
                         'strike': call_credit_spread_trade['short_strike_price'],
                         'optionType': 'call',
                         'effect': 'close',
                         'action': 'buy',},
                        {'expirationDate': call_credit_spread_trade['expiration_date'],
                         'strike': call_credit_spread_trade['long_strike_price'],
                         'optionType': 'call',
                         'effect': 'close',
                         'action': 'sell',},
                    ]

                    call_credit_spread_close_order_receipt = rs.order_option_debit_spread(
                        price=(call_credit_spread_trade['trade_limit_price'] * profit_target_percent).round(2),
                        symbol=call_credit_spread_trade['symbol'],
                        quantity=1,
                        spread=call_credit_spread_close_order_list,
                        timeInForce='gtc',
                    )

                updated_call_credit_spread_close_order_receipt = rs.get_option_order_info(
                    order_id=call_credit_spread_close_order_receipt['id'],
                )

                call_credit_spread_logging = pd.read_csv(trade_logging_file_path)
                call_credit_spread_logging_new_trade = pd.DataFrame(call_credit_spread_trade).T.round(6)

                for _col in call_credit_spread_logging_new_trade.columns:
                    if _col not in ['index', 'symbol', 'type', 'expiration_date']:
                        call_credit_spread_logging_new_trade[_col] = call_credit_spread_logging_new_trade[_col].astype(float).round(6)

                call_credit_spread_logging_new_trade['trade_open_id'] = call_credit_spread_open_order_receipt['id']
                call_credit_spread_logging_new_trade['trade_close_id'] = call_credit_spread_close_order_receipt['id']

                if 'index' in call_credit_spread_logging_new_trade.columns:
                    call_credit_spread_logging_new_trade.drop(columns=['index'], inplace=True)

                call_credit_spread_logging = pd.concat([call_credit_spread_logging, call_credit_spread_logging_new_trade])
                call_credit_spread_logging.drop_duplicates(inplace=True)
                call_credit_spread_logging.to_csv(trade_logging_file_path, index=False)

                daily_open_positions += 1

        # delay to prevent overwhelming Robinhood API
        logger.info('Sleep for 300 seconds.')
        sleep(300)

        ### get new current time
        current_time = parser.parse(datetime.now(timezone.utc).isoformat())
        pass

    # logout while not trading
    rs.logout()
    logger.info('Robinhood logout successful.')

    # pause trading if max daily open positions are reached
    if daily_open_positions >= max_daily_open_positions:
        logger.info('Max daily open positions reached. Sleep for {}.'.format(timedelta(seconds=23400)))
        sleep(23400)

    # seconds until next market open
    wait_time = max(seconds_until_market_open(market_opens), 0)

    # require login at least once per day to avoid error
    wait_time = wait_time/4
    logger.info('Market closed. Waiting {}.'.format(timedelta(seconds=wait_time)))
    sleep(wait_time)


if __name__ == "__main__":
    while True:
        main()
