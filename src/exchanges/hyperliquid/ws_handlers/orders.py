# -*- coding: utf-8 -*-
from typing import Dict, List, Union
from src.exchanges.common.types import Order,OrderStatus
from src.exchanges.hyperliquid.orderid import Cloid
from src.tools.log import LoggerInstance
import traceback

class HlOrdersHandler():
    """
    For Hyperliquid, the order handler's does not manage partial fills since we only get a message once an order has been fully filled.
    Therefore, remaining size on open orders is handled by the position handler.
    """
    _overwrite_ = set(("open", "triggered"))
    _remove_ = set(("rejected", "filled", "canceled","marginCanceled"))

    def __init__(self, data: Dict, logging: LoggerInstance) -> None:
        """
        Initializes the OrdersHandler class with an orders dictionary.

        Parameters
        ----------
        orders : dict
            A dictionary to store orders data.
        """
        self.orders = data["orders"]
        self.symbol = data["symbol"]
        self.flags = data["flags"]
        # self.format = {
        #     "createTime": 0.0, 
        #     "side": 0.0, 
        #     "price": 0.0, 
        #     "size": 0.0, 
        #     "orderId": "", 
        #     "clientOrderId": "",
        #     "statusTime":0.0,
        #     "type": ""
        # }
        self.sides_dict = {'A':-1,'B':1} 
        self.DEFAULTNUM = -123456789
        self.logging = logging
        self.logging.setFilters("OrderHandler")
        self.logging.setHandlers()
    
    def refresh(self, recv: Union[Dict, List]) -> None:
        """
        Refreshes the orders data with new data.
    
        This method should be implemented by subclasses to process
        new orders data and update the orders dictionary.
    
        Parameters
        ----------
        recv : Union[Dict, List]
            The received payload containing the orders data.
    
        Steps
        -----
        1. Extract the orders list from the recv payload.
           -> Ensure the following data points are present:
                - createTime
                - side
                - price
                - size
                - orderId
                - clientOrderId
        2. For each order in the list:
           -> Overwrite self.format with the respective values.
           -> self.orders[OrderId] = self.format.copy().
        """
        try:
            self.logging.debug(f"data['orders'] state BEFORE Refresh: {self.orders}")

            for order in recv:
                if order["coin"] != self.symbol:
                    continue
                
                cloid = order.get("cloid")       
                if not cloid:
                    self.orders["to_cancel"].update(
                            #Creating a placeholder order with the info necessary to cancel it
                            {order["oid"]:
                                 Order(symbol = order["coin"],
                                  side = self.sides_dict.get(order['side'],self.DEFAULTNUM),
                                  orderId = order["oid"],
                                  size = float(order["sz"])
                                  )
                                 }   
                                )
                    self.flags["to_cancel"].set()
                    continue
                
                if cloid in self.orders["in_the_book"]:
                    corresponding_order = self.orders["in_the_book"][cloid]
                    
                    corresponding_order._side = self.sides_dict.get(order['side'],self.DEFAULTNUM)
                    corresponding_order._size = float(order["sz"])
                    corresponding_order._price = float(order["limitPx"])
                    
                elif cloid in self.orders["to_be_triggered"]:
                    corresponding_order = self.orders["to_be_triggered"][cloid]
                    
                    corresponding_order._side = self.sides_dict.get(order['side'],self.DEFAULTNUM)
                    corresponding_order._size = float(order["sz"])
                    corresponding_order._price = float(order["limitPx"])
                else:
                    self.orders["to_cancel"].update(
                            #Creating a placeholder order with the info necessary to cancel it
                            {order["order"]["oid"]:
                                 Order(symbol = order["order"]["coin"],
                                  side = self.sides_dict.get(order["order"]['side'],self.DEFAULTNUM),
                                  orderId = order["order"]["oid"],
                                  size = float(order["sz"])
                                  )
                                 }   
                                )
                    self.flags["to_cancel"].set()
                    continue
                
            self.logging.debug(f"data['orders'] state AFTER Refresh: {self.orders}")
        except Exception as e:
            self.logging.error(f"traceback: {traceback.print_tb(e.__traceback__)}")
            raise Exception(f"Orders refresh : {e}")

    
    
    
    def process(self, recv: Dict) -> None:
        """
        Processes incoming orders data to update the orders dictionary.
    
        This method should be implemented by subclasses to process
        incoming orders data and update the orders dictionary.
    
        Parameters
        ----------
        recv : Dict
            The received payload containing the orders data.
    
        Steps
        -----
        1. Extract the orders list from the recv payload.
           -> Ensure the following data points are present:
                - createTime
                - side
                - price
                - size
                - orderId
                - clientOrderId
        2. For each order in the payload:
           -> Overwrite self.format with the respective values.
           -> self.orders[OrderId] = self.format.copy().
        3. If any orders need to be deleted:
           -> del self.orders[OrderId].
        """
        try:
            
            #TODO: Set the appropriate events to be awaited on.
            
            #Every order should be sent to in_flight and stop orders that need to be triggered should also be sent to "to_be_triggered"
            self.logging.debug(f"data['orders'] state BEFORE Process: {self.orders}")
            for order in recv["data"]:
                if order["order"]["coin"] != self.symbol:
                    continue
                cloid = order["order"].get("cloid")
                
                #Every order we send should have a cloid, if not something wrong, cancel it
                if not cloid:
                    if order["status"] == "open":
                        self.orders["to_cancel"].update(
                                #Creating a placeholder order with the info necessary to cancel it
                                {order["order"]["oid"]:
                                     Order(symbol = order["order"]["coin"],
                                      side = self.sides_dict.get(order["order"]['side'],self.DEFAULTNUM),
                                      orderId = order["order"]["oid"],
                                      size = float(order["order"]["sz"])
                                      )
                                     }   
                                    )
                        self.flags["to_cancel"].set()
                        continue
                    elif order["status"] == "canceled":
                        del self.orders["to_cancel"][order["order"]["oid"]]
                        continue
                    #If it has no cloid but the status is filled, size left is 0 and is reduce only, it is a liquidation
                    #Nothing to do, the position handler will deal with it
                    elif order["status"] == "filled" and order["order"]["sz"] == "0.0" and order.get("reduceOnly",False) :
                        continue
                    
                    
                if cloid in self.orders["to_create"]:
                    del self.orders["to_create"][cloid]
                elif cloid in self.orders["to_amend"]: 
                    del self.orders["to_amend"][cloid]


                # Check if new open order was sent by us previously if not cancel it
                if order["status"] == "open" :
                    if not self.orders["in_flight"].get(cloid, False):
                        self.orders["to_cancel"].update(
                                #Creating a placeholder order with the info necessary to cancel it
                                {order["order"]["oid"]:
                                     Order(symbol = order["order"]["coin"],
                                      side = self.sides_dict.get(order["order"]['side'],self.DEFAULTNUM),
                                      orderId = order["order"]["oid"],
                                      size = float(order["order"]["sz"])
                                      )
                                     }   
                                    )
                        self.flags["to_cancel"].set()
                        continue
                    #The order was sent by us, the exchange has assigned it an oid, so we update the value in our order. 
                    #Only need to change it in one place since every dict references the same order objects
                    self.orders["in_flight"][cloid]._orderId = order["order"]["oid"]
                    self.orders["in_flight"][cloid]._timestamp = order["statusTimestamp"]
                    
                    #If the order is not in "to_be_triggered",it was not a stop order so it has hit the books
                    if cloid not in self.orders["to_be_triggered"]:
                        self.orders["in_the_book"][cloid] = self.orders["in_flight"][cloid]
                        self.orders["in_the_book"][cloid].changeStatus(OrderStatus.IN_THE_BOOK)
                        
                    #If it was a stop order it will only live in "to_be_triggered", while waiting for trigger.
                    del self.orders["in_flight"][cloid]
                
                elif order["status"] == "triggered":
                    self.orders["in_the_book"][cloid] = self.orders["to_be_triggered"][cloid]
                    self.orders["in_the_book"][cloid].changeStatus(OrderStatus.IN_THE_BOOK)
                    del self.orders["to_be_triggered"][cloid]

    
                elif order["status"] in self._remove_:
                    
                    if cloid in self.orders["tp"]:
                        del self.orders["tp"][cloid]
                    elif cloid in self.orders["sl"]:
                        del self.orders["sl"][cloid]  
                        
                    if cloid in self.orders["to_cancel"]:
                        del self.orders["to_cancel"][cloid]
                    
                    if order["status"] == "rejected": #If the order has been rejected it has never made it out of in_flight
                        if cloid in self.orders["in_flight"]:
                            self.orders["recently_cancelled"][cloid] = self.orders["in_flight"][cloid]
                            self.orders["recently_cancelled"][cloid].changeStatus(OrderStatus.RECENTLY_CANCELLED)
                            self.orders["recently_cancelled"][cloid]._timestamp = order["statusTimestamp"]
                            del self.orders["in_flight"][cloid]
                                
                    else:
                        
                        self.orders["recently_cancelled"][cloid] = self.orders["in_the_book"][cloid]
                        self.orders["recently_cancelled"][cloid].changeStatus(OrderStatus.RECENTLY_CANCELLED)
                        self.orders["recently_cancelled"][cloid]._timestamp = order["statusTimestamp"]

                        del self.orders["in_the_book"][cloid]
                        
            self.logging.debug(f"data['orders'] state AFTER Process: {self.orders}")
  
        except Exception as e:
            self.logging.error(f"traceback: {traceback.print_tb(e.__traceback__)}")
            raise Exception(f"Orders Process :: {e}")

