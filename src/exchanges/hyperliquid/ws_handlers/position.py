from abc import ABC, abstractmethod
from typing import Dict, List, Union
import traceback

from src.exchanges.common.types import Position
from src.exchanges.hyperliquid.types import (
    HlSideConverter,
    HlOrderTypeConverter,
    HlTimeInForceConverter
    )


class HlPositionHandler():
    """
    A class for handling position data.

    This class provides methods for managing position data,
    including abstract methods for refreshing and processing
    position data, which should be implemented by subclasses.
    """
    EPSILON = 1e-6 
    def __init__(self, data: Dict, addr:str, logging) -> None:
        """
        Initializes the PositionHandler class with a position data structure.

        Parameters
        ----------
        position : Position
            A structure to store position data.
        """
        self.data = data
        self.symbol = data["symbol"]
        self.position = data["position"]
        self.orders = data["orders"]
        self.addr = addr.lower()
        self.sideConverter = HlSideConverter()
        self.ticker = data["ticker"]

        self.logging = logging
        self.logging.setFilters("PositionHandler")
        self.logging.setHandlers()
        self.flag = data["flags"]["position"]
        
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the position data with new data.

        This method should be implemented by subclasses to process
        new position data and update the position dictionary.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the position data.

        Steps
        -----
        1. Extract the position from the recv payload. Ensure *at least* the following data points are present:
            - side
            - price
            - size
            - uPnl

        2. Create a Position() instance with the respective values.
        3. self.position = Position()
        """        
        try:
            self.logging.debug(f"Position BEFORE refresh: {self.position}")
            
            if len(recv) > 0: 
                for position in recv:
                    
                    positionDetails = position["position"]
                    
                    if positionDetails["coin"] != self.symbol:
                        continue
                    
                    size = float(positionDetails["szi"])
                    posRefresh = {"entryPrice": float(positionDetails["entryPx"]),
                                  "size": size,
                                  "uPnl": float(positionDetails["unrealizedPnl"]),
                                  "side": int(abs(size)/size),
                                  }
                    self.position.update(**posRefresh)
            
            self.logging.debug(f"Position AFTER refresh: {self.position}")

        except Exception as e:
            self.logging.error(f"traceback: {traceback.print_tb(e.__traceback__)}")
            raise Exception(f"Position Refresh :: {e}")

    def process(self, recv: Dict) -> None:
        """
        Processes incoming position data to update the position.

        This method should be implemented by subclasses to process
        incoming position data and update the position dictionary.

        Parameters
        ----------
        recv : Dict
            The received payload containing the position data.

        Steps
        -----
        1. Extract the position from the recv payload. Ensure *at least* the following data points are present:
            - side
            - price
            - size
            - uPnl

        2. Update the self.position attributes using self.position.update()
        """
        try:
            # self.logging.debug(f"Position BEFORE process: {self.position}")

            if recv["channel"] == "userFills":
                self.logging.info(f"Position BEFORE process: {self.position}")
                self.logging.info("Received userFills")
                if recv["data"]["user"] != self.addr:
                    self.logging.debug("wrong user")
                    return
                
                
                if not recv["data"].get("isSnapshot",False):
                    for fill in recv["data"]["fills"]:
                        if fill["coin"] != self.symbol:
                            self.logging.debug("wrong coin")
                            continue
                        
                        start_size = float(fill["startPosition"])
                        new_size = start_size + self.sideConverter.to_num(fill["side"])*float(fill["sz"])
                        
                        if abs(new_size - 0.0) < self.EPSILON:
                            self.position.reset()
                            continue
                        
                        if start_size*new_size > 0:#position stayed on the same side
                            if abs(new_size) >= abs(start_size): #We increased our position on the same side 
                                new_avg_entry = (self.position._entryPrice*abs(self.position._size) + float(fill["px"])*float(fill["sz"]))/abs(new_size)
                            else: #we decreased position so avg entry price doesnt change
                                new_avg_entry = self.position.entryPrice          
                        else: #Position after fill is not same sign as before, we went from Long > Short or from Short > Long or opened a new position, so avg entry is just the price of the fill
                            new_avg_entry = float(fill["px"]) 
                        
                        uPnL = (new_avg_entry - self.ticker["markPrice"])*new_size                        
                        
                        posProcess = {"size": new_size,
                                      "entryPrice": new_avg_entry,
                                      "uPnl": uPnL if new_size > 0 else -uPnL,
                                      "side": int(abs(new_size)/new_size) ,
                                      "timestamp" : fill["time"] 
                                      }
                        
                        self.position.update(**posProcess)
                self.logging.debug(f"Position AFTER process: {self.position}")

                
            elif recv["channel"] == "webData2":
                self.logging.debug("Received webData2")
                self.data["account_balance"] = float(recv["data"]["clearinghouseState"]["marginSummary"]["accountValue"])
                
                if len(recv["data"]["clearinghouseState"]["assetPositions"]) > 0:
                    found = False
                    for position in recv["data"]["clearinghouseState"]["assetPositions"]:
                        positionDetails = position["position"]
                        
                        if positionDetails["coin"] != self.symbol:
                            continue
                        size = float(positionDetails["szi"])
                        posProcess = {"entryPrice": float(positionDetails["entryPx"]),
                                      "size": size,
                                      "uPnl": float(positionDetails["unrealizedPnl"]),
                                      "side": int(abs(size)/size)
                                      }
                        self.position.update(**posProcess)
                        found = True
                        
                    if not found:
                        self.position.reset()
                else:
                    # if abs(self.position.size - 0.0) > self.EPSILON:
                        self.position.reset()

            # self.logging.debug(f"Position AFTER process: {self.position}")
            
            if abs(self.position.size - 0.0) > self.EPSILON:
                self.flag.set()
                self.logging.debug("Position is non null, flag has been raised")
            else:
                self.flag.clear()
                self.logging.debug("Position neutralized, flag has been cleared")

                
        except Exception as e:
            self.logging.error(f"traceback: {traceback.print_tb(e.__traceback__)}")
            raise Exception(f"Position Process :: {e}")
