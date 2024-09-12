
from src.exchanges.hyperliquid.sdk.aapi import aAPI
from src.exchanges.hyperliquid.sdk.utils.types import Any, Callable, Meta, SpotMeta,SpotMetaAndAssetCtxs, Optional, Subscription, cast, Cloid
import threading


class aInfo(aAPI):
    def __init__(self, base_url=None,**kwargs):
        super().__init__(base_url=base_url, **kwargs)
        print(f'aInfo() being called from thread: {threading.current_thread().name}')

    async def user_state(self, address: str) -> Any:
        """Retrieve trading details about a user.

        POST /info

        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns:
            {
                assetPositions: [
                    {
                        position: {
                            coin: str,
                            entryPx: Optional[float string]
                            leverage: {
                                type: "cross" | "isolated",
                                value: int,
                                rawUsd: float string  # only if type is "isolated"
                            },
                            liquidationPx: Optional[float string]
                            marginUsed: float string,
                            positionValue: float string,
                            returnOnEquity: float string,
                            szi: float string,
                            unrealizedPnl: float string
                        },
                        type: "oneWay"
                    }
                ],
                crossMarginSummary: MarginSummary,
                marginSummary: MarginSummary,
                withdrawable: float string,
            }

            where MarginSummary is {
                    accountValue: float string,
                    totalMarginUsed: float string,
                    totalNtlPos: float string,
                    totalRawUsd: float string,
                }
        """
        return await self.post("/info", {"type": "clearinghouseState", "user": address})

    async def spot_user_state(self, address: str) -> Any:
        return await self.post("/info", {"type": "spotClearinghouseState", "user": address})

    async def open_orders(self, address: str) -> Any:
        """Retrieve a user's open orders.

        POST /info

        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns: [
            {
                coin: str,
                limitPx: float string,
                oid: int,
                side: "A" | "B",
                sz: float string,
                timestamp: int
            }
        ]
        """
        return await self.post("/info", {"type": "openOrders", "user": address})

    async def frontend_open_orders(self, address: str) -> Any:
        """Retrieve a user's open orders with additional frontend info.

        POST /info

        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns: [
            {
                children:
                    [
                        dict of frontend orders
                    ]
                coin: str,
                isPositionTpsl: bool,
                isTrigger: bool,
                limitPx: float string,
                oid: int,
                orderType: str,
                origSz: float string,
                reduceOnly: bool,
                side: "A" | "B",
                sz: float string,
                tif: str,
                timestamp: int,
                triggerCondition: str,
                triggerPx: float str
            }
        ]
        """
        return await self.post("/info", {"type": "frontendOpenOrders", "user": address})

    async def all_mids(self) -> Any:
        """Retrieve all mids for all actively traded coins.

        POST /info

        Returns:
            {
              ATOM: float string,
              BTC: float string,
              any other coins which are trading: float string
            }
        """
        return await self.post("/info", {"type": "allMids"})

    async def user_fills(self, address: str) -> Any:
        """Retrieve a given user's fills.

        POST /info

        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.

        Returns:
            [
              {
                closedPnl: float string,
                coin: str,
                crossed: bool,
                dir: str,
                hash: str,
                oid: int,
                px: float string,
                side: str,
                startPosition: float string,
                sz: float string,
                time: int
              },
              ...
            ]
        """
        return await self.post("/info", {"type": "userFills", "user": address})

    async def meta(self) -> Meta:
        """Retrieve exchange perp metadata

        POST /info

        Returns:
            {
                universe: [
                    {
                        name: str,
                        szDecimals: int
                    },
                    ...
                ]
            }
        """
        return cast(Meta, await self.post("/info", {"type": "meta"}))

    async def metaAndAssetCtxs(self) -> Any:
        """Retrieve exchange MetaAndAssetCtxs
        
        POST /info
        
        Returns:
            [
                {
                    universe: [
                        {
                            'maxLeverage': int,
                            'name': str,
                            'onlyIsolated': bool,
                            'szDecimals': int
                        },
                        ...
                    ]
                },
            [
                {
                    "dayNtlVlm": str,
                    "funding": str,
                    "impactPxs": [str, str],
                    "markPx": str,
                    "midPx": str,
                    "openInterest": str,
                    "oraclePx": str,
                    "premium": str,
                    "prevDayPx": str
                },
                ...
            ]
        """
        return await self.post("/info", {"type": "metaAndAssetCtxs"})

    async def spot_meta(self) -> SpotMeta:
        """Retrieve exchange spot metadata

        POST /info

        Returns:
            {
                tokens: [
                    {
                        name: str,
                        szDecimals: int,
                        weiDecimals: int
                    },
                    ...
                ],
                universe: [
                    {
                        name: str,
                        tokens: [int, int]
                    },
                    ...
                ]
            }
        """
        return cast(SpotMeta, await self.post("/info", {"type": "spotMeta"}))

    async def spot_meta_and_asset_ctxs(self) -> SpotMetaAndAssetCtxs:
        """Retrieve exchange spot asset contexts

        POST /info

        Returns:
            [
                {
                    universe: [
                        {
                            name: str,
                            tokens: [int, int]
                        }
                        ...
                    ],
                    tokens: [
                        {
                            name: str,
                            szDecimals: int,
                            weiDecimals int
                        },
                        ...
                    ]
                },
                [
                    {
                        dayNtlVlm: float,
                        markPx: float,
                        midPx: float,
                        prevDayPx: float,
                        circulatingSupply: float,
                        coin: str
                    }
                    ...
                ]
            ]
        """
        return cast(SpotMetaAndAssetCtxs, await self.post("/info", {"type": "spotMetaAndAssetCtxs"}))

    async def funding_history(self, coin: str, startTime: int, endTime: Optional[int] = None) -> Any:
        """Retrieve funding history for a given coin

        POST /info

        Args:
            coin (str): Coin to retrieve funding history for.
            startTime (int): Unix timestamp in milliseconds.
            endTime (int): Unix timestamp in milliseconds.

        Returns:
            [
                {
                    coin: str,
                    fundingRate: float string,
                    premium: float string,
                    time: int
                },
                ...
            ]
        """
        if endTime is not None:
            return await self.post(
                "/info", {"type": "fundingHistory", "coin": coin, "startTime": startTime, "endTime": endTime}
            )
        return await self.post("/info", {"type": "fundingHistory", "coin": coin, "startTime": startTime})

    async def user_funding_history(self, user: str, startTime: int, endTime: Optional[int] = None) -> Any:
        """Retrieve a user's funding history
        POST /info
        Args:
            user (str): Address of the user in 42-character hexadecimal format.
            startTime (int): Start time in milliseconds, inclusive.
            endTime (int, optional): End time in milliseconds, inclusive. Defaults to current time.
        Returns:
            List[Dict]: A list of funding history records, where each record contains:
                - user (str): User address.
                - type (str): Type of the record, e.g., "userFunding".
                - startTime (int): Unix timestamp of the start time in milliseconds.
                - endTime (int): Unix timestamp of the end time in milliseconds.
        """
        if endTime is not None:
            return await self.post("/info", {"type": "userFunding", "user": user, "startTime": startTime, "endTime": endTime})
        return await self.post("/info", {"type": "userFunding", "user": user, "startTime": startTime})

    async def l2_snapshot(self, coin: str) -> Any:
        """Retrieve L2 snapshot for a given coin

        POST /info

        Args:
            coin (str): Coin to retrieve L2 snapshot for.

        Returns:
            {
                coin: str,
                levels: [
                    [
                        {
                            n: int,
                            px: float string,
                            sz: float string
                        },
                        ...
                    ],
                    ...
                ],
                time: int
            }
        """
        return await self.post("/info", {"type": "l2Book", "coin": coin})

    async def candles_snapshot(self, coin: str, interval: str, startTime: int, endTime: int) -> Any:
        """Retrieve candles snapshot for a given coin

        POST /info

        Args:
            coin (str): Coin to retrieve candles snapshot for.
            interval (str): Candlestick interval.
            startTime (int): Unix timestamp in milliseconds.
            endTime (int): Unix timestamp in milliseconds.

        Returns:
            [
                {
                    T: int,
                    c: float string,
                    h: float string,
                    i: str,
                    l: float string,
                    n: int,
                    o: float string,
                    s: string,
                    t: int,
                    v: float string
                },
                ...
            ]
        """
        req = {"coin": coin, "interval": interval, "startTime": startTime, "endTime": endTime}
        return await self.post("/info", {"type": "candleSnapshot", "req": req})
    
    async def user_fees(self, address: str) -> Any:
        """Retrieve the volume of trading activity associated with a user.
        POST /info
        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns:
            {
                activeReferralDiscount: float string,
                dailyUserVlm: [
                    {
                        date: str,
                        exchange: str,
                        userAdd: float string,
                        userCross: float string
                    },
                ],
                feeSchedule: {
                    add: float string,
                    cross: float string,
                    referralDiscount: float string,
                    tiers: {
                        mm: [
                            {
                                add: float string,
                                makerFractionCutoff: float string
                            },
                        ],
                        vip: [
                            {
                                add: float string,
                                cross: float string,
                                ntlCutoff: float string
                            },
                        ]
                    }
                },
                userAddRate: float string,
                userCrossRate: float string
            }
        """
        return await self.post("/info", {"type": "userFees", "user": address})

    async def query_order_by_oid(self, user: str, oid: int) -> Any:
        return await self.post("/info", {"type": "orderStatus", "user": user, "oid": oid})

    async def query_order_by_cloid(self, user: str, cloid: Cloid) -> Any:
        return await self.post("/info", {"type": "orderStatus", "user": user, "oid": cloid.to_raw()})

    async def query_referral_state(self, user: str) -> Any:
        return await self.post("/info", {"type": "referral", "user": user})

    async def query_sub_accounts(self, user: str) -> Any:
        return await self.post("/info", {"type": "subAccounts", "user": user})
    
    async def close_ainfo(self):
        await self.session.close()

