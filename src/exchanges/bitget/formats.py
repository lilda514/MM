from typing import List, Dict

from src.tools.logging import time_ms
from src.exchanges.common.types import Order, OrderType
from src.exchanges.common.formats import Formats
from src.exchanges.bitget.types import BitgetSideConverter, BitgetOrderTypeConverter, BitgetTimeInForceConverter, BitgetPositionDirectionConverter, BitgetReduceOnlyConverter


class BitgetFormats(Formats):
    def __init__(self) -> None:
        super().__init__(
            convert_side = BitgetSideConverter(),
            convert_order_type = BitgetOrderTypeConverter(),
            convert_time_in_force = BitgetTimeInForceConverter(),
            convert_position_direction = BitgetPositionDirectionConverter()
        )
        self.convert_reduce_only = BitgetReduceOnlyConverter()
        self.base_kwarg = {"productType": "USDT-FUTURES"}

    def create_order(
        self,
        order
    ) -> Dict:
        params = []
        body = {
            **self.base_kwarg,
            "symbol": order.symbol,
            "marginMode": "isolated",
            "marginCoin": "USDT",
            "side": self.convert_side.to_str(order.side),
            "orderType": self.convert_order_type.to_str(order.orderType),
            "force": self.convert_tif.to_str(order.timeInForce),
            "size": str(order.size),
            **({"clientOid": order.clientOrderId} if order.clientOrderId else {}),
            "reduce_only": self.convert_reduce_only.to_str(order.reduceOnly)
        }

        match order.orderType:
            case OrderType.MARKET:
                pass
            case OrderType.LIMIT:
                body["price"] = str(order.price)
            case _:
                raise NotImplementedError(f"OrderType not implemented: {order.orderType}")
                
        return {"params": params, "body": body}
    
    def batch_create_orders(
        self,
        orders: List[Order]
    ) -> Dict:
        
        params = []
        batched_orders = []

        for order in orders:
            single_order = self.create_order(order)
            del single_order["body"]["symbol"]
            del single_order["body"]["marginMode"]
            batched_orders.append(single_order["body"])

        body = {
            **self.base_kwarg,
            "symbol": order.symbol,
            "marginMode":"isolated",
            "orderList": batched_orders,
        }
        return {"params":params ,"body": body}

    
    def amend_order(
        self,
        order
    ) -> Dict:
        
        params = []
        body = {
            **self.base_kwarg,
            **({"orderId": order.orderId} if order.orderId else {}),
            **({"clientOid": order.clientOrderId} if order.clientOrderId else {}),
            **({"newClientOid": order.clientOrderId} if order.clientOrderId else {}),
            "symbol": order.symbol,
            "side": self.convert_side.to_str(order.side),
            "quantity": str(order.size),
        }
        
        match order.orderType:
            case OrderType.MARKET:
                pass
            case OrderType.LIMIT:
                body["newPrice"] = str(order.price)
            case _:
                raise NotImplementedError(f"OrderType not implemented: {order.orderType}")
                
        return {"params":params,"body": body}


    # def batch_amend_orders(self, orders: List[Order]) -> Dict:
    #     batched_amends = []

    #     for order in orders:
    #         single_amend = self.amend_order(order)
    #         del single_amend["recvWindow"]
    #         del single_amend["timestamp"]
    #         batched_amends.append(order)
    
    #     return {
    #         "batchOrders": batched_amends,
    #         **self.base_payload,
    #         "timestamp": str(time_ms()),
    #     }
    
    def cancel_order(self, order) -> Dict:
        
        params = []
        body = {
            **self.base_kwarg,
            "symbol": order.symbol, 
            **({"orderId": order.orderId} if order.orderId else {}),
            **({"clientOid": order.clientOrderId} if order.clientOrderId else {}),
        }
        return {"params": params,"body": body}


    def batch_cancel_orders(self, orders: List[Order]) -> Dict:
        
        params = []
        body =  {
            "symbol": orders[0].symbol, # TODO: Find a better solution for this!
            "orderIdList": [{"orderId": order.orderId} for order in orders if order.orderId is not None],
            "origClientOrderIdList": [order.clientOrderId for order in orders if order.clientOrderId is not None],
            **self.base_kwarg,
        }
        return {"params": params, "body": body}

    
    def cancel_all_orders(self, symbol: str) -> Dict:
        body= {
            **self.base_kwarg,
            "symbol": symbol, 
        }
        return {"params":[],"body": body}


    def get_ohlcv(self, symbol, interval) -> Dict:
        
        # candle_no = 1000
        # now_ms = time_ms()
        # now_rounded_down = now_ms - now_ms % (3600*1000) #Now rounded down to the closest hour
        # one_min_to_ms = 60*1000
        # match interval:
        #     case "1m":
        #         time_delta = one_min_to_ms
        #     case "3m":
        #         time_delta = 3*one_min_to_ms
        #     case "5m":
        #         time_delta = 5*one_min_to_ms
        #     case "15m":
        #         time_delta = 15*one_min_to_ms
        #     case "30m":
        #         time_delta = 30*one_min_to_ms
        #     case "1h":
        #         time_delta = 60*one_min_to_ms
        #     case "2h":
        #         time_delta = 2*one_min_to_ms
        #     case "4h":
        #         time_delta = 4*60*one_min_to_ms
        #     case "6h":
        #         time_delta = 6*60*one_min_to_ms
                
        params =  {
            **self.base_kwarg,
            "symbol": symbol, 
            "granularity": interval, 
            "limit": "1000"}
        return {"params":[(key,params[key]) for key in sorted(params.keys())],"body":{}}


    def get_trades(self, symbol) -> Dict:
        params = {
            **self.base_kwarg,
            "symbol": symbol, 
            "limit": "1000"}
        return {"params":[(key,params[key]) for key in sorted(params.keys())],"body":{}}


    def get_orderbook(self, symbol) -> Dict:
        params = {
            **self.base_kwarg,
            "symbol":symbol,
            "limit": "100",
            "precision": "scale0"
            }
        return {"params":[(key,params[key]) for key in sorted(params.keys())],"body":{}}


    def get_ticker(self, symbol) -> Dict:
        params = {
            **self.base_kwarg,
            "symbol": symbol,
            }
        return {"params":[(key,params[key]) for key in sorted(params.keys())],"body":{}}


    def get_open_orders(self, symbol) -> Dict:
        params = {
            **self.base_kwarg,
            "symbol": symbol,
            }
        return {"params":[(key,params[key]) for key in sorted(params.keys())],"body":{}}


    def get_position(self, symbol) -> Dict:
        params = {
            **self.base_kwarg,
            "symbol":symbol,
            "marginCoin": "USDT"
            }
        return {"params":[(key,params[key]) for key in sorted(params.keys())],"body":{}}

    def get_account_info(self) -> Dict:
        params = self.base_kwarg
        return {"params":[(key,params[key]) for key in sorted(params.keys())],"body":{}}

    def get_exchange_info(self) -> Dict:
        params = self.base_kwarg
        return {"params":[(key,params[key]) for key in sorted(params.keys())],"body":{}}
    