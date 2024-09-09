# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 21:41:47 2024

@author: dalil
"""

import numpy as np
from typing import Dict, List, Union
from src.exchanges.common.localorderbook import BaseOrderbook
from abc import ABC, abstractmethod
from hyperliquid.utils.types import L2BookMsg

class HlOrderBookHandler():
    
    def __init__(self, Orderbook:BaseOrderbook = None ) -> None:
        
        if Orderbook is not None:
            self.orderbook = Orderbook
        else:
            raise ValueError("An orderbook was not provided")
     
    def refresh(self, recv: L2BookMsg) -> None:
        """
        Refreshes the order book data with new data.

        This method should be implemented by subclasses to process
        new order book data and update the order book.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the order book data.

        Steps
        -----
        1. Separate the recv payload into bids and asks.
           -> They should be in the format [Price, Size] per level.
        2. Wrap the lists into numpy arrays (overwrite self.bids & self.asks).
        3. Call self.orderbook.refresh(self.asks, self.bids).
        """
        n = min(len(recv['levels'][0]),len(recv['levels'][1]))  # 112 ns ± 5.97 ns
        bids = np.empty((n, 3), dtype=np.float64)               # 242 ns ± 8.96 ns
        asks = np.empty((n, 3), dtype=np.float64)               # 242 ns ± 8.96 ns
        time = recv['time']
        for i in range(n):
            bidslvldict = recv['levels'][0][i]                          # 356 ns ± 16.1 ns
            askslvldict = recv['levels'][1][i]                          # 356 ns ± 16.1 ns
            bids[i, 0] = bidslvldict['px']                              # 320 ns ± 4.5 ns
            bids[i, 1] = bidslvldict['sz']                                      
            bids[i, 2] = bidslvldict['n']
            asks[i, 0] = askslvldict['px']
            asks[i, 1] = askslvldict['sz']
            asks[i, 2] = askslvldict['n']
                             
        self.orderbook.refresh(bids,asks,time)

    @abstractmethod
    def process(self, recv: Dict) -> None:
        """
        Processes incoming order book data to update the Orderbook.

        This method should be implemented by subclasses to process
        incoming order book data and update the Orderbook.
        Not implemented on HL since the full book is always sent and data always goest to refresh

        Parameters
        ----------
        recv : Dict
            The received payload containing the order book data.

        Steps
        -----
        1. Separate the recv payload into bids and asks.
           -> They should be in the format [Price, Size] per level.
        2. Wrap the lists into numpy arrays (overwrite self.bids & self.asks).
        3. Get the timestamp of the update and update self.timestamp.
        4. Call self.orderbook.update_book(self.asks, self.bids, timestamp).
        """
        n = min(len(recv['data']['levels'][0]),len(recv['data']['levels'][1]))  # 112 ns ± 5.97 ns
        bids = np.empty((n, 3), dtype=np.float64)                               # 242 ns ± 8.96 ns
        asks = np.empty((n, 3), dtype=np.float64)                               # 242 ns ± 8.96 ns
        time = recv['data']['time']
        for i in range(n):
            bidslvldict = recv['data']['levels'][0][i]                          # 356 ns ± 16.1 ns
            askslvldict = recv['data']['levels'][1][i]                          # 356 ns ± 16.1 ns
            bids[i, 0] = bidslvldict['px']                                      # 320 ns ± 4.5 ns
            bids[i, 1] = bidslvldict['sz']                                      
            bids[i, 2] = bidslvldict['n']
            asks[i, 0] = askslvldict['px']
            asks[i, 1] = askslvldict['sz']
            asks[i, 2] = askslvldict['n']
                             
        self.orderbook.refresh(bids,asks,time)

        