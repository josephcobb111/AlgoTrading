## Very first algorithmic trading strategy
## Date: 12/04/2020
## Authors: Joseph Cobb
## Contributors: Jeffrey Wubbenhorst

## Strategy
## At the end of each trading day look up stocks with a day high price within
## 99% of the 52 week high price and submit open market order for following day
## List of eligible stocks includes every stock in S&P 500
## During market hours, only open positions will be monitored
## Positions with a profit or loss of 1% will be closed with a market order
## No more than 50% of portfolio will be allocated to open positions
## 1% of portfolio will be allocated to each position
## Stocks with open positions will not be eligible for new positions

## TO DO:
## Implement logic to indicate times market is open (9:30AM-4PM M-F)
## Implement logic to limit position size to 1%
## Implement logic to limit open positions per ticker to 1
## Implement logic to integrate all 500 S&P 500 stocks

import os
import pandas as pd
import robin_stocks as rs

# pull credentials from environment
robin_user = os.environ.get('robinhood_username')
robin_pass = os.environ.get('robinhood_password')

# login to Robinhood
rs.login(username=robin_user,
         password=robin_pass,
         expiresIn=86400,
         by_sms=True)

# strategy parameters
profit_target = 0.01
stop_loss = -0.01

# get list of S&P 500 tickers
table = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
df = table[0]
sp500_tickers = df['Symbol'].tolist()

# run once after hours
# get 52 week high
high_52_weeks = rs.stocks.get_fundamentals(inputSymbols='MA', info='high_52_weeks')
mastercard_high_52_weeks = float(high_52_weeks[0])

# get day high
high_day = rs.stocks.get_fundamentals(inputSymbols='MA', info='high')
mastercard_high_day = float(high_day[0])

# if day high within 99% of 52 week high then place buy order
if mastercard_high_day >= 0.99*mastercard_high_52_weeks:
    rs.orders.order_buy_fractional_by_price(symbol='MA',
                                            amountInDollars=1,
                                            timeInForce='gtc',
                                            extendedHours=False)

# run continuously during market hours
# build current portfolio holdings
holdings = rs.account.build_holdings()

# for each holding:
# close positions at 1% profit
# close positions at 1% loss
for ticker in holdings.keys():
    percent_change = float(holdings[ticker]['percent_change'][0])
    quantity = float(holdings[ticker]['quantity'][0])
    if percent_change >= profit_target:
        rs.orders.order_sell_fractional_by_quantity(symbol=ticker,
                                                    quantity=quantity,
                                                    timeInForce='gtc',
                                                    extendedHours=False)
        holdings.pop(ticker) # remove ticker from holdings
    elif percent_change <= stop_loss:
        rs.orders.order_sell_fractional_by_quantity(symbol=ticker,
                                                    quantity=quantity,
                                                    timeInForce='gtc',
                                                    extendedHours=False)
        holdings.pop(ticker) # remove ticker from holdings
