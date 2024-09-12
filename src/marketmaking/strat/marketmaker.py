import asyncio
import numpy as np

from src.marketmaking.sharedstate import MMSharedState
from src.marketmaking.quote_generators.base import QuoteGenerator
from src.marketmaking.oms.oms import OrderManagementSystem
# from src.marketmaking.features.features import FeatureEngine
from src.tools.log import LoggerInstance
import traceback

class TradingLogic:
    def __init__(self, ss: MMSharedState, logging: LoggerInstance) -> None:
        self.ss = ss
        self.logging = logging
        self.logging.setFilters("LOGIC")
        self.logging.setHandlers()
        
        # self.feature_engine = FeatureEngine(self.ss)
        self.oms = dict()
        self.trading_exchanges = []
        
        for exchange_name in self.ss.exchanges.keys():
            if self.ss.exchanges[exchange_name]["type"] == "trading":
                self.trading_exchanges.append(exchange_name)
                self.oms[exchange_name] = OrderManagementSystem(self.ss,exchange_name=exchange_name)
                self.oms[exchange_name].load_required_refs(self.logging.createChild(child_name=f"{exchange_name.upper()}.OMS", debug_mode=self.ss.debug))
 
    def load_quote_generator(self) -> QuoteGenerator:
        quote_gen_name = self.ss.quote_generator.lower()
        self.logging.info(f"Attempting to load quote generator: {quote_gen_name}")
        
        match quote_gen_name:
            case "plain":
                from src.marketmaking.quote_generators.plain import PlainQuoteGenerator
                return PlainQuoteGenerator(self.ss)

            case "stinky":
                from src.marketmaking.quote_generators.stinky import StinkyQuoteGenerator
                return StinkyQuoteGenerator(self.ss)
            
            case "sandbox":
                from src.marketmaking.quote_generators.sandbox import SandBoxQuoteGenerator
                return SandBoxQuoteGenerator(self.ss, "hyperliquid", self.logging.createChild(child_name="HYPERLIQUID.QUOTE_GEN", debug_mode=self.ss.debug))

            case _:
                raise ValueError(f"Invalid quote generator: {quote_gen_name}")

    async def wait_for_ws_warmup(self) -> None:
        """
        Waits for confirmation that the WebSocket connections are
        established and data is filling the arrays.
        """
        ready = False
        while not ready:
            
            await asyncio.sleep(1.0)
            ready = True
            
            for exchange in self.ss.exchanges.keys():
                if len(self.ss.data[exchange]["trades"]) < 29:
                    ready = False
                    break
    
                if len(self.ss.data[exchange]["ohlcv"]) < 100:
                    ready = False
                    break
                    
                if all(value == 0.0 for value in self.ss.data[exchange]["ticker"].values()):
                    ready = False
                    break
    
                if np.all(self.ss.data[exchange]["orderbook"].bids[:, 0] == 0.0) or np.all(self.ss.data[exchange]["orderbook"].asks[:, 0] == 0.0):
                    ready = False
                    break
    
                if (self.ss.data[exchange]["tick_size"], self.ss.data[exchange]["lot_size"]) == (0.0, 0.0):
                    ready = False
                    break
            
            continue
        
        self.logging.info("Feeds successfully warmed up.")
        return None

    async def start_loop(self) -> None:
        try:
            self.logging.info("Warming up data feeds...")
            await self.wait_for_ws_warmup()
            self.quote_generator = self.load_quote_generator()
            self.logging.info(
                f"Starting '{self.ss.quote_generator.lower()}' strategy on {self.ss.data[self.trading_exchanges[0]]['symbol']}..."
            )
            for trading_exch in self.trading_exchanges: 
                flags = ["to_create", 
                          "to_amend", 
                         "to_cancel"
                         ]
                
                asyncio.create_task(self.oms[trading_exch].monitor(flags))
                self.logging.info(f"monitor task started for {trading_exch}")
                asyncio.create_task(self.quote_generator.position_executor())
                self.logging.info(f"position executor task started for {trading_exch}")
                await asyncio.sleep(0)
                
            while True:
                # fp_skew = self.feature_engine.generate_skew()
                # vol = self.feature_engine.generate_vol()
                
                #TODO ADAPT QUOTE GENERATOR FOR MULTIPLE EXCHANGES
                new_orders = self.quote_generator.generate_orders()
                for trading_exch in self.trading_exchanges:
                    await self.oms[trading_exch].update(new_orders)

                # self.logging.debug(topic="MM", msg=f"FP Skew: {fp_skew} - Vol: {vol} - NewOrders: {new_orders}")
                self.logging.debug(f"NewOrders: {new_orders}")
                await asyncio.sleep(self.quote_generator.params["generation_interval"]/1000)#interval in ms

        except Exception as e:
            self.logging.error(f"Main loop: {e}")
            self.logging.error(f"traceback: {traceback.print_tb(e.__traceback__)}")
            raise e
