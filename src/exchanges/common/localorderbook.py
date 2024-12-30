import numpy as np
from numpy.typing import NDArray
from typing import Dict
from src.tools.Numbas import nbisin, nb_float_to_str,numba_sort_desc,numba_sort_asc
from numba.experimental import jitclass
import numba.types
import time
from numba import njit


spec = [
        ('depth', numba.types.int16),
        ('bids', numba.types.float64[:, :]),
        ('asks', numba.types.float64[:, :]),
        ('bba', numba.types.float64[:, :]),
        ('timestamp', numba.types.float64),
        ('columns', numba.types.int16),
        ('seq_id', numba.types.int32),
        ]

@jitclass(spec)
class BaseOrderbook:
    """
    A base class for maintaining and updating an order book with ask and bid orders.

    Attributes
    ----------
    asks : NDArray
        A NumPy array to store ask orders. Each order is represented by a [price, quantity] pair.
    bids : NDArray
        A NumPy array to store bid orders. Each order is represented by a [price, quantity] pair.

    Methods
    -------
    sort_book():
        Sorts the ask and bid arrays by price in ascending and descending order, respectively.
    update_book(asks_or_bids: NDArray, data: NDArray) -> NDArray:
        Updates the order book (asks or bids) with new data.
    process(recv):
        Abstract method for processing incoming data. To be implemented by derived classes.
    """

    def __init__(self,depth:int, columns:int = 2) -> None:
        """
        Initializes the BaseOrderBook with empty asks and bids arrays. 
        
        Parameters
        ----------
        depth : int
            Amount of levels to keep on each side of the book
        columns : int
            How many columns should the book have. Default is set at 2 so every level is [price,size].
            Ex: Hyperliquid provides number of orders at each lvl so columns = 3 [price,size,qty]
        
        """
        self.depth = depth 
        self.asks = np.zeros((self.depth, columns), dtype= np.float64)
        self.bids = np.zeros((self.depth, columns), dtype= np.float64)
        self.bba = np.zeros((2, columns), dtype= np.float64)
        self.timestamp = 0.0
        self.columns = columns
        self.seq_id = 0
        
    # def sort_bids(self) -> None: # 1.56 µs ± 31.6 ns
    #     """
    #     Sorts the bid orders in descending order of price and updates the best bid.
    #     """
    #     self.bids = self.bids[self.bids[:, 0].argsort()][::-1][: self.depth]
    #     self.bba[0, :] = self.bids[0]

    # def sort_asks(self) -> None: # 1.56 µs ± 31.6 ns
    #     """
    #     Sorts the ask orders in ascending order of price and updates the best ask.
    #     """
    #     self.asks = self.asks[self.asks[:, 0].argsort()][: self.depth]
    #     self.bba[1, :] = self.asks[0]
        
    def sort_bids(self) -> None: #786 ns ± 30.9 ns
        """
        Sorts the bid orders in descending order of price and updates the best bid.
        """
        self.bids = numba_sort_desc(self.bids[: self.depth])  # Sort descending
        self.bba[0, :] = self.bids[0]  # Update best bid
    
    
    def sort_asks(self) -> None: #786 ns ± 30.9 ns
        """
        Sorts the ask orders in ascending order of price and updates the best ask.
        """
        self.asks = numba_sort_asc(self.asks[: self.depth])  # Sort ascending
        self.bba[1, :] = self.asks[0]  # Update best ask

    def refresh(self, bids: NDArray, asks: NDArray, timestamp, new_seq_id) -> None: #1.66 μs ± 32.4 ns
        """
        Refreshes the order book with given *complete* ask and bid data and sorts the book.

        Parameters
        ----------
        asks : Array
            Initial ask orders data, formatted as [[price, size], ...].

        bids : Array
            Initial bid orders data, formatted as [[price, size], ...].
        """
        max_asks_idx = min(asks.shape[0], self.depth)
        max_bids_idx = min(bids.shape[0], self.depth)
        
        self.asks[:max_asks_idx, :self.columns] = asks[:max_asks_idx, :self.columns]
        self.bids[:max_bids_idx, :self.columns] = bids[:max_bids_idx, :self.columns]
        self.timestamp = timestamp

        if new_seq_id == 0:
            self.seq_id += 1
        else:
            self.seq_id = new_seq_id
            
        self.sort_bids()
        self.sort_asks()

    def update_bids(self, bids: NDArray, timestamp, new_seq_id) -> None: #2.36 μs ± 77.5 ns
        """
        Updates the current bids with new data. Removes entries with matching
        prices in update, regardless of size, and then adds non-zero quantity
        data from update to the book.  Useful when new Ob data is given as a delta

        Parameters
        ----------
        bids : Array
            New bid orders data, formatted as [[price, size], ...].
        """
        if bids.size == 0:
            return None
        
        if new_seq_id == 0:
            self.seq_id += 1
        else:
            self.seq_id = new_seq_id

        self.bids = self.bids[~nbisin(self.bids[:, 0], bids[:, 0])]
        self.bids = np.vstack((self.bids, bids[bids[:, 1] != 0]))
        self.sort_bids()
        if self.timestamp < timestamp:
            self.timestamp = timestamp

    def update_asks(self, asks: NDArray, timestamp, new_seq_id) -> None: #2.36 μs ± 77.5 ns
        """
        Updates the current asks with new data. Removes entries with matching
        prices in update, regardless of size, and then adds non-zero quantity
        data from update to the book. Useful when new Ob data is given as a delta

        Parameters
        ----------
        asks : Array
            New ask orders data, formatted as [[price, size], ...].
        """
        if asks.size == 0:
            return None
        
        if new_seq_id == 0:
            self.seq_id += 1
        else:
            self.seq_id = new_seq_id

        self.asks = self.asks[~nbisin(self.asks[:, 0], asks[:, 0])]
        self.asks = np.vstack((self.asks, asks[asks[:, 1] != 0]))
        self.sort_asks()
        if self.timestamp < timestamp:
            self.timestamp = timestamp

    def update_full(self, asks: NDArray, bids: NDArray) -> None:
        """
        Updates the order book with new ask and bid data.

        Parameters
        ----------
        asks : Array
            New ask orders data, formatted as [[price, size], ...].

        bids : Array
            New bid orders data, formatted as [[price, size], ...].
        """

        self.update_asks(asks)
        self.update_bids(bids)
    
    @property
    def mid(self) -> float: # 81.3 ns ± 1.76 ns
        """
        Calculates the mid price of the order book based on the best bid and ask prices.

        Returns
        -------
        float
            The mid price, which is the average of the best bid and best ask prices.
        """
        return (self.bba[0, 0] + self.bba[1, 0]) / 2
    
    @property
    def wmid(self) -> float: # 91.4 ns ± 4.25 ns
        """
        Calculates the weighted mid price of the order book, considering the volume imbalance
        between the best bid and best ask.

        Returns
        -------
        float
            The weighted mid price, which accounts for the volume imbalance at the top of the book.
        """
        imb = self.bba[0, 1] / (self.bba[0, 1] + self.bba[1, 1])
        return self.bba[0, 0] * imb + self.bba[1, 0] * (1 - imb)
    
    def get_vamp(self, depth: float) -> float: # 699 ns ± 15.1 ns
        """
        Calculates the volume-weighted average market price (VAMP) up to a specified depth for both bids and asks.

        Parameters
        ----------
        depth : float
            The depth (in terms of volume) up to which the VAMP is calculated.

        Returns
        -------
        float
            The VAMP, representing an average price weighted by order sizes up to the specified depth.
        """
        bid_size_weighted_sum = 0.0
        ask_size_weighted_sum = 0.0
        bid_cum_size = 0.0
        ask_cum_size = 0.0

        # Calculate size-weighted sum for bids
        for price, size in self.bids[:,0:2]:
            if bid_cum_size + size > depth:
                remaining_size = depth - bid_cum_size
                bid_size_weighted_sum += price * remaining_size
                bid_cum_size += remaining_size
                break

            bid_size_weighted_sum += price * size
            bid_cum_size += size

            if bid_cum_size >= depth:
                break

        # Calculate size-weighted sum for asks
        for price, size in self.asks[:,0:2]:
            if ask_cum_size + size > depth:
                remaining_size = depth - ask_cum_size
                ask_size_weighted_sum += price * remaining_size
                ask_cum_size += remaining_size
                break

            ask_size_weighted_sum += price * size
            ask_cum_size += size

            if ask_cum_size >= depth:
                break

        total_size = bid_cum_size + ask_cum_size

        if total_size == 0.0:
            return 0.0

        return (bid_size_weighted_sum + ask_size_weighted_sum) / total_size
    
    @property
    def spread(self) -> float: # 73.3 ns ± 2.06 ns
        """
        Calculates the current spread of the order book.

        Returns
        -------
        float
            The spread, defined as the difference between the best ask and the best bid prices.
        """
        return self.bba[1, 0] - self.bba[0, 0]
    
    def get_slippage(self, book: NDArray, size: float) -> float:
        """
        Calculates the slippage cost for a hypothetical order of a given size, based on either the bid or ask side of the book.

        Parameters
        ----------
        book : Array
            The order book data for the side (bids or asks) being considered.

        size : float
            The size of the hypothetical order for which slippage is being calculated.

        Returns
        -------
        float
            The slippage cost, defined as the volume-weighted average deviation from the mid price for the given order size.
        """
        mid = self.mid
        cum_size = 0.0
        slippage = 0.0

        for level in range(book.shape[0]):
            cum_size += book[level, 1]
            slippage += np.abs(mid - book[level, 0]) * book[level, 1]

            if cum_size >= size:
                slippage /= cum_size
                break

        return slippage if slippage <= mid else mid

    def display(self, levels: int) -> None:
        """
        Displays the top X bid/ask levels of the order book.
        """
        levels = self.depth if self.depth < levels else levels
        first_asks = self.asks[::-1][:levels]
        first_bids = self.bids[:levels]

        ask_str = "Asks: |" + "\n      |".join(
            [
                f"Price: {nb_float_to_str(price)}, Size: {nb_float_to_str(size)}"
                for price, size in zip(first_asks[:, 0], first_asks[:, 1])
            ]
        )

        bid_str = "Bids: |" + "\n      |".join(
            [
                f"Price: {nb_float_to_str(price)}, Size: {nb_float_to_str(size)}"
                for price, size in zip(first_bids[:, 0], first_bids[:, 1])
            ]
        )

        return print(f"{ask_str}\n{'-' * 40}\n{bid_str}")
    

