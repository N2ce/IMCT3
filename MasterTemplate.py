from typing import Dict, List, Any
import json
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."
logger = Logger()

class Product:
    RAINFOREST_RESIN = "RAINFOREST_RESIN"
    KELP = "KELP"
    SQUID_INK = "SQUID_INK"
    CROISSANTS = "CROISSANTS"
    DJEMBES = "DJEMBES"
    JAMS = "JAMS"
    PICNIC_BASKET1 = "PICNIC_BASKET1"
    PICNIC_BASKET2 = "PICNIC_BASKET2"

        

class OrderModel: # handles orders, positioning and data storage
    def __init__(self, product: str, OD: OrderDepth) -> None:
        self.product = product
        self.position : tuple[int, int] = (0, 0) # (quantity, price)
        self.Data: OrderDepth = OD
        
        # class OrderDepth:
        #     def __init__(self):
        #         self.buy_orders: Dict[int, int] = {}
        #         self.sell_orders: Dict[int, int] = {}

    def update(self, orderd: OrderDepth): 
        self.Data = orderd
    
    def liquidate(self) -> list[Order]:
        if self.position == (0, 0):
            print("No position to liquidate")
            return
        print("Liquidating, last price: ", self.position[1])
        return self.sendMarketOrder(-self.position[0])
    
    def sendOrder(self, quantity: int, price: int) -> list[Order]: 
        return [Order(self.product, price, quantity)]
    
    def sendMarketOrder(self, quantity: int) -> list[Order]:
        orders = []
        weighedprice = 0
        actualquantity = 0
        
        if quantity > 0:
            print("Buying: ", quantity)
            while not quantity == 0 and len(self.Data.buy_orders) > 0:
                best_ask = min(self.Data.buy_orders.keys())
                if self.Data.buy_orders[best_ask] >= quantity:
                    orders.append(Order(self.product, best_ask, quantity))
                    quantity = 0
                else:
                    orders.append(Order(self.product, best_ask, self.Data.buy_orders[best_ask]))
                    quantity -= self.Data.buy_orders[best_ask]
                    del self.Data.buy_orders[best_ask]
                    
        elif quantity < 0:
            print("Selling: ", abs(quantity))
            while not quantity == 0 and len(self.Data.sell_orders) > 0:
                best_bid = max(self.Data.sell_orders.keys())
                if self.Data.sell_orders[best_bid] >= abs(quantity):
                    orders.append(Order(self.product, best_bid, abs(quantity)))
                    quantity = 0
                else:
                    orders.append(Order(self.product, best_bid, self.Data.sell_orders[best_bid]))
                    quantity += self.Data.sell_orders[best_bid]
                    del self.Data.sell_orders[best_bid]
        
        for order in orders:
            if order.quantity > 0:
                weighedprice += order.price * order.quantity
                actualquantity += order.quantity
        
        weighedprice = weighedprice / actualquantity if actualquantity > 0 else 0
        self.position = (self.position[0] + quantity, weighedprice if self.position[0] + quantity != 0 else 0)

        
        return orders


class AlphaModel:
    def __init__(self, name: str, OD: OrderDepth = None, tradestate: TradingState = None) -> None:
        self.name = name
        self.Data = OD
        self.tradestate = tradestate
        
    def Update(self, state: TradingState):
        self.tradestate = state
    
    def genAlpha(self, **kwargs):
        pass
    
class MultiAlphaModel(AlphaModel):
    def __init__(self, name: str, OD: OrderDepth = None, tradestate: TradingState = None, **kwargs) -> None:
        super().__init__(name, OD, tradestate)
        self.orderModels: dict[str: OrderModel] = kwargs
    
    def genAlpha(self, **kwargs) -> list[Order]:
        pass


class Trader:
    def __init__(self) -> None:
        self.orderModels: dict[str: OrderModel] = {
            Product.RAINFOREST_RESIN: OrderModel(Product.RAINFOREST_RESIN, None),
            Product.KELP: OrderModel(Product.KELP, None),
            Product.SQUID_INK: OrderModel(Product.SQUID_INK, None),
            Product.CROISSANTS: OrderModel(Product.CROISSANTS, None),
            Product.DJEMBES: OrderModel(Product.DJEMBES, None),
            Product.JAMS: OrderModel(Product.JAMS, None),
            Product.PICNIC_BASKET1: OrderModel(Product.PICNIC_BASKET1, None),
            Product.PICNIC_BASKET2: OrderModel(Product.PICNIC_BASKET2, None)
        }
        self.pairTradeAlphaModel = MultiAlphaModel("PairTradeAlphaModel",
                                                  **{Product.CROISSANTS : self.orderModels[Product.CROISSANTS],
                                                     Product.DJEMBES : self.orderModels[Product.DJEMBES],
                                                     Product.JAMS : self.orderModels[Product.JAMS],
                                                     Product.PICNIC_BASKET1 : self.orderModels[Product.PICNIC_BASKET1]},
                                                  )
    
    def getDataHelper(self, order_depth: OrderDepth) -> tuple[int, int, int, int, int, int]: # Depreciated, for reference
        if len(order_depth.buy_orders) > 0 and len(order_depth.sell_orders) > 0:

            best_bid = max(order_depth.buy_orders.keys())
            best_ask = min(order_depth.sell_orders.keys())
            best_bid_volume = order_depth.buy_orders[best_bid]
            best_ask_volume = order_depth.sell_orders[best_ask]
            if best_bid_volume != 0 and best_ask_volume != 0:
                wmid = (best_bid * best_bid_volume + best_ask * abs(best_ask_volume)) / (best_bid_volume + abs(best_ask_volume))  
            else:
                wmid = None
            mid = (best_bid + best_ask) / 2
        return (best_bid, best_ask, best_bid_volume, best_ask_volume, wmid, mid)

    
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}

        ## Update
        for product in state.order_depths.keys():
            order_depth = state.order_depths[product]
            self.orderModels[product].update(order_depth)
        self.pairTradeAlphaModel.Update(state)
                        
            # result[product] = self.orderModels[product].sendMarketOrder(1)




                
                
                
        traderData = "SAMPLE" # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.

        conversions = 1 
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData
