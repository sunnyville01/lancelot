import json
import time
import requests
import sqlite3
from os import path
import urllib.request
from operator import itemgetter
import pandas as pd

# Loop through all coins
    # check if last 1D candle is red
    #     check if the high of the last green candle is 40% higher than the close of this 1D candle
    #         append this coin to the list

# Manual: Put buy orders in the red region of the Fibionaci retracement, after analyzing the chart
class Lancelot:

    def __init__(self, interval):

        self.interval = interval
        self.bittrex_coins = []
        self.binance_coins = []
        self.bittrex_ignore = []
        self.binance_ignore = ["VEN", "HSR", "TRIG", "CHAT"]
        self.results = []

        # Connect to Database
        self.conn = sqlite3.connect('lancelot.db')
        self.c = self.conn.cursor()

        self.get_coins()
        self.loop_coins()

    def get_coins(self):

        # bittrex coins
        bittrex_url = 'https://api.bittrex.com/api/v1.1/public/getmarkets'
        bittrex_markets = requests.get(bittrex_url).json()["result"]
        btc_markets_bittrex = [d for d in bittrex_markets if d["BaseCurrency"] == "BTC"]
        for market in btc_markets_bittrex:
            self.bittrex_coins.append(market["MarketCurrency"])

        # binance coins
        binance_url = "https://api.binance.com/api/v1/exchangeInfo"
        binance_markets = requests.get(binance_url).json()["symbols"]
        btc_markets_binance = [d for d in binance_markets if d["symbol"].endswith("BTC")]
        for market in btc_markets_binance:
            symbol = market["symbol"][:-3]
            self.binance_coins.append(symbol)


    def loop_coins(self):

        print("Bittrex Coins:")
        for coin in self.bittrex_coins:
            try:
                if coin in self.bittrex_ignore:
                    continue
                print(coin)
                market = "BTC-"+ coin
                url = "https://international.bittrex.com/Api/v2.0/pub/market/GetTicks?_=154849081700&marketName="+ market +"&tickInterval=day"
                json_data = requests.get(url).json()["result"]
                if self.interval == 'W':
                    df = pd.DataFrame(json_data)
                    df['T'] = pd.to_datetime(df['T'])
                    df = df.set_index("T")
                    df = df[["O", "H", "L", "C"]]
                    df1W = df.resample('W').agg({'O': 'first', 'H': 'max', 'L': 'min', 'C': 'last'})
                    df1W = df1W.to_dict(orient='records')
                    ohlc_data = list(reversed(df1W))
                else:
                    ohlc_data = list(reversed(json_data))
                criteria_1 = False
                for item in ohlc_data:
                    is_green = self.is_green(item, "bittrex")
                    if is_green == False:
                        if criteria_1 == False:
                            price_close = item["C"]
                            criteria_1 = True
                    else:
                        if criteria_1 == True:
                            price_high = item["H"]
                            pct_change =  ((price_high - price_close) / price_high) * 100
                            if pct_change > 30:
                                self.results.append({"Coin":coin, "Change":pct_change, "Exchange": "Bittrex"})
                        break
                time.sleep(1)
            except Exception as e:
                print(e)


        print("\n")
        print("Binance Coins:")
        for coin in self.binance_coins:

            try:
                if coin in self.binance_ignore:
                    continue
                print(coin)
                market = coin +"BTC"
                interval_tag = '1d' if self.interval == "D" else '1w'
                url = "https://api.binance.com/api/v1/klines?symbol="+ market +"&interval="+ interval_tag
                json_data = requests.get(url).json()
                ohlc_data = list(reversed(json_data))
                criteria_1 = False
                for item in ohlc_data:
                    is_green = self.is_green(item, "binance")
                    if is_green == False:
                        if criteria_1 == False:
                            price_close = float(item[4])
                            criteria_1 = True
                    else:
                        if criteria_1 == True:
                            price_high = float(item[2])
                            pct_change =  ((price_high - price_close) / price_high) * 100
                            if pct_change > 30:
                                self.results.append({"Coin":coin, "Change":pct_change, "Exchange": "Binance"})
                        break
                time.sleep(1)

            except Exception as e:
                print(e)


        self.results = sorted(self.results, key=itemgetter('Exchange'))
        print(self.results)

        if self.interval == 'D':
            self.c.execute("DELETE FROM results_D") # Remove previous prices from table
            self.conn.commit()
            for result in self.results:
                self.c.execute("INSERT INTO results_D (Coin, Change, Exchange) VALUES (?, ?, ?)",
                    (result["Coin"], result["Change"], result["Exchange"]))
                self.conn.commit()
        else:
            self.c.execute("DELETE FROM results_W") # Remove previous prices from table
            self.conn.commit()
            for result in self.results:
                self.c.execute("INSERT INTO results_W (Coin, Change, Exchange) VALUES (?, ?, ?)",
                    (result["Coin"], result["Change"], result["Exchange"]))
                self.conn.commit()

    def is_green(self, item, exchange):
        if exchange == "bittrex":
            if item["C"] > item["O"]:
                return True
            return False
        elif exchange == "binance":
            if float(item[4]) > float(item[1]):
                return True
            return False


if __name__ == '__main__':

    while True:
        interval = input("Interval (D/W):\n")
        interval = interval.upper()
        if interval in ('D', 'W'):
            break

    i = Lancelot(interval)
