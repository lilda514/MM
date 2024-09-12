import orjson
# import logging
from orjson import JSONDecodeError

import aiohttp

from src.exchanges.hyperliquid.sdk.utils.constants import MAINNET_API_URL
from src.exchanges.hyperliquid.sdk.utils.error import ClientError, ServerError
from src.exchanges.hyperliquid.sdk.utils.types import Any


class aAPI:
    def __init__(
        self,
        base_url=None,
                 ) -> None:
        self.base_url = MAINNET_API_URL
        self.session = aiohttp.ClientSession(headers = {"Content-Type": "application/json"})

        if base_url is not None:
            self.base_url = base_url

        # self._logger = logging.getLogger(__name__)
        super().__init__()
        return

    async def post(self, url_path: str, payload: Any = None) -> Any:
        if payload is None:
            payload = {}
        url = self.base_url + url_path
        self.logging.debug(f"payload sent: {payload}")
        response = await self.session.post(url, data = orjson.dumps(payload)) #,json=payload)
        # resp_txt = await response.text()
        # self.logging.debug(f"received msg {resp_txt}")
        await self._handle_exception(response)

        try:
            return await response.json()
        except ValueError:
            return {"error": f"Could not parse JSON: {response.text}"}

    async def _handle_exception(self, response):
        status_code = response.status
        if status_code < 400:
            return
        err_txt = await response.text()
        if 400 <= status_code < 500:
            try:
                err = orjson.loads(err_txt)
            except JSONDecodeError:
                self.logging.debug(f"error: {err_txt}")
                raise ClientError(status_code, None, err_txt, None, response.headers)
            error_data = None
            if "data" in err:
                error_data = err["data"]
            raise ClientError(status_code, err["code"], err["msg"], response.headers, error_data)
        raise ServerError(status_code, err_txt)


