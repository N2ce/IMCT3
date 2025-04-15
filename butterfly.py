from typing import Dict, List, Any
import json
from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
import math

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
    VOLCANIC_ROCK = "VOLCANIC_ROCK"
    VOLCANIC_ROCK_VOUCHER_9500 = "VOLCANIC_ROCK_VOUCHER_9500"
    VOLCANIC_ROCK_VOUCHER_9750 = "VOLCANIC_ROCK_VOUCHER_9750"
    VOLCANIC_ROCK_VOUCHER_10000 = "VOLCANIC_ROCK_VOUCHER_10000"
    VOLCANIC_ROCK_VOUCHER_10250 = "VOLCANIC_ROCK_VOUCHER_10250"
    VOLCANIC_ROCK_VOUCHER_10500 = "VOLCANIC_ROCK_VOUCHER_10500"

        

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

    def getDataHelper(self) -> tuple[int, int, int, int, int, int]:
        if len(self.Data.buy_orders) > 0 and len(self.Data.sell_orders) > 0:

            best_bid = max(self.Data.buy_orders.keys())
            best_ask = min(self.Data.sell_orders.keys())
            best_bid_volume = self.Data.buy_orders[best_bid]
            best_ask_volume = self.Data.sell_orders[best_ask]
            if best_bid_volume != 0 and best_ask_volume != 0:
                wmid = (best_bid * best_bid_volume + best_ask * abs(best_ask_volume)) / (best_bid_volume + abs(best_ask_volume))  
            else:
                wmid = None
            mid = (best_bid + best_ask) / 2
        return (best_bid, best_ask, best_bid_volume, best_ask_volume, wmid, mid)
            
    


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

class ButterflyAlphaModel(AlphaModel):
    def __init__(self, name: str, ticker, OD: OrderDepth = None, tradestate: TradingState = None, **kwargs) -> None:
        super().__init__(name, OD, tradestate)
        self.ticker = ticker
        self.orderModels: dict[str: OrderModel] = kwargs
        self.parabola = [4.11060503, 0.00526344, 0.0098111]
        self.IV = [0.0, 0.0, 0.0, 0.0, 0.0]
        self.delta = [0.0, 0.0, 0.0, 0.0, 0.0]
    def norm_cdf(self, x):
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    def bs_call_price(self, S, K, T, sigma, r=0.0):
        # Handle corner cases where time or volatility is essentially zero.
        if T <= 0 or sigma <= 0:
            return max(0.0, S - K * math.exp(-r * T))
        
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        price = S * self.norm_cdf(d1) - K * math.exp(-r * T) * self.norm_cdf(d2)
        return price
    
    def black_scholes_implied_vol(self, S, V, K, T, r=0.0, tol=1e-6, max_iterations=100):

        sigma = 0.2  # initial guess (20% annualized volatility)
        
        for i in range(max_iterations):
            price = self.bs_call_price(S, K, T, sigma, r)
            diff = price - V  # error between the Black–Scholes price and observed price
            if abs(diff) < tol:
                return sigma
            
            # Vega: sensitivity of the option price to volatility.
            d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
            vega = S * math.sqrt(T) * (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1 ** 2)
            if vega == 0:
                break
            sigma -= diff / vega
        
        return sigma
    
    def compute_delta(self, S, K, T, sigma, r=0.0):
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        delta = self.norm_cdf(d1)
        return delta
        
    # def compute_iv(df):
    #     """
    #     Given a DataFrame with columns:
    #         'timestamp', 'mid_price', 'mid_price_9500', 'mid_price_9750', 
    #         'mid_price_10000', 'mid_price_10250', 'mid_price_10500'
        
    #     This function computes the implied volatility for each call option
    #     (assuming expiration in 7 days, TTE = 7/365) and returns a new DataFrame 
    #     with columns: 'timestamp', 'IV9500', 'IV9750', 'IV10000', 'IV10250', 'IV10500'
    #     """
    #     # Set time-to-expiry in years (7 days to expiry)
    #     TTE = 7 / 365.0
        
    #     # Define strikes and the corresponding option mid price column names.
    #     strikes = {
    #         9500: 'mid_price_9500',
    #         9750: 'mid_price_9750',
    #         10000: 'mid_price_10000',
    #         10250: 'mid_price_10250',
    #         10500: 'mid_price_10500'
    #     }
        
    #     # Create an output DataFrame with the timestamp column.
    #     result = pd.DataFrame({'timestamp': df['timestamp']})
        
    #     # Compute the implied volatility for each option strike.
    #     for strike, col_name in strikes.items():
    #         iv_col_name = 'IV' + str(strike)
            
    #         # Apply the implied volatility function row-wise.
    #         result[iv_col_name] = df.apply(
    #             lambda row: black_scholes_implied_vol(
    #                 S=row['mid_price'],    # underlying price at time t
    #                 V=row[col_name],       # observed option (voucher) mid price
    #                 K=strike,              # strike price
    #                 T=TTE
    #             ), axis=1
    #         )
        
    #     return result
    
    
    def Update(self, state: TradingState):
        self.tradestate = state
        _,_,_,_,_,umid= self.ticker.getDataHelper()
        keys = list(self.orderModels.keys())
        for i in range(0, 5):
            _,_,_,_,_,mid= self.orderModels[self.ticker].getDataHelper()
            self.IV[i] = self.black_scholes_implied_vol(umid, mid, int(keys[0].split('_')[-1]), 5/365)

        
        
        
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
        # self.pairTradeAlphaModel = MultiAlphaModel("PairTradeAlphaModel",
        #                                           **{Product.CROISSANTS : self.orderModels[Product.CROISSANTS],
        #                                              Product.DJEMBES : self.orderModels[Product.DJEMBES],
        #                                              Product.JAMS : self.orderModels[Product.JAMS],
        #                                              Product.PICNIC_BASKET1 : self.orderModels[Product.PICNIC_BASKET1]},
        #                                           )
        self.butterflyAlphaModel = ButterflyAlphaModel("ButterflyAlphaModel",
                                                        Product.VOLCANIC_ROCK,
                                                        **{Product.VOLCANIC_ROCK_VOUCHER_9500 : self.orderModels[Product.VOLCANIC_ROCK_VOUCHER_9500],
                                                             Product.VOLCANIC_ROCK_VOUCHER_9750 : self.orderModels[Product.VOLCANIC_ROCK_VOUCHER_9750],
                                                             Product.VOLCANIC_ROCK_VOUCHER_10000 : self.orderModels[Product.VOLCANIC_ROCK_VOUCHER_10000],
                                                             Product.VOLCANIC_ROCK_VOUCHER_10250 : self.orderModels[Product.VOLCANIC_ROCK_VOUCHER_10250],
                                                             Product.VOLCANIC_ROCK_VOUCHER_10500 : self.orderModels[Product.VOLCANIC_ROCK_VOUCHER_10500]},
                                                        )
    
    

    
    def run(self, state: TradingState) -> Dict[str, List[Order]]:
        result = {}

        ## Update
        for product in state.order_depths.keys():
            order_depth = state.order_depths[product]
            self.orderModels[product].update(order_depth)
        self.butterflyAlphaModel.Update(state)
                        
            # result[product] = self.orderModels[product].sendMarketOrder(1)




                
                
                
        traderData = "SAMPLE" # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.

        conversions = 1 
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData
