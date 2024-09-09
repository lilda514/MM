import numpy as np
from typing import List, Dict
from numpy_ringbuffer import RingBuffer
from abc import ABC, abstractmethod
from typing import Dict, List, Union


class HlCandleHandler():
    
    def __init__(self, candles: RingBuffer) -> None:
        """
        Initializes the OhlcvHandler class with an OHLCV RingBuffer.
    
        Parameters
        ----------
        ohlcv : RingBuffer
            A RingBuffer instance to store OHL CV data.
        """
        self.ohlcv = candles
        self.format = np.array(
            [   0.0,  # Open Timestamp
                0.0,  # Close Timestamp
                0.0,  # Open
                0.0,  # High
                0.0,  # Low
                0.0,  # Close
                0.0,  # Volume
                0.0,  # No. of trades
            ])
    
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the OHLCV data with new data.

        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the OHLCV data.

        Steps
        -----
        1. Extract the OHLCV list from the recv payload.
           -> Ensure the following data points are present:
                - Timestamp
                - Open
                - High
                - Low
                - Close
                - Volume
        2. Overwrite the self.format array with the correct values
           and call 'self.ohlcv.append(self.format.copy())'.
           -> Remember to call this for each candle in the OHLCV list.
        """
        for candle in recv:
            self.format[:] = np.array(
                [
                    float(candle["t"]),
                    float(candle["T"]),
                    float(candle["o"]),
                    float(candle["h"]),
                    float(candle["l"]),
                    float(candle["c"]),
                    float(candle["v"]),
                    float(candle["n"])
                ])
            self.ohlcv.append(self.format.copy())
        
        
    def process(self, recv: Dict) -> None:
        """
        Processes incoming OHLCV data to update the RingBuffer.
    
        Parameters
        ----------
        recv : Dict
            The received payload containing the OHLCV data.
    
        Steps
        -----
        1. Extract the OHLCV list from the recv payload.
           -> Ensure the following data points are present:
                - Timestamp
                - Open
                - High
                - Low
                - Close
                - Volume
        2. Overwrite the self.format array with the correct values.
        3. If the candle is new (not an update), call 'self.ohlcv.append(self.format.copy())'.
           -> Remember to check that the candle is not new before appending!
        """
        candle = recv["data"]
        ts = float(candle["t"])
        new = ts > self.format[0] 
        
        self.format[:] = np.array(
            [
                ts,
                float(candle["T"]),
                float(candle["o"]),
                float(candle["h"]),
                float(candle["l"]),
                float(candle["c"]),
                float(candle["v"]),
                float(candle["n"])
            ])

        if not new:
            self.ohlcv.pop()

        self.ohlcv.append(self.format.copy())
    
        