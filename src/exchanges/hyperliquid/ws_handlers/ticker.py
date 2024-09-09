from abc import ABC, abstractmethod
from typing import Dict, List
from datetime import datetime, timedelta

def get_next_round_hour_timestamp() -> float:
    now = datetime.now()
    next_hour = now.replace(microsecond=0, second=0, minute=0) + timedelta(hours=1)
    return next_hour.timestamp()

class HlTickerHandler():
    """
    A base class for handling ticker data.

    This class provides methods for managing ticker data,
    including abstract methods for refreshing and processing
    ticker data, which should be implemented by subclasses.
    """

    def __init__(self, ticker: Dict, symbol: str) -> None:
        """
        Initializes the TickerHandler class with a ticker dictionary.

        Parameters
        ----------
        ticker : dict
            A dictionary to store ticker data.
        """
        self.ticker = ticker
        self.format = {
            "markPrice": 0.0,
            "indexPrice": 0.0,
            "fundingTime": 0.0,
            "fundingRate": 0.0,
        }
        self.symbol = symbol
        
    def time_to_funding_ms(self) -> float:
        expiry_time = get_next_round_hour_timestamp()
        now = datetime.now().timestamp()
        return (expiry_time - now) * 1000    

    @abstractmethod
    def refresh(self, recv: Dict) -> None:
        """
        Refreshes the ticker data with new data.

        This method should be implemented by subclasses to process
        new ticker data and update the ticker dictionary.

        Parameters
        ----------
        recv : Dict
            The received payload containing the ticker data.
        """
        for idx in range(len(recv[0]["universe"])):
            if recv[0]["universe"][idx]["name"] == self.symbol:
                asset_ctx = recv[1][idx]
                break 
        self.format["markPrice"] = float(asset_ctx["markPx"])
        self.format["indexPrice"] = float(asset_ctx["oraclePx"])
        self.format["fundingTime"] = self.time_to_funding_ms()
        self.format["fundingRate"] = float(asset_ctx["funding"])
        self.ticker.update(self.format)

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming ticker data to update the ticker dictionary.

        This method should be implemented by subclasses to process
        incoming ticker data and update the ticker dictionary.

        Parameters
        ----------
        recv : Dict
            The received payload containing the ticker data.

        Steps
        -----
        1. Extract the ticker data from the recv payload.
           -> Ensure the following data points are present:
                - Mark price
                - Index price (if not available, use mark/oracle price)
                - Next funding timestamp
                - Funding rate
        2. Overwrite the self.format dict with the respective values.
        3. Call self.ticker.update(self.format).
        """
        asset_ctx = recv["data"]
        if asset_ctx["coin"] != self.symbol:
            return
        self.format["markPrice"] = float(asset_ctx["ctx"]["markPx"])
        self.format["indexPrice"] = float(asset_ctx["ctx"]["oraclePx"])
        self.format["fundingTime"] = self.time_to_funding_ms()
        self.format["fundingRate"] = float(asset_ctx["ctx"]["funding"])
        self.ticker.update(self.format)