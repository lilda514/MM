import numpy as np
from typing import List, Dict

from src.exchanges.common.ws_handlers.ohlcv import OhlcvHandler


class BinanceOhlcvHandler(OhlcvHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["ohlcv"])

    def refresh(self, recv: List[List]) -> None:
        try:
            self.clear_ohlcv_ringbuffer()
            for candle in recv:
                self.format[:] = np.array(
                    [
                        float(candle[0]),
                        float(candle[1]),
                        float(candle[2]),
                        float(candle[3]),
                        float(candle[4]),
                        float(candle[5]),
                    ],
                    dtype=np.float64,
                )
                self.ohlcv.append(self.format.copy())

        except Exception as e:
            raise Exception(f"[OHLCV refresh] {e}")

    def process(self, recv: Dict) -> None:
        try:
            candle = recv["data"]
            ts = float(candle[0])
            new = True if ts > self.format[0] else False

            self.format[:] = np.array(
                [
                    ts,
                    float(candle[1]),#Open
                    float(candle[2]),#High
                    float(candle[3]),#Low
                    float(candle[4]),#Close
                    float(candle[5])#Volume
                ],
                dtype=np.float64,
            )

            if not new:
                self.ohlcv.pop()

            self.ohlcv.append(self.format.copy())

        except Exception as e:
            raise Exception(f"[OHLCV process] {e}")
