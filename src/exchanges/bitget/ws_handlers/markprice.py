from typing import Dict

from src.exchanges.common.ws_handlers.ticker import TickerHandler


class BitgetTickerHandler(TickerHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["ticker"])

    def refresh_ticker(self, recv: Dict) -> None:
        try:
            ticker_data = recv["data"]
            recv_ts = int(ticker_data["ts"])
            
            if recv_ts >= self.ticker["timestamp"]:

                self.format["indexPrice"] = float(
                    ticker_data.get("indexPrice", self.format["indexPrice"])
                )
                self.format["fundingRate"] = float(
                    ticker_data.get("lastFundingRate", self.format["fundingRate"])
                )
                # self.format["fundingTime"] = float(
                #     ticker_data.get("nextFundingTime", self.format["fundingTime"])
                # )
                self.format["timestamp"] = recv_ts
                self.ticker.update(self.format)

        except Exception as e:
            raise Exception(f"Ticker refresh - {e}")
            
    def refresh_mark(self, recv: Dict) -> None:
        try:
            prices_data = recv["data"]
            recv_ts = int(prices_data["ts"])
            if recv_ts >= self.ticker["timestamp"]:
                self.format["indexPrice"] = float(
                    prices_data.get("indexPrice", self.format["indexPrice"])
                    )
                self.format["markPrice"] = float(
                    prices_data.get("markPrice", self.format["markPrice"])
                )
                self.format["timestamp"] = recv_ts
                self.ticker.update(self.format)  
                
        except Exception as e:
            raise Exception(f"Ticker refresh - {e}")
        
    def process(self, recv: Dict) -> None:
        try:
            ticker_data = recv["data"]
            recv_ts = int(ticker_data["ts"])
            if recv_ts >= self.ticker["timestamp"]:
                self.format["markPrice"] = float(ticker_data.get("markPrice", self.format["markPrice"]))
                self.format["indexPrice"] = float(ticker_data.get("markPrice", self.format["indexPrice"]))
                self.format["fundingRate"] = float(
                    ticker_data.get("fundingRate", self.format["fundingRate"])
                )
                self.format["fundingTime"] = float(
                    ticker_data.get("nextFundingTime", self.format["fundingTime"])
                )
                self.format["timestamp"] = recv_ts
                self.ticker.update(self.format)  

        except Exception as e:
            raise Exception(f"Ticker process - {e}")
