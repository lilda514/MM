from typing import List, Union
import traceback

from src.tools.misc import time_ms
from src.tools.Numbas import nbgeomspace
from src.tools.weights import generate_geometric_weights
from src.marketmaking.sharedstate import MMSharedState
from src.tools.log import LoggerInstance
from src.tools.rounding import hl_round_floor, hl_round_ceil, round_discrete
from src.marketmaking.quote_generators.base import (
    QuoteGenerator, 
    Side, 
    TimeInForce, 
    OrderType, 
    Order,
    Position
)


class SandBoxQuoteGenerator(QuoteGenerator):
    """
    This strategy's breakdown can be found in [smm/quote_generators/README.md]
    """
    def __init__(self, ss: MMSharedState, exchange_name: str, logging:LoggerInstance) -> None:
        super().__init__(ss,exchange_name)
        
        self.position: Position = ss.data[exchange_name]["position"]
        self.generated_tp = ss.data[exchange_name]["orders"]["tp"]
        self.generated_sl = ss.data[exchange_name]["orders"]["sl"]
        self.logging = logging
        self.logging.setFilters(exchange_name.upper() + "." + "QUOTE_GEN")  
        self.logging.setHandlers()
        
    def generate_stinky_orders(self) -> List[Order]:
        """
        Generate deep orders in a range from the base spread to base^1.5 away from mid.

        Steps
        -----
        1. Convert the base spread from basis points to a decimal.
        2. Generate geometric sequences for spreads and sizes:
            a. The spreads range from the base spread to the base spread raised to the power of 1.5.
            b. The sizes are generated using geometric weights.
        3. For each spread and size pair:
            a. Calculate the bid price by subtracting the spread from the mid-price.
            b. Calculate the ask price by adding the spread to the mid-price.
        4. Generate and append a bid order:
            a. Use the calculated bid price and size.
            b. Assign a client order ID with the level suffix.
        5. Generate and append an ask order:
            a. Use the calculated ask price and size.
            b. Assign a client order ID with the level suffix.

        Parameters
        ----------
        None

        Returns
        -------
        List[Order]
            A list of orders.
        """
        orders: List[Order] = []
        level = 0

        spreads = nbgeomspace(
            start = self.bps_to_decimal(self.params["minimum_spread"]),
            end = self.bps_to_decimal(self.params["minimum_spread"] ** 1.5),
            n = self.total_orders//2,
            reverse = False
        )
        
        #Check the case where we have a position open on this side already. We do not want to make a new order with the size provided from the quote generator since it would blow risk limit
        # Rather we want to modify the size of the order to have current_position + notional of new order < risk limit
        if  (self.position.size - 0.0) < 1e-6:
            if self.position.side == Side.BUY:
                remaining_bid = max(0,self.max_position - abs(self.position.size))
                bid_sizes = remaining_bid * generate_geometric_weights(num = self.total_orders//2, reverse = True)        
                ask_sizes = self.max_position * generate_geometric_weights(num = self.total_orders//2, reverse = True)
            else:
                remaining_ask = max(0,self.max_position - abs(self.position.size))
                bid_sizes = self.max_position * generate_geometric_weights(num = self.total_orders//2, reverse = True)
                ask_sizes = remaining_ask * generate_geometric_weights(num = self.total_orders//2, reverse = True)
        else:
            bid_sizes = ask_sizes = self.max_position * generate_geometric_weights(num = self.total_orders//2, reverse = True)


        
        #Creating quotes from outside in
        for spread, bid_size, ask_size, level in zip(spreads, bid_sizes, ask_sizes, range(1,(self.total_orders//2)+1)):
            
            bid_price = hl_round_floor(self.mid_price - (self.mid_price*spread) / 2, 5, 6)
            ask_price = hl_round_ceil( self.mid_price + (self.mid_price*spread) / 2, 5, 6)
            
            if bid_size > 0:
                orders.append(
                    self.generate_single_quote(
                        side = Side.BUY,
                        orderType = OrderType.LIMIT,
                        timeInForce = TimeInForce.POST_ONLY,
                        price = bid_price,
                        size = round_discrete(bid_size,self.data["lot_size"]),
                        clientOrderId = self.orderid.generate_order_id(level = level)
                    )
                )
            if ask_size > 0:

                orders.append(
                    self.generate_single_quote(
                        side = Side.SELL,
                        orderType = OrderType.LIMIT,
                        timeInForce= TimeInForce.POST_ONLY,
                        price = ask_price,
                        size = round_discrete(ask_size,self.data["lot_size"]),
                        clientOrderId = self.orderid.generate_order_id(level = -level)
                    )
                )

        return orders

    async def position_executor(self) -> List[Union[Order, None]]:
        """
        Manages the position in for this strategy

        This method checks waits for the position flag to be set by the  websocket position handler.
        Once we are filled, it places a take profit limit order. It also monitors the duration of the current position
        and generates a taker order to exit it +  cancels the take profit order 

        Steps
        -----
        1. Once the flag is set and a position is found, we generate a take profit order of the same size as the position a
           with price determined by parameters
        2. Check if the position has been open for more than a time limit determined by the parameters 
        3. If the position did not exceed time limit, create a new tp from the quote we just generated or amend any currently existing tp
        4. If it has, purge the position with a market order and delete previously generated take profit.
        5.Set the necessary flags (create or amend) and clear the position flag. It will be reraised by the position handler if needed 

        Parameters
        ----------

        Returns
        -------
        List[Union[Order, None]]
            A list containing either a single taker order, or an empty list if no order is generated.
        """
        while True:
            orders: List[Union[Order, None]] = []

            try:
                self.logging.debug("pos executor started waiting for position flag")
                await self.data["flags"]["position"].wait()
              
                # self.logging.debug(f"")
              
                #setting take_profit
                if abs(self.position.size - 0.0) > 1e-6:
                    closing_side = Side.SELL if self.position.size > 0.0 else Side.BUY
                    tp = self.bps_to_decimal(self.params["take_profit"])*self.position.entryPrice
                    is_previous_tp = len(self.generated_tp) > 0 #Wether there is already a tp intended
                    price = self.position.entryPrice + (tp if closing_side == Side.SELL else -tp)
                    if is_previous_tp:
                        # list(self.generated_tp.keys())[0]
                        active_previous_tp = [tp_order for tp_order in self.generated_tp.values() if tp_order in self.data["orders"]["in_the_book"].values()]
                        is_inactive_previous_tp = (len(self.generated_tp) - len(active_previous_tp)) > 0
                        
                        if len(active_previous_tp) > 1: 
                            self.logging.debug("More TP's than allowed in the book, keeping the newest and canceling the rest")
                            newest_timestamp = 0
                            for idx,order in enumerate(active_previous_tp):
                                if order.timestamp > newest_timestamp:
                                    newest_timestamp = order.timestamp
                                    newest_idx = idx
                            #we keep the most recent as the active previous tp and cancel the rest
                            old_tps = active_previous_tp
                            active_previous_tp = old_tps.pop(newest_idx)
                            self.data["orders"]["to_cancel"].update({order.clientOrderId.to_raw() : order for order in old_tps})
                            self.data["flags"]["to_cancel"].set()
                            
                        #If we have tp in the book and no tp waiting for exchange ackowledgement
                        elif len(active_previous_tp) > 0 and not is_inactive_previous_tp:
                            active_previous_tp = active_previous_tp[0]
                        else:
                            self.logging.debug("A previous tp has been generated but not yet acknowledge by the exchange")
                            #TODO: IMPLEMENT LOGIC TO VERIFY IF SOMETHING IS IN FLIGHT. IF IT IS FOR LESS THAN 10 SEC DONT GENERATE NEW TP BUT IF 
                            #MORE, CONSIDER IT LOST/DROPPED AND GENERATE NEW ONE
                            self.data["flags"]["position"].clear()
                            continue
                        
                    orders.append(
                        self.generate_single_quote(
                        side = closing_side,
                        orderType = OrderType.LIMIT,
                        timeInForce = TimeInForce.POST_ONLY,
                        price = hl_round_ceil(price) if closing_side == Side.SELL else hl_round_floor(price),
                        size = round_discrete(abs(self.position.size), self.data["lot_size"]),
                        clientOrderId = self.orderid.generate_order_id(level = 0),
                        orderId = active_previous_tp.orderId if is_previous_tp else None
                            )
                        )
                    
                    #If the executor generates the same order as the one already in the book dont send anything:
                    if is_previous_tp and  orders[0] == active_previous_tp:
                        self.logging.debug("Position executor generated the same tp as the one already in the book")
                        orders.clear()
                    
                    if time_ms() - self.position.openTime >= self.params["liquidation_timer"]:
                        self.logging.debug("Position executor has reached liquidation timer,generating market order")
                        #If we market close remove the tp's we just created that have not been sent from "orders" list
                        orders.clear()
                        
                        #Create a taker order
                        orders.append(self.generate_single_quote(
                                  side=Side.SELL if self.position.size > 0.0 else Side.BUY,    
                                  orderType=OrderType.MARKET,
                                  timeInForce= TimeInForce.FOK,
                                  price=0.0,
                                  size= round_discrete(abs(self.position.size), self.data["lot_size"]),
                                  reduceOnly= False, 
                                  clientOrderId=self.orderid.generate_order_id(level = 0),
                                  orderId = active_previous_tp.orderId if is_previous_tp else None
                                   )
                              )
                        # #If we market close our position, cancel all active tp's currently in the book
                        # if len(self.generated_tp) > 0 and previous_tp in self.data["orders"]["in_the_book"]:
                        #     self.data["orders"]["to_cancel"].update(self.generated_tp)
                        #     self.data["flags"]["to_cancel"].set()
                    
                if len(orders) > 0:
                    
                    if is_previous_tp : #If we already had a tp in the book we amend it otherwise we create a new one
                        if len(self.generated_tp) <= 2:
                            self.generated_tp.update({orders[0].clientOrderId.to_raw() : orders[0] })
                            self.logging.debug(f"Position executor will AMEND with orders : {orders}")
                            self.data["orders"]["to_amend"].update({order.clientOrderId.to_raw() : order for order in orders})
                            self.data["flags"]["to_amend"].set()
                        else:
                            self.logging.debug("Position executor still waiting on a previous order")
                            self.logging.debug(f"Cannot send order: {orders}")


                    else:
                        self.generated_tp.update({orders[0].clientOrderId.to_raw() : orders[0] })
                        self.logging.debug(f"Position executor will CREATE orders : {orders}")
                        self.data["orders"]["to_create"].update({order.clientOrderId.to_raw() : order for order in orders})
                        self.data["flags"]["to_create"].set()
                        

                self.data["flags"]["position"].clear()
                self.logging.debug(f"pos executor has cleared position flag")


            
            except Exception as e:
                self.logging.error(f"Main loop: {e}")
                self.logging.error(f"traceback: {traceback.print_tb(e.__traceback__)}")
                raise e
            
    def generate_orders(self, fp_skew: float = 0, vol: float = 0) -> List[Order]:
        return self.generate_stinky_orders()
