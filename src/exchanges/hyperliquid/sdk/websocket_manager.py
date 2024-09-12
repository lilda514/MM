import orjson
import logging
import threading
import time
from collections import defaultdict

import websocket

from src.exchanges.hyperliquid.sdk.utils.types import Any, Callable, Dict, List, NamedTuple, Optional, Subscription, Tuple, WsMsg

ActiveSubscription = NamedTuple("ActiveSubscription", [("callback", Callable[[Any], None]), ("subscription_id", int)])


def subscription_to_identifier(subscription: Subscription) -> str:
    if subscription["type"] == "allMids":
        return "allMids"
    elif subscription["type"] == "l2Book":
        return f'l2Book:{subscription["coin"].lower()}'
    elif subscription["type"] == "trades":
        return f'trades:{subscription["coin"].lower()}'
    elif subscription["type"] == "user":
        return "userEvents"
    elif subscription["type"] == "orderUpdates":
        return "orderUpdates"
    elif subscription["type"] == "userFills":
        return "userFills"
    elif subscription["type"] == "candle":
        return f'candle:{subscription["coin"].lower()}:{subscription["interval"].lower()}'
    elif subscription["type"] == "userHistoricalOrders":
        return "userHistoricalOrders"


def ws_msg_to_identifier(ws_msg: WsMsg) -> Optional[str]:
    if ws_msg["channel"] == "pong":
        return "pong"
    elif ws_msg["channel"] == "subscriptionResponse":
        return "subscriptionResponse"
    elif ws_msg["channel"] == "allMids":
        return "allMids"
    elif ws_msg["channel"] == "l2Book":
        return f'l2Book:{ws_msg["data"]["coin"].lower()}'
    elif ws_msg["channel"] == "trades":
        trades = ws_msg["data"]
        if len(trades) == 0:
            print(trades)
            return None
        else:
            return f'trades:{trades[0]["coin"].lower()}'
    elif ws_msg["channel"] == "user":
        return "userEvents"
    elif ws_msg["channel"] == "orderUpdates":
        return "orderUpdates"
    elif ws_msg["channel"] == "userFills":
        return "userFills"
    elif ws_msg["channel"] == "candle":
        return f'candle:{ws_msg["data"]["s"].lower()}:{ws_msg["data"]["i"].lower()}'
    elif ws_msg["channel"] == "userHistoricalOrders":
        return "userHistoricalOrders"


class WebsocketManager(threading.Thread):
    def __init__(self, base_url):
        super().__init__()
        self.subscription_id_counter = 0
        self.ws_ready = False
        self.queued_subscriptions: List[Tuple[Subscription, ActiveSubscription]] = []
        self.active_subscriptions: Dict[str, List[ActiveSubscription]] = defaultdict(list)
        ws_url = "ws" + base_url[len("http") :] + "/ws"
        self.ws = websocket.WebSocketApp(ws_url, on_message=self.on_message, on_open=self.on_open)
        self.ping_sender = threading.Thread(target=self.send_ping, name='ping_sender', daemon=True)
        self.stop_event = threading.Event()  # Add stop event

    def run(self): 
        print(f'WebsocketManager() running in thread: {threading.current_thread().name}')
        self.ping_sender.start()
        while not self.stop_event.is_set():
            self.ws.run_forever()
            # Break loop if stop_event is set, otherwise handle reconnect
            if self.stop_event.is_set():
                break
            # Optionally, you can handle reconnection logic here if needed
        self.ws.close()
        self.stop_event.set()


    def send_ping(self):
        while not self.stop_event.is_set():  # Check stop event
            time.sleep(50)  # Wait 50 seconds
            if not self.stop_event.is_set():  # Check again before sending
                logging.debug("Websocket sending ping")
                self.ws.send(orjson.dumps({"method": "ping"}))
                
    def stop(self):
        self.stop_event.set()  # Set the stop event
        self.ws.close()  # Close WebSocket connection when stopping
        self.ws.keep_running = False
        self.ws_ready = False
        self.ping_sender.join()  # Wait for ping_sender to finish
        self.join()  # Wait for the main thread to finish


    def on_message(self, _ws, message):
        if self.stop_event.is_set():
            return  # Exit if stopping
        if message == "Websocket connection established.":
            logging.debug(message)
            return
        #logging.debug(f"on_message {message}")
        ws_msg: WsMsg = orjson.loads(message)
        identifier = ws_msg_to_identifier(ws_msg)
        if identifier == "pong":
            logging.debug("Websocket received pong")
            return
        if identifier == "subscriptionResponse":
            logging.debug(f"subscription successfull to: {ws_msg['data']['subscription']['type']}")
            return
        if identifier is None:
            logging.debug("Websocket not handling empty message")
            return
        active_subscriptions = self.active_subscriptions[identifier]
        if len(active_subscriptions) == 0:
            print("Websocket message from an unexpected subscription:", message, identifier)
        else:
            for active_subscription in active_subscriptions:
                active_subscription.callback(ws_msg)

    def on_open(self, _ws):
        logging.debug("on_open")
        self.ws_ready = True
        for (subscription, active_subscription) in self.queued_subscriptions:
            self.subscribe(subscription, active_subscription.callback, active_subscription.subscription_id)

    def subscribe(
        self, subscription: Subscription, callback: Callable[[Any], None], subscription_id: Optional[int] = None
    ) -> int:
        if self.stop_event.is_set():
            return  # Exit if stopping
        if subscription_id is None:
            self.subscription_id_counter += 1
            subscription_id = self.subscription_id_counter
        if not self.ws_ready:
            logging.debug("enqueueing subscription")
            self.queued_subscriptions.append((subscription, ActiveSubscription(callback, subscription_id)))
        else:
            logging.debug("subscribing")
            identifier = subscription_to_identifier(subscription)
            if subscription["type"] == "userEvents":
                # TODO: ideally the userEvent messages would include the user so that we can support multiplexing them
                if len(self.active_subscriptions[identifier]) != 0:
                    raise NotImplementedError("Cannot subscribe to UserEvents multiple times")
            self.active_subscriptions[identifier].append(ActiveSubscription(callback, subscription_id))
            self.ws.send(orjson.dumps({"method": "subscribe", "subscription": subscription}))
        return subscription_id

    def unsubscribe(self, subscription: Subscription, subscription_id: int) -> bool:
        if not self.ws_ready:
            raise NotImplementedError("Can't unsubscribe before websocket connected")
        if self.stop_event.is_set():
            return  # Exit if stopping
        identifier = subscription_to_identifier(subscription)
        active_subscriptions = self.active_subscriptions[identifier]
        new_active_subscriptions = [x for x in active_subscriptions if x.subscription_id != subscription_id]
        if len(new_active_subscriptions) == 0:
            self.ws.send(orjson.dumps({"method": "unsubscribe", "subscription": subscription}))
        self.active_subscriptions[identifier] = new_active_subscriptions
        return len(active_subscriptions) != len(active_subscriptions)
