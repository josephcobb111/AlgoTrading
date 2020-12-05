#  Ultimate List of Automated Trading Strategies You Should Know — Part 1



Since the public release of Alpaca’s commission-free trading API, many developers and tech-savvy people have joined our community slack to discuss various aspects of automated trading. We are excited to see many have already started running algorithms in production, while others are testing their algorithms with our paper trading feature, which allows users to play with our API in a real-time simulation environment.

When we started thinking about a trading API service earlier this year, we were looking at only a small segment of algo trading. However, the more users we talked with, the more we realized there are many use cases for automated trading, particularly when considering different time horizons, tools, and objectives.

Today, as a celebration of our public launch and as a welcome message to our new users, we would like to highlight various automated trading strategies to provide you with ideas and opportunities you can explore for your own needs.

Please note that some concepts overlap with others, and not every item necessarily talks about a specific strategy per se, and some of the strategies may not be applicable to the current Alpaca offering.

##(1) Time-Series Momentum/Mean Reversion
Background

(Time-series) momentum and mean reversion are two of the most well known and well-researched concepts in trading. Billions of dollars are put to work by CTAs employing these concepts to produce alpha and create diversified return streams.
What It Is

The fundamental idea of time-series forecasting is to predict future values based on previously observed values. Time-series momentum, also known as trend-following, seeks to generate excess returns through an expectation that the future price return of an asset will be in the same direction as that asset’s return over some lookback period.

Trend-following strategies might define and look for specific price actions, such as range breakouts, volatility jumps, and volume profile skews, or attempt to define a trend based on a moving average that smooths past price movements. One of the simple, well-known strategies is the “simple moving average crossover”, which buys a stock if its short-period moving average value surpasses its long-period moving average value, and sells if the inverse event happens.

Mean-reversion is the expectation that the future price return of an asset will be in the opposite direction of that asset’s return over some lookback period. One of the most popular indicators is the Relative Strength Index, or RSI, which measures the speed and change of price movements using a scale of 0 to 100. For the purposes of trying to assess the likelihood of mean-reversion, a higher RSI value is said to indicate an overbought asset while a lower RSI value is said to indicate an oversold asset.
For Implementation

Trend-following and mean-reversion strategies are easy to understand since they look at a single asset’s time-series and try to make a prediction about that asset’s future return, but there are many ways to interpret the past behavior. You will need access to historical price data and may benefit from an indicator calculator library such as TA-lib. Virtually every trading framework library, including pyalgotrade, backtrader, and pylivetrader, can support these types of strategies.

Here is the Quantopian tutorial with backtest result for moving average crossover:
Quantopian Tutorials
Quantopian is a free online platform for education and creation of investment algorithms. Selected algorithms get…
www.quantopian.com
## (2) Cross-Sectional Momentum/Mean Reversion
### Background: 

In the U.S. stock market, there are more than 6,000 names listed on the exchanges and actively traded every day. One of the hardest problems in stock trading (and also true for global cryptocurrency trading) is how to pick the stocks.
What It Is

Cross-sectional momentum compares the momentum metrics across different stocks to try to predict the future returns of one or more of them. Even if two stocks such as Facebook and Google are indicating a momentum breakout, this may be driven by the market, but you try to beat the market by taking stronger momentum between those signals. Same for mean reversion. The point is that we consider the market movement that drives each individual stock and consider the relative strength of signals across stocks in an effort to produce a strategy that will outperform the market. This tends to be more computationally heavy, since you need to calculate the metrics with potentially tens to hundreds of time-series.
For Implementation

Again, for this type of strategy libraries like TA-Lib may make it easier to calculate the indicators. Also, you may need simultaneous access to multiple symbols’ price data. IEX’s API can provide up daily bar data for up to 100 stocks per query.

A medium post about cross-sectional study:
Basics of Backtest and Cross-sectional Momentum
medium.com
## (3) Dollar Cost Averaging
###Background: 

This is one of the simplest automated trading strategies and it is widely used by many investors.
What It Is

The idea is to invest a fixed amount of money into an asset periodically. You may doubt it, but some research indicates that this works in the real world, especially long-term. The logic behind it is that price fluctuates many times, and you may buy the stock cheaper overall compared to just investing in the stock at one point in time.

Remember, all of you who contribute to your 401k account are basically doing this. However, you might never think about doing it yourself, simply because there has been no easy way to automate this process.
For Implementation

Now with Alpaca trading API, it’s much simpler and provides much more flexibility.
## (4) Market Making
###Background: 

Market makers are important intermediaries who stand ready to buy and sell securities continuously. By doing this, they provide much-needed liquidity and are compensated for their inventory risk primarily by capturing bid-ask spreads.

Market making used to be done primarily by humans, who worked as floor traders in the pits, but now it’s almost entirely performed by machines. As exchanges have become more and more electronic, the strategy market makers employ has naturally required automation.
What It Is

There are a variety of approaches to market making but most typically rely upon successful inventory management through hedging and limiting adverse selection.

Some market makers may have very tight exposure limits and seek to turn over their positions quickly with the goal of being flat at the end of each day. Others may operate on a much longer horizon, carrying a large and diverse portfolio of securities long and short indefinitely. Undoubtedly, for any market maker, speed helps. The speed of calculation allows the market maker to continuously update its pricing and portfolio risk models, while the speed of execution allows the market maker to act on its models in a timely manner in an effort to reduce adverse selection and get better pricing on its hedges.

Competitive market makers need high-resolution data and a low latency infrastructure, although typically the longer their trading horizon is, the less sensitive they are to these things, and a smart but slow model goes a long way.
For Implementation

Also, in order to process vast amounts of data quickly and handle concurrency, languages like python may not be suitable. Go/Rust would be a good choice for balance between ease of concurrency handling and processing speed, as well as functional languages like Erlang/OCaml or good old languages like C++.

Some high-level explanation of market making:
How profitable is market making on different exchanges
Market making is a trading strategy that lets traders make money when executed with relatively stable instruments…
rados.io

## (5) Day Trading Automation
### Background: 

Lots of day traders develop their trading strategies based on a mechanical set of conditions that are first based on intuition. Since manual day trading involves continuously assessing market conditions and making discretionary trading decisions on the spot, it can often be very physically and emotionally draining. Because the strategies are based on some rules or heuristics which can be codified, it is natural to think they can be automated, which is likely the case.
What It Is

One of the very well-known day trading strategies is the gap-up momentum strategy.

Suppose between the previous market close and next market open there is a positive earnings report. The market opens with a big gap, drawing lots of traders’ attention, and the price keeps going up for a while in the morning (but may not continue for long).

This strategy seeks to capture this follow-through momentum. The challenge here is that not all gap-up stocks keep going up, and among a handful of screened stocks, you need to watch each one’s price action simultaneously.

Some traders may enter on a price breakout from a certain price resistance level, while others may wait to see a chart pattern form to determine the first bottom before going higher. Day trading often relies on analyzing the stock’s price chart and fine-tuning the algorithm to capture the price action can be tricky. That said, once it’s well developed, you are letting your bot trade on your behalf as if you were trading manually, and now you don’t need to monitor the markets and you can also monitor more stocks at the same time without any emotions affecting your trade execution, which is very compelling.
For Implementation

The main thing you need for this is access to market data. You may not even need indicator calculations but instead, you may need a stock screening library such as pipeline-live. The latency typically isn’t so important, so you don’t need to write your system in C++. Python, as well as other lightweight languages, are likely sufficient.
