import asyncio
import aiohttp
import orjson
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Callable, Optional

from src.tools.log import LoggerInstance
import time
import msgpack
import zstandard as zstd
import boto3
from datetime import datetime


class WebsocketStream(ABC):
    _success_ = set((aiohttp.WSMsgType.TEXT, aiohttp.WSMsgType.BINARY))
    _failure_ = set((aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR))
    _conns_ = 1  # NOTE: Handlers don't support duplicate detection yet!

    def __init__(self, ws_record = False) -> None:
        """
        Initializes the WebsocketStream class with public and private aiohttp sessions.

        Attributes
        ----------
        public : aiohttp.ClientSession
            The aiohttp session for public WebSocket connections.

        private : aiohttp.ClientSession
            The aiohttp session for private WebSocket connections.
        """
        self.public = aiohttp.ClientSession()
        self.private = aiohttp.ClientSession()
        
        self.ws_record = ws_record
        #Allows to record received websocket messages and save them to s3 bucket. For debugging purposes
        if self.ws_record:    
            self.message_queue = asyncio.Queue()
            self.compressor = zstd.ZstdCompressor(level=3)
            self.s3_client = boto3.client('s3')
            self.BATCH_SIZE = 10000  # Number of messages per batch to save
            self.SAVE_INTERVAL = 3600  # Save to S3 every 1 hour (in seconds) 

    def _disable_trading_methods(self):
        """Disable trading methods if trading access is not allowed."""
        methods_to_disable = [
            'start_private_ws',
            'private_stream_sub',
            'private_stream_handler',
        ]
        for method_name in methods_to_disable:
            setattr(self, method_name, self._method_unavailable)
    
    async def _method_unavailable(self, *args, **kwargs):
        if hasattr(self, 'logging'):
            self.logging.info("This method is unavailable since this exchange is in data mode")
        else:
            print("This method is unavailable since this exchange is in data mode")
        return {}

    def load_required_refs(self, logging: LoggerInstance, symbol: str, data: Dict) -> None:
        """
        Loads required references such as logging, symbol, and data.

        Parameters
        ----------
        logging : Logger
            The Logger instance for logging events and messages.

        symbol : str
            The trading symbol.

        data : dict
            A dictionary holding various shared state data.
        """
        self.logging = logging
        logger_name = self.logging.name
        separated_names = logger_name.split(".")
        self.logging.setFilters(separated_names[-2].upper() + "." + "WS") #Topic is "{Exchange_name}.WS"
        self.logging.setHandlers()
        self.symbol = symbol
        self.data = data

    @abstractmethod
    def create_handlers(self) -> None:
        """
        Abstract method to create handlers for the WebSocket streams.

        This method should be called in .start() *after* self.load_required_refs is completed.
        """
        pass

    @abstractmethod
    async def refresh_orderbook_data(self, timer: int = 600) -> None:
        """
        Periodically fetches and updates the order book data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    async def refresh_trades_data(self, timer: int = 600) -> None:
        """
        Periodically fetches and updates trade data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    async def refresh_ohlcv_data(self, timer: int = 600) -> None:
        """
        Periodically fetches and updates OHLCV data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    async def refresh_ticker_data(self, timer: int = 600) -> None:
        """
        Periodically fetches and updates ticker data at a set interval.

        Parameters
        ----------
        timer : int, optional
            The time interval in seconds between data refreshes, default is 600 seconds.
        """
        pass

    @abstractmethod
    def public_stream_sub(self) -> Tuple[str, List[Dict]]:
        """
        Prepares the subscription request for public WebSocket channels.

        Returns
        -------
        Tuple[str, List[Dict]]
            A tuple containing the WebSocket URL and the formatted subscription request list.
        """
        pass

    @abstractmethod
    async def public_stream_handler(self, recv: Dict) -> None:
        """
        Handles incoming messages from the public WebSocket stream.

        Parameters
        ----------
        recv : Dict
            The received message dictionary.

        Raises
        ------
        KeyError
            If the received message does not contain expected keys or handler mappings.
        """
        pass

    @abstractmethod
    async def private_stream_sub(self) -> Tuple[str, List[Dict]]:
        """
        Prepares the authentication and subscription messages for the private WebSocket channels.

        Returns
        -------
        Tuple[str, List[Dict]]
            A tuple containing the WebSocket URL and the formatted subscription request list.
        """
        pass

    @abstractmethod
    async def private_stream_handler(self, recv: Dict) -> None:
        """
        Handles incoming messages from the private WebSocket stream.

        Parameters
        ----------
        recv : Dict
            The received message dictionary.

        Raises
        ------
        KeyError
            If the received message does not contain expected keys or handler mappings.
        """
        pass
    
    # @abstractmethod
    # async def custom_ping(self,
    #                       ws: aiohttp.ClientWebSocketResponse, 
    #                       stream_str: str, 
    #                       payload: Dict = None,
    #                       timer:float = None
    #                       ):
    #     """
    #     Sends a ping message at a fixed interval

    #     Parameters
    #     ----------
    #     payload : Dict
    #         The the ping payload.

    #     Returns
    #     -------
    #     None.

    #     """
    #     pass
    async def send(
        self, ws: aiohttp.ClientWebSocketResponse, stream_str: str, payload: Dict
    ) -> None:
        """
        Sends a payload through the WebSocket stream.

        Parameters
        ----------
        ws : aiohttp.ClientWebSocketResponse
            The WebSocket connection instance.

        stream_str : str
            The stream type (public or private).

        payload : Dict
            The payload to be sent.


        Raises
        ------
        Exception
            If there is an issue sending the payload.
        """
        try:
            self.logging.debug(
                f"Sending {stream_str} ws payload: {payload}"
            )
            await ws.send_json(payload)
        except Exception as e:
            self.logging.error(
              f"Failed to send {stream_str.lower()} ws payload: {payload} - Error: {e}",
            )

    async def _single_conn_(
        self,
        url: str,
        handler_map: Callable,
        on_connect: List[Dict],
        private: bool,
        custom_ping: dict = None, 
        ping_timer: float = None 
    ) -> bool:
        """
        Manages a single WebSocket connection.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict
            The messages to send upon connection.

        private : bool
            Flag to indicate if the connection is private.


        Returns
        -------
        bool
            Flag indicating if a reconnection is needed.

        Raises
        ------
        Exception
            If there is an issue with the WebSocket connection.
        """
        session = self.private if private else self.public
        stream_str = "private" if private else "public"

        try:
            self.logging.info(
                f"Attempting to start {stream_str} ws stream..."
            )
            
            if ping_timer != None and custom_ping == None: 
                _heartbeat = ping_timer
            else:
                _heartbeat = None
            
            async with session.ws_connect(url, heartbeat = _heartbeat) as ws:
                
                #TODO: add logic for sending custom ping messages
                # asyncio.create_task(self.send(ws,stream_str,custom_ping))
                
                for payload in on_connect:
                    await self.send(ws, stream_str, payload)

                async for msg in ws:
                    await self.message_queue.put((str(time.time_ns()) , msg.data))

                    if msg.type in self._success_:
                        # self.logging.debug(f"{msg.data}")
                        # await handler_map(orjson.loads(msg.data))
                        pass

                    elif msg.type in self._failure_:
                        self.logging.warning(
                            f"{stream_str} ws closed/error, reconnecting...",
                        )

        except asyncio.CancelledError:
            return False

        except orjson.JSONDecodeError:
            self.logging.warning(
                f"Failed to load payload: {msg.data}"
            )

        except Exception as e:
            self.logging.error(f"{stream_str} stream: {e}")
            return True

    async def _create_reconnect_task_(
        self, url: str, handler_map: Callable, on_connect: List[Dict], private: bool, custom_ping: Dict = None, ping_timer: float = None,
    ) -> None:
        """
        Creates a task to manage reconnections.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict
            The messages to send upon connection.

        private : bool
            Flag to indicate if the connection is private.

        """
        while True:
            reconnect = await self._single_conn_(url, handler_map, on_connect, private, custom_ping, ping_timer)
            self.logging.debug(
                f"Attempting to reconnect ws task, status: [{reconnect}]",
            )
            if not reconnect:
                break
            await asyncio.sleep(1.0)

    async def _manage_connections_(
        self, url: str, handler_map: Callable, on_connect: List[Dict], private: bool, custom_ping: Dict = None, ping_timer: float = None,
    ) -> None:
        """
        Manages multiple WebSocket connections.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict
            The messages to send upon connection.

        private : bool
            Flag to indicate if the connection is private.

        """
        tasks = [
            self._create_reconnect_task_(url, handler_map, on_connect, private, custom_ping, ping_timer)
            for _ in range(self._conns_)
        ]
        await asyncio.gather(*tasks)

    async def start_public_ws(
        self, url: str, handler_map: Callable, on_connect: Optional[List[Dict]] = None, custom_ping: Dict = None, ping_timer: float = None,
    ) -> None:
        """
        Starts the public WebSocket connection.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict, optional
            The messages to send upon connection.
        """
        await self._manage_connections_(
            url=url,
            handler_map=handler_map,
            on_connect=[] if on_connect is None else on_connect,
            private=False,
            custom_ping=custom_ping,
            ping_timer=ping_timer,
        )

    async def start_private_ws(
        self, url: str, handler_map: Callable, on_connect: Optional[List[Dict]] = None, custom_ping: Dict = None, ping_timer: float = None,
    ) -> None:
        """
        Starts the private WebSocket connection.

        Parameters
        ----------
        url : str
            The WebSocket URL.

        handler_map : Callable
            The function to handle incoming messages.

        on_connect : list of dict, optional
            The messages to send upon connection.
        """
        await self._manage_connections_(
            url=url,
            handler_map=handler_map,
            on_connect=[] if on_connect is None else on_connect,
            private=False,
            custom_ping=custom_ping,
            ping_timer=ping_timer,
        )
        
    async def save_to_s3(self, message_queue: asyncio.Queue, bucket_name: str, key_prefix: str = None):
        """
        Save messages from the queue to S3 in compressed, hourly batches.

        Parameters
        ----------
        message_queue : asyncio.Queue
            The queue containing messages.
        bucket_name : str
            S3 bucket name.
        key_prefix : str
            Prefix (folder path) for S3 keys.
        """
        if not key_prefix: 
            key_prefix = self.logging.topic.split(".")  # name of the exchange
        
        current_batch = []
        start_time = datetime.utcnow()
        
        try:
            while True:
                try:
                    # Gather messages for batching
                    for _ in range(self.BATCH_SIZE):
                        current_batch.append(await asyncio.wait_for(self.message_queue.get(), timeout=1))
    
                except asyncio.TimeoutError:
                    pass  # No messages to process, proceed with saving
    
                now = datetime.utcnow()
                elapsed_time = (now - start_time).total_seconds()
    
                if len(current_batch) >= self.BATCH_SIZE or (elapsed_time >= self.SAVE_INTERVAL and current_batch): 
                    # Serialize and compress the batch
                    packed_data = msgpack.packb(current_batch)
                    compressed_data = self.compressor.compress(packed_data)

                    # Generate a timestamped S3 key
                    timestamp = start_time.strftime("%Y-%m-%d_%Hh%Mm%Ss")
                    s3_key = f"{key_prefix}/data_{timestamp}.msgpack.zst"

                    # Upload to S3
                    try:
                        self.s3_client.put_object(
                            Bucket=bucket_name,
                            Key=s3_key,
                            Body=compressed_data,
                        )
                        print(f"Uploaded batch to S3: {s3_key}")
                    except Exception as e:
                        print(f"Failed to upload batch to S3: {e}")

                    # Clear the current batch
                    current_batch = []
    
                    # Update start time for the next interval
                    start_time = now
        except asyncio.CancelledError:
            # Handle graceful shutdown
            if current_batch:
                print("Saving remaining messages before shutting down...")
                packed_data = msgpack.packb(current_batch)
                compressed_data = self.compressor.compress(packed_data)
    
                # Generate a timestamped S3 key
                timestamp = datetime.utcnow().strftime("%Y-%m-%d_%Hh%Mm%Ss")
                s3_key = f"{key_prefix}/data_{timestamp}.msgpack.zst"
    
                # Upload to S3
                try:
                    self.s3_client.put_object(
                        Bucket=bucket_name,
                        Key=s3_key,
                        Body=compressed_data,
                    )
                    print(f"Uploaded remaining batch to S3: {s3_key}")
                except Exception as e:
                    print(f"Failed to upload remaining batch to S3: {e}")
            print("Gracefully shutting down...")
        finally:
            # Close the S3 client
            self.s3_client.close()


    @abstractmethod
    async def start(self) -> None:
        """
        Starts all necessary asynchronous tasks for Websocket stream management and data refreshing.
        """
        pass

    async def shutdown(self) -> None:
        """
        Shuts down the WebSocket connections by closing the aiohttp sessions.
        """
        await self.public.close()
        await self.private.close()
        self.logging.close()
