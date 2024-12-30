import numpy as np
from typing import Dict

from src.exchanges.common.ws_handlers.orderbook import OrderbookHandler


class BinanceOrderbookHandler(OrderbookHandler):
    def __init__(self, data: Dict) -> None:
        self.data = data
        super().__init__(self.data["orderbook"])
        # self.update_id = 0

    def refresh(self, recv: Dict) -> None:
        try:
            # self.update_id = int(recv["lastUpdateId"])
            bids = np.array(recv["bids"], dtype=np.float64)
            asks = np.array(recv["asks"], dtype=np.float64)
            timestamp = float(recv["ts"])

            self.orderbook.refresh(asks, bids, timestamp)

        except Exception as e:
            raise Exception(f"Orderbook Refresh :: {e}")

    def process(self, recv: Dict) -> None:
        try:
            # new_update_id = int(recv["u"])
            timestamp = float(recv["ts"])
            # if new_update_id > self.update_id:
            #     self.update_id = new_update_id

            if len(recv.get("bids", [])) > 0:
                bids = np.array(recv["bids"], dtype=np.float64)
                self.orderbook.update_bids(bids,timestamp)

            if len(recv.get("asks", [])) > 0:
                asks = np.array(recv["bids"], dtype=np.float64)
                self.orderbook.update_asks(asks,timestamp)

        except Exception as e:
            raise Exception(f"Orderbook Process :: {e}")
