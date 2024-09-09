# -*- coding: utf-8 -*-
"""
Created on Sun May 19 11:36:17 2024

@author: dalil
"""
import json
import logging
import threading
import time

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.signing import get_timestamp_ms
from hyperliquid.utils.types import *
import example_utils
from ws_stream.websocket import HlWebsocket
import time
from src.exchanges.common.localorderbook import BaseOrderbook
from src.exchanges.hyperliquid.ws_stream.handlers.orderbook import HlOrderBookHandler
from src.tools.rounding import *
from hyperliquid.utils.signing import (OrderRequest,ModifyRequest)



# How far from the best bid and offer this strategy ideally places orders. Currently set to .3%
# i.e. if the best bid is $1000, this strategy will place a resting bid at $997
DEPTH = 0.003

# How far from the target price a resting order can deviate before the strategy will cancel and replace it.
# i.e. using the same example as above of a best bid of $1000 and targeted depth of .3%. The ideal distance is $3, so
# bids within $3 * 0.5 = $1.5 will not be cancelled. So any bids > $998.5 or < $995.5 will be cancelled and replaced.
ALLOWABLE_DEVIATION = 0.5

# The maximum absolute position value the strategy can accumulate in units of the coin.
# i.e. the strategy will place orders such that it can long up to 1 ETH or short up to 1 ETH
MAX_POSITION = 1.0

# The coin to add liquidity on
COIN = "ETH"

InFlightOrder = TypedDict("InFlightOrder", {"type": Literal["in_flight_order"], "time": int})
Resting = TypedDict("Resting", {"type": Literal["resting"], "px": float, "oid": int})
Cancelled = TypedDict("Cancelled", {"type": Literal["cancelled"]})
ProvideState = Union[InFlightOrder, Resting, Cancelled]


def side_to_int(side: Side) -> int:
    return 1 if side == "A" else -1


def side_to_uint(side: Side) -> int:
    return 1 if side == "A" else 0


class BasicAdder:
    def __init__(self, address: str, info: Info, exchange: Exchange):
        self.info = info
        self.exchange = exchange
        subscription: L2BookSubscription = {"type": "l2Book", "coin": COIN}
        self.info.subscribe(subscription, self.on_book_update)
        self.info.subscribe({"type": "userEvents", "user": address}, self.on_user_events)
        self.position: Optional[float] = None
        self.provide_state: Dict[Side, ProvideState] = {
            "A": {"type": "cancelled"},
            "B": {"type": "cancelled"},
        }
        self.recently_cancelled_oid_to_time: Dict[int, int] = {}
        # self.poller = threading.Thread(target=self.poll)
        # self.poller.start()

    def on_book_update(self, book_msg: L2BookMsg) -> None:
        logging.debug(f"book_msg {book_msg}")
        book_data = book_msg["data"]
        if book_data["coin"] != COIN:
            print("Unexpected book message, skipping")
            return
        for side in SIDES:
            book_price = float(book_data["levels"][side_to_uint(side)][0]["px"])
            ideal_distance = book_price * DEPTH
            ideal_price = book_price + (ideal_distance * (side_to_int(side)))
            logging.debug(
                f"on_book_update book_price:{book_price} ideal_distance:{ideal_distance} ideal_price:{ideal_price}"
            )

            # If a resting order exists, maybe cancel it
            provide_state = self.provide_state[side]
            if provide_state["type"] == "resting":
                distance = abs(ideal_price - provide_state["px"])
                if distance > ALLOWABLE_DEVIATION * ideal_distance:
                    oid = provide_state["oid"]
                    print(
                        f"cancelling order due to deviation oid:{oid} side:{side} ideal_price:{ideal_price} px:{provide_state['px']}"
                    )
                    response = self.exchange.cancel(COIN, oid)
                    if response["status"] == "ok":
                        self.recently_cancelled_oid_to_time[oid] = get_timestamp_ms()
                        self.provide_state[side] = {"type": "cancelled"}
                    else:
                        print(f"Failed to cancel order {provide_state} {side}", response)
            elif provide_state["type"] == "in_flight_order":
                if get_timestamp_ms() - provide_state["time"] > 10000:
                    print("Order is still in flight after 10s treating as cancelled", provide_state)
                    self.provide_state[side] = {"type": "cancelled"}

            # If we aren't providing, maybe place a new order
            provide_state = self.provide_state[side]
            if provide_state["type"] == "cancelled":
                if self.position is None:
                    logging.debug("Not placing an order because waiting for next position refresh")
                    continue
                sz = MAX_POSITION + self.position * (side_to_int(side))
                if sz * ideal_price < 10:
                    logging.debug("Not placing an order because at position limit")
                    continue
                px = float(f"{ideal_price:.5g}")  # prices should have at most 5 significant digits
                print(f"placing order sz:{sz} px:{px} side:{side}")
                self.provide_state[side] = {"type": "in_flight_order", "time": get_timestamp_ms()}
                response = self.exchange.order(COIN, side == "B", sz, px, {"limit": {"tif": "Alo"}})
                print("placed order", response)
                if response["status"] == "ok":
                    status = response["response"]["data"]["statuses"][0]
                    if "resting" in status:
                        self.provide_state[side] = {"type": "resting", "px": px, "oid": status["resting"]["oid"]}
                    else:
                        print("Unexpected response from placing order. Setting position to None.", response)
                        self.provide_state[side] = {"type": "cancelled"}
                        self.position = None

    def on_user_events(self, user_events: UserEventsMsg) -> None:
        print(user_events)
        user_events_data = user_events["data"]
        if "fills" in user_events_data:
            with open("fills", "a+") as f:
                f.write(json.dumps(user_events_data["fills"]))
                f.write("\n")
        # Set the position to None so that we don't place more orders without knowing our position
        # You might want to also update provide_state to account for the fill. This could help avoid sending an
        # unneeded cancel or failing to send a new order to replace the filled order, but we skipped this logic
        # to make the example simpler
        self.position = None        

    def poll(self):
        while True:
            open_orders = self.info.open_orders(self.exchange.wallet.address)
            print("open_orders", open_orders)
            ok_oids = set(self.recently_cancelled_oid_to_time.keys())
            for provide_state in self.provide_state.values():
                if provide_state["type"] == "resting":
                    ok_oids.add(provide_state["oid"])

            for open_order in open_orders:
                if open_order["coin"] == COIN and open_order["oid"] not in ok_oids:
                    print("Cancelling unknown oid", open_order["oid"])
                    self.exchange.cancel(open_order["coin"], open_order["oid"])

            current_time = get_timestamp_ms()
            self.recently_cancelled_oid_to_time = {
                oid: timestamp
                for (oid, timestamp) in self.recently_cancelled_oid_to_time.items()
                if current_time - timestamp > 30000
            }

            user_state = self.info.user_state(self.exchange.wallet.address)
            for position in user_state["assetPositions"]:
                if position["position"]["coin"] == COIN:
                    self.position = float(position["position"]["szi"])
                    print(f"set position to {self.position}")
                    break
            if self.position is None:
                self.position = 0.0
            time.sleep(10)

def make_book(exchange:Exchange,ws:HlWebsocket,coin:str):
    
    user_state = ws.info.user_state(exchange.account_address)
    available_margin = float(user_state["marginSummary"]["accountValue"]) - float(user_state["marginSummary"]["totalMarginUsed"]) 
    book = BaseOrderbook(10)
    obhandler = HlOrderBookHandler(book)
    meta = ws.info.meta()

    for asset in meta["universe"]:
        if asset["name"] == coin:
            sz_dec = asset["szDecimals"]
            max_leverage = asset["maxLeverage"]
            only_isolated = asset["onlyIsolated"]
            break
    
    px_max_dec_perp = 6
    px_sig_fig = 5
    exchange.update_leverage(int(max_leverage/1), coin,is_cross = False )
    global size_step_size 
    size_step_size = 10**-sz_dec
    
    fees_info = ws.info.user_fees(exchange.account_address)
    maker_fee = float(fees_info["userAddRate"])
    taker_fee = float(fees_info["userCrossRate"])
    
    break_even_spread_ratio = 2*maker_fee
    
    formatted_snapshot = dict()
    raw_snapshot = ws.info.l2_snapshot(coin)
    formatted_snapshot["data"] = raw_snapshot
    obhandler.refresh(formatted_snapshot)
    mid = book.mid  
    break_even_spread = break_even_spread_ratio*mid
    
    spread_diff = book.spread - break_even_spread
    spread = break_even_spread + spread_diff if spread_diff > 0.0000001 else break_even_spread
    
    trig_px = hl_round_floor(mid,5,6)
    bid_px = hl_round_floor(mid - 0.5*spread,5,6)
    bid_sz = round_discrete( max_leverage*available_margin/mid ,size_step_size)
    
    # trig_px_ask = hl_round_floor(mid,5,6)
    ask_px = hl_round_ceil(mid + 0.5*spread,5,6)
    ask_sz = round_discrete( max_leverage*available_margin/mid ,size_step_size)
    
    limit_type = {"limit": {"tif":"Gtc"}}
    trig_type =  {"trigger":{"isMarket":False,"triggerPx":trig_px,"tpsl":"sl"}}    
    bid = cast(OrderRequest, {"coin": coin,
                              "is_buy": True,
                              "sz": bid_sz,
                              "limit_px": bid_px,
                              "order_type": limit_type,
                              "reduce_only": False,
                              "cloid": Cloid.from_int(5)})
               
    ask = cast(OrderRequest, {"coin": coin,
                              "is_buy": False,
                              "sz": ask_sz,
                              "limit_px": ask_px,
                              "order_type": limit_type,
                              "reduce_only": False,
                              "cloid": Cloid.from_int(6)})
    
    order_list = [bid,ask]
    print(order_list)
    # order_list = [bid]

    
    #sending_orders
    return exchange.bulk_orders(order_list)
    
    # return exchange.market_open(coin, True, bid_sz)

def widen_open_orders(exchange:Exchange,ws:HlWebsocket,coin:str):
    open_orders = ws.info.open_orders(exchange.account_address)
    
    modified_orders = [{"oid": order["oid"],
                        "order": {
                                    "coin": order["coin"],
                                    "is_buy": True if order["side"] == "B" else False ,
                                    "sz": round_discrete(float(order["sz"])*1.5,size_step_size),
                                    "limit_px": hl_round_floor(float(order["limitPx"])-0.5*float(order["limitPx"]),5,6) if order["side"] == "B" else hl_round_ceil(float(order["limitPx"])+0.5*float(order["limitPx"]),5,6),
                                    "order_type": {"limit":{"tif":"Gtc"}},
                                    "reduce_only": False,
                                    "cloid": Cloid.from_str(order["cloid"]) if "cloid" in order and order["cloid"] is not None else None,}
                                  } for order in open_orders if order["coin"] == coin]
    
    return exchange.bulk_modify_orders_new(modified_orders)
        
    
def main():
    # Setting this to logging.DEBUG can be helpful for debugging websocket callback issues
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(thread)d - %(module)s - %(message)s')
    try:
        hlws = HlWebsocket(constants.TESTNET_API_URL)
        address, exchange = example_utils.setup(constants.TESTNET_API_URL,info = hlws.info )
        coin = "WLD"
        # adder = BasicAdder(address, info, exchange)
        # subscriptions = hlData.subscription_request(['l2Book','trades','user','candle','allMids','orderUpdates','userFills'],coin='NOT',address=str(address),interval='1m')
        subscriptions = hlws.generate_subscription_request(['trades','user','orderUpdates','userFills','userHistoricalOrders'],coin=coin,address=str(address),interval='1m')
    
        for sub in subscriptions:
            hlws.info.subscribe(sub[0],sub[1])
        
        # time.sleep(30)
        resp_ord = make_book(exchange,hlws,coin)
        # resp_mod = widen_open_orders(exchange,hlws, "WLD")
    finally:
        hlws.info.disconnect()
        hlws.close_logs()
    
if __name__ == "__main__":
    main()