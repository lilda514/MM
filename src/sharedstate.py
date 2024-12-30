# -*- coding: utf-8 -*-
"""
Created on Sat May 25 22:05:55 2024

@author: dalil
"""

import asyncio
import os
import yaml
from numpy_ringbuffer import RingBuffer
from typing import Dict
from abc import ABC, abstractmethod
import numpy as np
import json
from getpass import getpass


from src.exchanges.common.localorderbook import BaseOrderbook
from src.exchanges.common.types import Position
from src.tools.log import LoggerInstance
from src.exchanges.credential_encoding import decrypt_config



class SharedState(ABC):
    """
    Centralizes shared data and configurations for the trading application, including market data
    and trading parameters, and provides utility methods for market metric calculations.

    Attributes
    ----------
    PARAM_DIR : str
        The directory path to the parameters file containing trading settings.

    Methods
    -------
    load_settings(settings: Dict) -> None:
        Updates trading parameters and settings from a given dictionary.
    load_initial_settings() -> None:
        Loads initial trading settings from the parameters file.
    """

    PARAM_PATH = os.path.dirname(os.path.realpath(__file__)) + "/../parameters.yaml"  

    def __init__(self,debug) -> None:
        """
        Initializes the SharedState with paths to configuration and parameters files,
        loads initial configurations and settings, and initializes market data attributes.
        """        
        self.debug = debug
        
        # self.logging = Logger(debug_mode=self.debug)
        
        self.exchanges: Dict = dict()
        self.websockets: Dict = dict()
        self.data: Dict = dict()

        self.parameters = {}
        self.param_path = self.set_parameters_path()
        self.load_config()    
        self.load_parameters()
                
        # #Lock  that has to be used in every method accessing sharedstate for thread sync
        # self.lock = threading.Lock()

    @abstractmethod
    def set_parameters_path(self) -> str:
        """
        Abstract method to set the path of the parameters YAML file.

        Returns
        -------
        str
            The file path to the parameters YAML file.
        """
        pass

    @abstractmethod
    def process_parameters(self, parameters: Dict, reload: bool) -> None:
        """
        Abstract method to process the parameters from the YAML file.

        Parameters
        ----------
        parameters : dict
            The dictionary of parameters loaded from the YAML file.

        reload : bool
            Flag to indicate if the parameters are being reloaded.
        """
        pass
    
    def load_exchange(self, exchange: str, exchangeType: str, symbol:str) -> None:
        """
        Loads the specified exchange and initializes the exchange and websocket objects.

        Parameters
        ----------
        exchange : str
            The name of the exchange to be loaded.

        Raises
        ------
        Exception
            If the specified exchange is not found or invalid.
        """         
            
        if exchange.lower() == "binance":
            from src.exchanges.binance.exchange import Binance
            from src.exchanges.binance.websocket import BinanceWebsocket
            
            # NOTE: Binance requires capital symbols
            self.exchanges["binance"]["symbol"] = symbol.upper()
            
            if self.exchanges["binance"]["type"].lower() == "trading" :
                if (not self.config["binance"].get("api_key",False) or not self.config["binance"].get("api_secret",False)) :
                    raise Exception("Missing/incorrect API credentials!")
                else:
                    api_key = self.config["binance"]["api_key"]
                    api_secret = self.config["binance"]["api_secret"]
            else:
                api_key = None
                api_secret = None
                
            self.exchanges["binance"]["exchange"] = Binance(api_key, api_secret)
            self.exchanges["binance"]["exchange"].load_required_refs(
                logging=self.logging.createChild("binance.exchange",self.debug),
                symbol=self.exchanges["binance"]["symbol"],
                data=self.data["binance"]
                )

            self.websockets["binance"] = BinanceWebsocket(self.exchanges["binance"]["exchange"],ws_record=True)
            self.websockets["binance"].load_required_refs(
                logging=self.logging.createChild("binance.ws",self.debug),
                symbol=self.exchanges["binance"]["symbol"],
                data=self.data["binance"]
                )

        elif exchange.lower() == "bybit": 
            from frameworks.exchange.bybit.exchange import Bybit
            from frameworks.exchange.bybit.websocket import BybitWebsocket

            # NOTE: Bybit requires capital symbols
            self.exchanges["bybit"]["symbol"] = symbol.upper()
            
            if self.exchanges["bybit"]["type"].lower() == "trading" :
                if (not self.config["bybit"].get("api_key",False) or not self.config["bybit"].get("api_secret",False)) :
                    raise Exception("Missing/incorrect API credentials!")
                else:
                    api_key = self.config["bybit"]["api_key"]
                    api_secret = self.config["bybit"]["api_secret"]
            else:
                api_key = None
                api_secret = None

            self.exchanges["bybit"]["exchange"] = Bybit(api_key, api_secret)
            self.exchanges["bybit"]["exchange"].load_required_refs(
                logging=self.logging.createChild("bybit.exchange",self.debug),
                symbol=self.exchanges["bybit"]["symbol"],
                data=self.data["bybit"]
                )

            self.websockets["bybit"] = BybitWebsocket(self.exchanges["bybit"]["exchange"])
            self.websockets["bybit"].load_required_refs(
                logging=self.logging.createChild("bybit.ws",self.debug),
                symbol=self.exchanges["bybit"]["symbol"],
                data=self.data["bybit"]
                )

        elif exchange.lower() == "hyperliquid":
            
                from src.exchanges.hyperliquid.exchange import Hyperliquid
                from src.exchanges.hyperliquid.ws import HlWebsocket
                
                # NOTE: Hl requires capital symbols
                self.exchanges["hyperliquid"]["symbol"] = symbol.upper()
                
                if self.exchanges["hyperliquid"]["type"].lower() == "trading" :
                    if (not self.config["hyperliquid"].get("secret_key",False)):
                        raise Exception("Missing/incorrect API credentials!")
                    else:
                        secret_key = self.config["hyperliquid"]["secret_key"]
                else:
                    #TODO: Change this logic. When using None as secret key, it throws an erros when creating a wallet during exchange __init__ 
                    secret_key = None

                self.exchanges["hyperliquid"]["exchange"] = Hyperliquid(secret_key, is_mainnet=True)
                self.exchanges["hyperliquid"]["exchange"].load_required_refs(
                    logging=self.logging.createChild("hyperliquid.exchange",self.debug),
                    symbol=self.exchanges["hyperliquid"]["symbol"],
                    data=self.data["hyperliquid"]
                )

                self.websockets["hyperliquid"] = HlWebsocket(self.exchanges["hyperliquid"]["exchange"],ws_record=True)
                self.websockets["hyperliquid"].load_required_refs(
                    logging=self.logging.createChild("hyperliquid.ws",self.debug),
                    symbol=self.exchanges["hyperliquid"]["symbol"],
                    data=self.data["hyperliquid"]
                )
                
        elif exchange.lower() == "bitget":
            from src.exchanges.bitget.exchange import Bitget
            from src.exchanges.bitget.websocket import BitgetWebsocket
            
            # NOTE: bitget requires capital symbols
            self.exchanges["bitget"]["symbol"] = symbol.upper()
            
            if self.exchanges["bitget"]["type"].lower() == "trading" :
                if (not self.config["bitget"].get("secret_key",False)) or (not self.config["bitget"].get("api_key",False)) or (not self.config["bitget"].get("passphrase",False)):
                    raise Exception("Missing/incorrect API credentials!")
                else:
                    secret_key = self.config["bitget"]["secret_key"]
                    api_key = self.config["bitget"]["api_key"]
                    passphrase = self.config["bitget"]["passphrase"]
            else:
                secret_key = None

            self.exchanges["bitget"]["exchange"] = Bitget(api_key, api_secret,passphrase)
            self.exchanges["bitget"]["exchange"].load_required_refs(
                logging=self.logging.createChild("bitget.exchange",self.debug),
                symbol=self.exchanges["bitget"]["symbol"],
                data=self.data["bitget"]
                )

            self.websockets["bitget"] = BitgetWebsocket(self.exchanges["bitget"]["exchange"])
            self.websockets["bitget"].load_required_refs(
                logging=self.logging.createChild("bitget.ws",self.debug),
                symbol=self.exchanges["bitget"]["symbol"],
                data=self.data["bitget"]
                )
            
        elif exchange.lower() == "dydx":
            from src.exchanges.dydx_v4.exchange import Dydx
            from src.exchanges.dydx_v4.websocket import DydxWebsocket

            self.exchanges["dydx"]["exchange"] = Dydx(api_key, api_secret)
            self.exchanges["dydx"]["exchange"].load_required_refs(
                logging=self.logging.createChild("dydx.exchange",self.debug),
                symbol=self.exchanges["dydx"]["symbol"],
                data=self.data["dydx"]
                )

            self.websockets["dydx"] = DydxWebsocket(self.exchanges["dydx"]["exchange"])
            self.websockets["dydx"].load_required_refs(
                logging=self.logging.createChild("dydx.ws",self.debug),
                symbol=self.exchanges["dydx"]["symbol"],
                data=self.data["dydx"]
                )

        elif exchange.lower() in ["okx" , "paradex" , "vertex" , "kraken" , "x10"]:
            raise NotImplementedError

        else:
            raise ValueError("Invalid exchange name, not found...")

    def load_config(self) -> None:
        """
        Loads all the API credentials from the config file

        Raises
        ------
        Exception
            If the API credentials are missing or incorrect.
        """
        
        current_folder = os.path.dirname(os.path.abspath(__file__))
        while current_folder.split(os.sep)[-1] != "src":
            current_folder  = os.path.dirname(current_folder)
        
        config_path = os.path.join(current_folder, 'exchanges', 'config.json.enc')
        
        
        password = getpass("Enter password to decrypt the file: ")
        decrypted_data = decrypt_config(config_path, password)
        self.config = json.loads(decrypted_data)
            
    def load_parameters(self, reload: bool = False) -> None:
        """
        Loads initial trading settings from the parameters YAML file.

        Parameters
        ----------
        reload : bool, optional
            Flag to indicate if the parameters are being reloaded (default is False).
        """
        try:
            with open(self.param_path, "r") as f:
                params = yaml.safe_load(f)
                self.process_parameters(params, reload)

        except Exception as e:
            raise Exception(f"Error loading parameters: {e}")
    
    def generate_data_dict(self,exchange_name):
        exchange_name = exchange_name.lower()
        self.data[exchange_name] = { 
                                "symbol" : self.exchanges[exchange_name]["symbol"],
                                
                                "ohlcv": RingBuffer(1000, dtype=(np.float64, 8)) if exchange_name.lower()=="hyperliquid" else RingBuffer(1000, dtype=(np.float64, 6)),
                                "trades": RingBuffer(1000, dtype=(np.float64, 4)),
                                "orderbook": BaseOrderbook(30,3) if exchange_name.lower()=="hyperliquid" else BaseOrderbook(50), # NOTE: Modify OB size if required!
                                "ticker": {
                                    "timestamp": 0.0,
                                    "markPrice": 0.0,
                                    "indexPrice": 0.0,
                                    "fundingTime": 0.0,
                                    "fundingRate": 0.0,

                                },
                                "tick_size": 0.0,
                                "lot_size": 0.0,
                                }                                
        if self.exchanges[exchange_name]["type"].lower() == "trading":
            
            self.data[exchange_name].update(
                                {
                                "flags": {"position": asyncio.Event(),
                                          "to_create":asyncio.Event(),
                                          "to_amend": asyncio.Event(),
                                          "to_cancel":asyncio.Event(),
                                          },
                                "max_leverage" : 0.0,
                                "position": Position(symbol=self.exchanges[exchange_name]["symbol"]),
                                
                                "orders": { # All the dictionnaries are indexed with client order id (cloid for Hl) as keys
                                    "to_create": dict(),
                                    "to_amend": dict(),
                                    "to_cancel": dict(), #dict of oids OR cloids to cancel with associated order
                                    
                                    "tp":dict(),
                                    "sl":dict(), 
                                    
                                    "in_flight": dict(), #Orders sent by us but not yet acknowledged by the exchange
                                    "to_be_triggered": dict(), #Necessary for HL since "open" message comes before "triggered", therefore we cannot interpret "open" as having hit the Ob. Once a "trggered" message is received, the handler transfers order to "in_the_books"
                                    "in_the_book": dict(), #Orders that have hit the orderbook. Market orders will momentarely go through here before the handler reads the "filled" message
                                    "recently_cancelled": dict() #keeps track of the canceled orders for logging purposes, etc.
                                        },
                                "account_balance": 0.0,
                                }
                            )       
    
    async def start_internal_processes(self) -> None:
        """
        Starts the internal processes such as warming up the exchange and starting the websocket.
        """
        coroutines = []
        
        for exchange_name in self.exchanges.keys():
            coroutines.append(self.exchanges[exchange_name]["exchange"].warmup())
            coroutines.append(self.websockets[exchange_name].start())
             
        await asyncio.gather(*coroutines)
    

    async def refresh_parameters(self, interval: float=10.0) -> None:
        """
        Periodically refreshes trading parameters from the parameters file.
        """
        # self.load_parameters(reload=False)
        while True:
            await asyncio.sleep(interval)
            self.load_parameters(reload=True)