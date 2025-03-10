import eth_account
import logging
import secrets

from eth_abi import encode
from eth_account.signers.local import LocalAccount
from eth_utils import keccak, to_hex

from src.exchanges.hyperliquid.sdk.aapi import aAPI
from src.exchanges.hyperliquid.sdk.info import Info

from src.exchanges.hyperliquid.sdk.utils.constants import MAINNET_API_URL
from src.exchanges.hyperliquid.sdk.utils.signing import (
    CancelRequest,
    CancelByCloidRequest,
    ModifyRequest,
    OrderRequest,
    OrderType,
    OrderWire,
    ScheduleCancelAction,
    float_to_usd_int,
    get_timestamp_ms,
    order_request_to_order_wire,
    order_wires_to_order_action,
    sign_l1_action,
    sign_usd_transfer_action,
    sign_withdraw_from_bridge_action,
    sign_agent,
)
from src.exchanges.hyperliquid.sdk.utils.types import Any, List, Meta, SpotMeta, Optional, Tuple, Cloid


class aExchange(aAPI):

    # Default Max Slippage for Market Orders 5%
    DEFAULT_SLIPPAGE = 0.05

    def __init__(
        self,
        wallet: LocalAccount,
        base_url: Optional[str] = None,
        meta: Optional[Meta] = None,
        vault_address: Optional[str] = None,
        account_address: Optional[str] = None,
        spot_meta: Optional[SpotMeta] = None,
        **kwargs
        ):
        super().__init__(base_url=base_url, **kwargs)
        self.wallet = wallet
        self.vault_address = vault_address
        self.account_address = account_address
        
        info = Info(base_url,True)
        if meta is None:
            self.meta = info.meta()
        else:
            self.meta = meta

        if spot_meta is None:
            self.spot_meta = info.spot_meta()
        else:
            self.spot_meta = spot_meta

        self.coin_to_asset = {asset_info["name"]: asset for (asset, asset_info) in enumerate(self.meta["universe"])}

        # spot assets start at 10000
        for i, spot_pair in enumerate(self.spot_meta["universe"]):
            self.coin_to_asset[spot_pair["name"]] = i + 10000
        
        info.close()
        del info   

    async def _post_action(self, action, signature, nonce):
        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": self.vault_address,
        }
        logging.debug(payload)
        return await self.post("/exchange", payload)

    async def _slippage_price(
        self,
        coin: str,
        is_buy: bool,
        slippage: float,
        px: Optional[float] = None,
    ) -> float:

        if not px:
            # Get midprice
            px = float((await self.all_mids())[coin])
        # Calculate Slippage
        px *= (1 + slippage) if is_buy else (1 - slippage)
        # We round px to 5 significant figures and 6 decimals
        return round(float(f"{px:.5g}"), 6)

    async def order(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: OrderType,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
    ) -> Any:
        order: OrderRequest = {
            "coin": coin,
            "is_buy": is_buy,
            "sz": sz,
            "limit_px": limit_px,
            "order_type": order_type,
            "reduce_only": reduce_only,
        }
        if cloid:
            order["cloid"] = cloid
        return await self.bulk_orders([order])

    async def bulk_orders(self, order_requests: List[OrderRequest]) -> Any:
        order_wires: List[OrderWire] = [
            order_request_to_order_wire(order, self.coin_to_asset[order["coin"]]) for order in order_requests
        ]
        timestamp = get_timestamp_ms()

        order_action = order_wires_to_order_action(order_wires)

        signature = sign_l1_action(
            self.wallet,
            order_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )

        return await self._post_action(
            order_action,
            signature,
            timestamp,
        )

    async def modify_order(
        self,
        oid: int,
        coin: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: OrderType,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
    ) -> Any:

        modify: ModifyRequest = {
            "oid": oid,
            "order": {
                "coin": coin,
                "is_buy": is_buy,
                "sz": sz,
                "limit_px": limit_px,
                "order_type": order_type,
                "reduce_only": reduce_only,
                "cloid": cloid,
            },
        }
        return await self.bulk_modify_orders_new([modify])

    async def bulk_modify_orders_new(self, modify_requests: List[ModifyRequest]) -> Any:
        timestamp = get_timestamp_ms()
        modify_wires = [
            {
                "oid": modify["oid"],
                "order": order_request_to_order_wire(modify["order"], self.coin_to_asset[modify["order"]["coin"]]),
            }
            for modify in modify_requests
        ]

        modify_action = {
            "type": "batchModify",
            "modifies": modify_wires,
        }

        signature = sign_l1_action(
            self.wallet,
            modify_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )

        return await self._post_action(
            modify_action,
            signature,
            timestamp,
        )

    async def market_open(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        px: Optional[float] = None,
        slippage: float = DEFAULT_SLIPPAGE,
        cloid: Optional[Cloid] = None,
    ) -> Any:

        # Get aggressive Market Price
        px = self._slippage_price(coin, is_buy, slippage, px)
        # Market Order is an aggressive Limit Order IoC
        return await self.order(coin, is_buy, sz, px, order_type={"limit": {"tif": "Ioc"}}, reduce_only=False, cloid=cloid)

    async def market_close(
        self,
        coin: str,
        sz: Optional[float] = None,
        px: Optional[float] = None,
        slippage: float = DEFAULT_SLIPPAGE,
        cloid: Optional[Cloid] = None,
    ) -> Any:
        address = self.wallet.address
        if self.account_address:
            address = self.account_address
        if self.vault_address:
            address = self.vault_address
        positions = (await self.user_state(address))["assetPositions"]
        for position in positions:
            item = position["position"]
            if coin != item["coin"]:
                continue
            szi = float(item["szi"])
            if not sz:
                sz = abs(szi)
            is_buy = True if szi < 0 else False
            # Get aggressive Market Price
            px = self._slippage_price(coin, is_buy, slippage, px)
            # Market Order is an aggressive Limit Order IoC
            return  await self.order(coin, is_buy, sz, px, order_type={"limit": {"tif": "Ioc"}}, reduce_only=True, cloid=cloid)

    async def cancel(self, coin: str, oid: int) -> Any:
        return await self.bulk_cancel([{"coin": coin, "oid": oid}])

    async def cancel_by_cloid(self, coin: str, cloid: Cloid) -> Any:
        return await self.bulk_cancel_by_cloid([{"coin": coin, "cloid": cloid}])

    async def bulk_cancel(self, cancel_requests: List[CancelRequest]) -> Any:
        timestamp = get_timestamp_ms()
        cancel_action = {
            "type": "cancel",
            "cancels": [
                {
                    "a": self.coin_to_asset[cancel["coin"]],
                    "o": cancel["oid"],
                }
                for cancel in cancel_requests
            ],
        }
        signature = sign_l1_action(
            self.wallet,
            cancel_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )

        return await self._post_action(
            cancel_action,
            signature,
            timestamp,
        )

    async def bulk_cancel_by_cloid(self, cancel_requests: List[CancelByCloidRequest]) -> Any:
        timestamp = get_timestamp_ms()

        cancel_action = {
            "type": "cancelByCloid",
            "cancels": [
                {
                    "asset": self.coin_to_asset[cancel["coin"]],
                    "cloid": cancel["cloid"].to_raw(),
                }
                for cancel in cancel_requests
            ],
        }
        signature = sign_l1_action(
            self.wallet,
            cancel_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )

        return await self._post_action(
            cancel_action,
            signature,
            timestamp,
        )

    async def schedule_cancel(self, time: Optional[int]) -> Any:
        """Schedules a time (in UTC millis) to cancel all open orders. The time must be at least 5 seconds after the current time.
        Once the time comes, all open orders will be canceled and a trigger count will be incremented. The max number of triggers
        per day is 10. This trigger count is reset at 00:00 UTC.

        Args:
            time (int): if time is not None, then set the cancel time in the future. If None, then unsets any cancel time in the future.
        """
        timestamp = get_timestamp_ms()
        schedule_cancel_action: ScheduleCancelAction = {
            "type": "scheduleCancel",
        }
        if time is not None:
            schedule_cancel_action["time"] = time
        signature = sign_l1_action(
            self.wallet,
            schedule_cancel_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )
        return await self._post_action(
            schedule_cancel_action,
            signature,
            timestamp,
        )

    async def update_leverage(self, leverage: int, coin: str, is_cross: bool = True) -> Any:
        timestamp = get_timestamp_ms()
        asset = self.coin_to_asset[coin]
        update_leverage_action = {
            "type": "updateLeverage",
            "asset": asset,
            "isCross": is_cross,
            "leverage": leverage,
        }
        signature = sign_l1_action(
            self.wallet,
            update_leverage_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )
        return await self._post_action(
            update_leverage_action,
            signature,
            timestamp,
        )

    async def update_isolated_margin(self, amount: float, coin: str) -> Any:
        timestamp = get_timestamp_ms()
        asset = self.coin_to_asset[coin]
        amount = float_to_usd_int(amount)
        update_isolated_margin_action = {
            "type": "updateIsolatedMargin",
            "asset": asset,
            "isBuy": True,
            "ntli": amount,
        }
        signature = sign_l1_action(
            self.wallet,
            update_isolated_margin_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )
        return await self._post_action(
            update_isolated_margin_action,
            signature,
            timestamp,
        )

    async def set_referrer(self, code: str) -> Any:
        timestamp = get_timestamp_ms()
        set_referrer_action = {
            "type": "setReferrer",
            "code": code,
        }
        signature = sign_l1_action(
            self.wallet,
            set_referrer_action,
            None,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )
        return await self._post_action(
            set_referrer_action,
            signature,
            timestamp,
        )

    async def create_sub_account(self, name: str) -> Any:
        timestamp = get_timestamp_ms()
        create_sub_account_action = {
            "type": "createSubAccount",
            "name": name,
        }
        signature = sign_l1_action(
            self.wallet,
            create_sub_account_action,
            None,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )
        return await self._post_action(
            create_sub_account_action,
            signature,
            timestamp,
        )

    async def user_spot_transfer(self, usdc: float, to_perp: bool) -> Any:
        usdc = int(round(usdc, 2) * 1e6)
        timestamp = get_timestamp_ms()
        spot_user_action = {
            "type": "spotUser",
            "classTransfer": {
                "usdc": usdc,
                "toPerp": to_perp,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            spot_user_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )
        return await self._post_action(
            spot_user_action,
            signature,
            timestamp,
        )

    async def sub_account_transfer(self, sub_account_user: str, is_deposit: bool, usd: int) -> Any:
        timestamp = get_timestamp_ms()
        sub_account_transfer_action = {
            "type": "subAccountTransfer",
            "subAccountUser": sub_account_user,
            "isDeposit": is_deposit,
            "usd": usd,
        }
        signature = sign_l1_action(
            self.wallet,
            sub_account_transfer_action,
            None,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )
        return await self._post_action(
            sub_account_transfer_action,
            signature,
            timestamp,
        )

    async def usd_transfer(self, amount: float, destination: str) -> Any:
        timestamp = get_timestamp_ms()
        payload = {
            "destination": destination,
            "amount": str(amount),
            "time": timestamp,
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_usd_transfer_action(self.wallet, payload, is_mainnet)
        return await self._post_action(
            {
                "chain": "Arbitrum" if is_mainnet else "ArbitrumTestnet",
                "payload": payload,
                "type": "usdTransfer",
            },
            signature,
            timestamp,
        )

    async def withdraw_from_bridge(self, usd: float, destination: str) -> Any:
        timestamp = get_timestamp_ms()
        payload = {
            "destination": destination,
            "usd": str(usd),
            "time": timestamp,
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_withdraw_from_bridge_action(self.wallet, payload, is_mainnet)
        return await self._post_action(
            {
                "chain": "Arbitrum" if is_mainnet else "ArbitrumTestnet",
                "payload": payload,
                "type": "withdraw2",
            },
            signature,
            timestamp,
        )

    async def approve_agent(self, name: Optional[str] = None) -> Tuple[Any, str]:
        agent_key = "0x" + secrets.token_hex(32)
        account = eth_account.Account.from_key(agent_key)
        if name is not None:
            connection_id = keccak(encode(["address", "string"], [account.address, name]))
        else:
            connection_id = keccak(encode(["address"], [account.address]))
        agent = {
            "source": "https://hyperliquid.xyz",
            "connectionId": connection_id,
        }
        timestamp = get_timestamp_ms()
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_agent(self.wallet, agent, is_mainnet)
        agent["connectionId"] = to_hex(agent["connectionId"])
        action = {
            "chain": "Arbitrum" if is_mainnet else "ArbitrumTestnet",
            "agent": agent,
            "agentAddress": account.address,
            "type": "connect",
        }
        if name is not None:
            action["extraAgentName"] = name
        return await (
            self._post_action(
                action,
                signature,
                timestamp,
            ),
            agent_key,
        )
    
    async def close_aexchange(self):
        await self.session.close()
