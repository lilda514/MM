import asyncio
from typing import List, Dict, Union

from src.marketmaking.sharedstate import MMSharedState
from src.exchanges.common.types import OrderType, Side
from src.exchanges.common.types import Order
from src.tools.log import LoggerInstance
from src.tools.misc import time_ms
import traceback

class OrderManagementSystem:
    """
    Handles order management functionalities including creating, amending, and canceling orders.

    Attributes
    ----------
    ss : SmmSharedState
        Shared state object containing the necessary data and configurations.

    symbol : str
        Trading symbol for the orders.

    data : dict
        Shared data dictionary containing order and market data.

    exchange : Exchange
        Exchange interface to send orders to.

    prev_intended_orders : list
        List to keep track of previously intended state of orders.
    """
    def __init__(self, ss: MMSharedState, exchange_name: str) -> None:
        self.ss = ss
        self.params = ss.parameters[ss.quote_generator]
        self.exchange_name = exchange_name
        self.symbol = ss.exchanges[exchange_name]["symbol"]
        self.data = ss.data[exchange_name]
        self.exchange =  ss.exchanges[exchange_name]["exchange"]
        self.orderid = self.exchange.orderid
        self.prev_intended_orders: Dict[Order] = self.data["orders"]["in_flight"]
        
    def load_required_refs(self, logging: LoggerInstance ):
        self.logging = logging
        self.logging.setFilters(self.exchange_name.upper() + "." + "OMS")  
        self.logging.setHandlers()

    async def create_orders(self, new_orders: List[Order]) -> asyncio.Task:
        """
        Format a create order and send to exchange.

        Parameters
        ----------
        new_order : Order
            Dictionary containing order details.

        Returns
        -------
        asyncio.coro
            
        """
        if isinstance(new_orders, Order):
            new_orders = [new_orders]
            
        for new_order in new_orders:
            self.data["orders"]["in_flight"].update({new_order.clientOrderId.to_raw() : new_order})
            
            match new_order.orderType:
                case OrderType.STOP_LIMIT | OrderType.TAKE_PROFIT_LIMIT | OrderType.STOP_MARKET | OrderType.TAKE_PROFIT_MARKET: 
                    self.data["orders"]["to_be_triggered"].update({new_order.clientOrderId.to_raw() : new_order})

        return await self.exchange.batch_create_orders(new_orders)
    
    async def amend_orders(self, new_orders: List[Order]) -> asyncio.Task:
        """
        Format an amend order and send to exchange. The new order should have the same exchange assigned order id as the one 
        it is meant to amend

        Parameters
        ----------
        new_order : Order
            The new order.

        Returns
        -------
        asyncio.coro
            
        """
        if isinstance(new_orders, Order):
            new_orders = [new_orders]
            
        for new_order in new_orders:

            self.data["orders"]["in_flight"].update({new_order.clientOrderId.to_raw() : new_order})
            
            match new_order.orderType:
                case OrderType.STOP_LIMIT | OrderType.TAKE_PROFIT_LIMIT | OrderType.STOP_MARKET | OrderType.TAKE_PROFIT_MARKET: 
                    self.data["orders"]["to_be_triggered"].update({new_order.clientOrderId.to_raw() : new_order})
 
        return await self.exchange.batch_amend_orders(new_orders)
            
    async def cancel_orders(self, old_orders: List[Union[Order,int]]) -> asyncio.Task:
        """
        Format a cancel order and send to exchange.

        Parameters
        ----------
        old_order : Order
            The client order ID of the order to cancel.

        Returns
        -------
        asyncio.coro
            
        """
        if isinstance(old_orders, Order):
            old_orders = [old_orders]
        
        return await self.exchange.batch_cancel_orders(old_orders)
    
    async def cancel_all_orders(self) -> asyncio.Task:
        """
        Format a cancel order and send to exchange to cancel all orders.

        Returns
        -------
        asyncio.Task
            asyncio.Task for canceling all orders.
        """
        return await self.exchange.cancel_all_orders(
            symbol=self.symbol
        )
    
    def find_matched_order(self, new_order: Order) -> Order:
        """
        Attempt to find the order with a matching level number.

        Steps
        -----
        1. Extract the level number from the `clientOrderId` of the `new_order`.
        2. Iterate through the current orders in `self.data["orders"]`.
        3. Compare the level number of each current order with the `new_order` level number.
        4. Return the first matching order found, or an empty Order if no match is found.

        Parameters
        ----------
        new_order : Order
            The new order from the quote generator.  
        
        Returns
        -------
        Order
            The order with the closest price to the target price and matching side.
        """  
        new_order_level = self.orderid.match_level(new_order.clientOrderId)

        for current_order in self.data["orders"]["in_the_book"].values():
            # self.logging.debug(f"Matching against: {current_order}")
            if self.orderid.match_level(current_order.clientOrderId) == new_order_level:
                return current_order

        return None

    def is_out_of_bounds(self, old_order: Order, new_order: Order, sensitivity: float=0.2) -> bool:
        """
        Check if the old order's price is out of bounds compared to the new order's price.

        Steps
        -----
        1. Calculate the distance from the mid price using the old order's price.
        2. Determine the acceptable price range using the sensitivity factor.
        3. Check if the new order's price is within the acceptable range.
        4. Return True if the price is out of bounds, otherwise return False.

        Parameters
        ----------
        old_order : Order
            The old order.

        new_order : Order
            The new order.

        sensitivity : float, optional
            The sensitivity factor for determining out-of-bounds (default is 0.1 or 10%).

        Returns
        -------
        bool
            True if the old order's price is out of bounds, False otherwise.
        """
        distance_from_mid = abs(new_order.price - self.data["orderbook"].mid)
        buffer = distance_from_mid * sensitivity
        
        return abs(old_order.price - new_order.price) > buffer


    async def update(self, new_orders: List[Order]) -> None:
        """
        Update the order book with new orders, canceling and creating orders as necessary.

        This method processes new orders and updates the existing orders by:
        
        1. Creating new orders if there are no previously intended orders.
        2. Cancelling any duplicate orders that might be created due to network delay.
        3. Processing each new order based on its type (MARKET or LIMIT).
        4. Replacing out-of-bound orders with new orders when necessary.
        
        Steps:
        ------
        1. If we have orders in flight, compare new orders to it and cancel new ones where the in flight order is not out of bounds:
            a. Iterate over in flight orders.
            b. get the price level
            b. Create a task to send the order to the exchange.
        
        2. Handle duplicate orders caused by network delays:
            a. Check if the number of active orders exceeds the allowed total orders.
            b. Identify duplicate tags by checking the client order ID.
            c. Cancel the duplicate orders.
        
        3. Process each new order based on its type:
            a. If the order type is MARKET:
                i. Create a task to send the order to the exchange.
            
            b. If the order type is LIMIT:
                i. Find a matching old order by comparing the client order ID.
                ii. Check if the new order is out of bounds compared to the old order.
                iii. If out of bounds, cancel the old order and create a new order.
                iv. If not out of bounds, create the new order.
        
        Parameters
        ----------
        new_orders : List[Order]
            List of new orders to be processed.
        
        Returns
        -------
        None
        """
        # while True:
            
            #TODO await for a flag to be set ex: when fair value changes more than
            # percentage. For now we use time interval to generate new quotes
            # await asyncio.sleep(self.params["generation_interval"])
            
        try:
            to_create = []
            to_amend = []
            cancel_tasks = []
            
            for order_to_cancel in self.data["orders"]["to_cancel"].values():
                cancel_tasks.append(asyncio.create_task(self.cancel_orders(order_to_cancel)))
            
            for order in new_orders:
                skip_order=False
                # Step 1: Checking in flight orders for similar order in case of network delay
                if len(self.prev_intended_orders) != 0:
                    
                   for in_flight_order in self.prev_intended_orders.values():
                       
                       # if we have already sent this order but the exchange has not yet aknowledged it for less than 3 sec, we dont resend the order 
                       if order == in_flight_order or not self.is_out_of_bounds(in_flight_order, order) :
                           if (time_ms() - in_flight_order.timestamp) < 3*1000:
                               self.logging.info(f"Dropping {order} beacause similar order already on the way - {in_flight_order}")
                               skip_order = True
                               break

                           else:
                               self.logging.debug(f"considering order {in_flight_order.clientOrderId.to_raw()} dropped")
                               #If the order has been in flight for more than 3 sec, we consider it dropped and resend it 
                               del self.prev_intended_orders[in_flight_order.clientOrderId.to_raw()]
                               to_create.append(order)
                               skip_order = True
                               break
                       # else:
                       #     #If we have already sent an order of the same level, nothing to do but wait for it to be ackowledged by the exchange
                       #     if self.orderid.match_level(order.clientOrderId) == self.orderid.match_level(in_flight_order.clientOrderId):
                if skip_order:
                    continue
                                       
                           
                # Step 2
                match order.orderType:
                    case OrderType.MARKET: 
                        to_create.append(order)
                        self.logging.debug(f"Sending order: {order}")
                    
                    case OrderType.LIMIT:
                            
                            matched_old_order = self.find_matched_order(order)

                            if matched_old_order != None:
                                self.logging.debug(f"found a matching order : {matched_old_order}")
                                if self.is_out_of_bounds(matched_old_order, order):
                                    #Out of bounds orders are immediatly canceled, but creating new corresponding orders will be done in batch at the end of the loop to save on rate limit
                                    cancel_tasks.append(asyncio.create_task(self.cancel_orders(matched_old_order)))
                                    to_create.append(order)
                                    self.logging.debug(f"Replacing order: {order}")
                                    
                            else:
                                if len(self.data["orders"]["in_the_book"]) - len(self.data["orders"]["tp"]) < self.ss.parameters[self.ss.quote_generator]["total_orders"]:  
                                    if self.data["position"].entryPrice is not None:
                                        #Not posting new orders that would make us blow inventory $ limit
                                        if abs(self.data["position"].size*self.data["position"].entryPrice + order.side*order.size*order.price) < self.ss.parameters[self.ss.quote_generator]["max_position"]:
                                            to_create.append(order)
                                    else:
                                        to_create.append(order)

                                        
                                else:
                                    self.logging.debug(f"We entered the weird case for {order}")
                                    #Should never enter this case since we create orders per level and keep track. Every order should be matched to an old order 
                                    #except when starting up MM. Just in case, we start canceling orders from the closest to mid all the way out as to never exceed max allowed orders
                                    closest_order = sorted([
                                                            resting_order.clientOrderId for resting_order in self.data["orders"]["in_the_book"].values() 
                                                            if (resting_order.side == order.side and resting_order.orderType == OrderType().LIMIT)
                                                            ], 
                                                            reverse = True if order.side == Side.BUY else False)[0]
                                    self.logging.info("More resting orders than allowed, canceling {closest_order} and sending {order}")
                                    cancel_tasks.append(asyncio.create_task(self.cancel_orders(closest_order)))
                                    #TODO ADD LOGIC TO CREATE ORDER OR REMOVE LOGIC TO CANCEL AND ADD LOGIC TO AMEND
                                    
                                    
                    case _:
                        to_create.append(order)             
                        self.logging.debug(f"Sending order: {order}")
            
            self.logging.info(f"sending following orders: {to_create}")
            if to_create: 
                order_create_task =  [asyncio.create_task(self.create_orders(to_create))]
                tasks = cancel_tasks + order_create_task
            else:
                tasks = cancel_tasks
                
            if len(tasks) > 0:
                results = await asyncio.gather(*tasks,return_exceptions=True)
            
                for task_result in results:
                    self.logging.debug(f"{task_result}" )
                    if isinstance(task_result, dict):
                        for order_identification,result in task_result.items():
                            if result[0] == False:
                                self.logging.debug(f"There was a problem with order {order_identification} : {result}")
                                self.order_error(order_identification,result)

        except Exception as e:
            self.logging.error(msg=e)
            self.logging.error(f"traceback: {traceback.print_tb(e.__traceback__)}")

    async def update_simple(self, new_orders: List[Order]) -> None:
        """
        Simple update method to cancel all orders and create new ones.

        Parameters
        ----------
        new_orders : List[Order]
            List of new orders to be processed.
        """
        try:
            await asyncio.gather(*[
                self.cancel_all_orders(), 
                *[self.create_orders(order) for order in new_orders]
            ])

        except Exception as e:
            self.logging.error(e)
    
    async def monitor(self,flags: List[str]) -> None:
        """
        Monitors the cancel, create and amend queues via flags. Gets awaken by an asyncio event and
        once action is completed sets itself back to sleep.
        
        Parameters
        ----------
        flags : List[str]
            List of flag names to be monitored. Flags will be fetched from SharedState.data
        """
        
        pending = [asyncio.create_task(self.data["flags"][flag_name].wait(),name=flag_name) for flag_name in flags]

        while True:
            try:
                
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

                
                # Extract the single completed task
                self.logging.debug(f"the following task has completed : {done}")
                completed_task = done.pop().get_name() # There will be only one item in 'done'
                
                match completed_task :
                    case "to_create":
                        self.logging.debug("CREATE monitor has been awoken")
                        task = asyncio.create_task(self.create_orders(self.data["orders"]["to_create"].values()))
                        
                    case "to_amend":
                        self.logging.debug("AMEND monitor has been awoken")
                        task = asyncio.create_task(self.amend_orders(self.data["orders"]["to_amend"].values()))
                    
                    case "to_cancel":
                        self.logging.debug("CANCEL monitor has been awoken")
                        task = asyncio.create_task(self.cancel_orders(self.data["orders"]["to_cancel"].values()))
                        
                
                
                results = await task
                self.logging.debug(f"{completed_task} task result: {results}")
                for order_identification, result_tuple in results.items():
                        if result_tuple[0] == False:
                            self.logging.debug(f"There was a problem with order {order_identification} : {result_tuple}")
                            self.order_error(order_identification,result_tuple)
                        
                self.data["flags"][completed_task].clear()
                pending.add(asyncio.create_task(self.data["flags"][completed_task].wait(),name=completed_task))
                self.logging.debug(f"Now that the task is executed, the state of pending is : {pending}")
                
            except Exception as e:
                self.logging.error(msg=e)
                self.logging.error(f"traceback: {traceback.print_tb(e.__traceback__)}")
        

    def order_error(self,order_identification,result) -> None:
        
        #We might want to do different things depending on where the problematic order was. For
        #now we simply delete it from there
        
        if order_identification in self.data["orders"]["to_create"]:
            self.logging.info(f"error with order {self.data['orders']['to_create'][order_identification]}: {result}")
            del self.data["orders"]["to_create"][order_identification]
            
        elif order_identification in self.data["orders"]["to_amend"]:
            self.logging.info(f"error with order {self.data['orders']['to_amend'][order_identification]}: {result}")
            del self.data["orders"]["to_amend"][order_identification]
            
        elif order_identification in self.data["orders"]["to_cancel"]:
            self.logging.info(f"error with order {self.data['orders']['to_cancel'][order_identification]}: {result}")
            del self.data["orders"]["to_cancel"][order_identification]
        
        if order_identification in self.data["orders"]["tp"]:
            self.logging.info(f"error with order {self.data['orders']['tp'][order_identification]}: {result}")
            del self.data["orders"]["tp"][order_identification]
            
        elif order_identification in self.data["orders"]["sl"]:
            self.logging.info(f"error with order {self.data['orders']['sl'][order_identification]}: {result}")
            del self.data["orders"]["sl"][order_identification]
        
        if order_identification in self.data["orders"]["in_flight"]:
            self.logging.info(f"error with order {self.data['orders']['in_flight'][order_identification]}: {result}")
            del self.data["orders"]["in_flight"][order_identification]
            
            
        elif order_identification in self.data["orders"]["in_the_book"]:
            #Do nothing since the exchange knows about this order and will most likely send out orderupdates or userfills about it
            #It will mess up the websocket handlers if we delete it now.
            pass 
        
