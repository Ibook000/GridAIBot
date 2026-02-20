"""
OKX API 客户端管理模块
统一管理所有 OKX API 客户端实例
"""
from okx import Account, Grid, MarketData

from config import (
    OKX_API_KEY,
    OKX_API_SECRET,
    OKX_PASSPHRASE,
    OKX_FLAG,
)


class OKXClient:
    """
    OKX API 客户端管理类
    提供统一的客户端初始化和访问接口
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._account = None
        self._grid = None
        self._market = None
        self._initialized = True

    @property
    def account(self) -> Account.AccountAPI:
        """
        获取账户 API 客户端
        用于查询持仓、余额等信息
        """
        if self._account is None:
            self._account = Account.AccountAPI(
                api_key=OKX_API_KEY,
                api_secret_key=OKX_API_SECRET,
                passphrase=OKX_PASSPHRASE,
                flag=OKX_FLAG,
                debug=False
            )
        return self._account

    @property
    def grid(self) -> Grid.GridAPI:
        """
        获取网格策略 API 客户端
        用于查询和管理网格策略
        """
        if self._grid is None:
            self._grid = Grid.GridAPI(
                api_key=OKX_API_KEY,
                api_secret_key=OKX_API_SECRET,
                passphrase=OKX_PASSPHRASE,
                flag=OKX_FLAG,
                debug=False
            )
        return self._grid

    @property
    def market(self) -> MarketData.MarketAPI:
        """
        获取市场数据 API 客户端
        用于查询行情、K线等公开数据（无需 API 密钥）
        """
        if self._market is None:
            self._market = MarketData.MarketAPI(
                api_key='',
                api_secret_key='',
                passphrase='',
                flag=OKX_FLAG,
                debug=False
            )
        return self._market


okx_client = OKXClient()
