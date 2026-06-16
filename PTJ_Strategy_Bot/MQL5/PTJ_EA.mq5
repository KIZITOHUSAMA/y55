//+------------------------------------------------------------------+
//|                                              PTJ_Hybrid_Bot.mq5 |
//|                                  Copyright 2026, Jules (Bolt)    |
//|                                             https://example.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Jules (Bolt)"
#property link      "https://example.com"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- Input Parameters
input double   InpRiskPercent = 1.0;       // Risk Percent per Trade
input int      InpSMA_Period  = 200;       // Trend Filter SMA Period
input ENUM_TIMEFRAMES InpTrendTF = PERIOD_M15; // Trend Filter Timeframe
input int      InpRR_Ratio    = 5;         // Final Reward-to-Risk Ratio
input double   InpPartialRR   = 3.0;       // Partial Close RR
input double   InpPartialVol  = 0.5;       // Partial Close Volume %
input int      InpAsiaEndHour = 8;         // Asia Session End (Accumulation)
input int      InpLondonEndHour = 16;      // London Session End
input int      InpNYEndHour     = 21;      // NY Session End

//--- Global Variables
CTrade         trade;
CPositionInfo  posInfo;
CSymbolInfo    symInfo;
int            handleSMA;
double         bufferSMA[];

struct SessionRange {
    double high;
    double low;
    bool   set;
};

SessionRange asiaRange;
bool partialClosed = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    if(!symInfo.Name(_Symbol)) return INIT_FAILED;

    handleSMA = iMA(_Symbol, InpTrendTF, InpSMA_Period, 0, MODE_SMA, PRICE_CLOSE);
    if(handleSMA == INVALID_HANDLE) return INIT_FAILED;

    ArraySetAsSeries(bufferSMA, true);

    trade.SetExpertMagicNumber(123456);

    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    IndicatorRelease(handleSMA);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
    UpdateAsiaRange();
    ManageTrades();

    if(!CanTradeSession()) return;
    if(PositionsTotal() > 0) return; // PTJ: No averaging down, one trade at a time

    CheckEntrySignals();
}

//+------------------------------------------------------------------+
//| Logic to update the Asia session range (Accumulation)            |
//+------------------------------------------------------------------+
void UpdateAsiaRange()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);

    if(dt.hour == 0 && dt.min == 0) {
        asiaRange.high = 0;
        asiaRange.low = 999999;
        asiaRange.set = false;
    }

    if(dt.hour < InpAsiaEndHour) {
        double high = iHigh(_Symbol, PERIOD_M5, 0);
        double low = iLow(_Symbol, PERIOD_M5, 0);
        if(high > asiaRange.high) asiaRange.high = high;
        if(low < asiaRange.low) asiaRange.low = low;
        asiaRange.set = true;
    }
}

//+------------------------------------------------------------------+
//| Session check for best volume (London / NY)                      |
//+------------------------------------------------------------------+
bool CanTradeSession()
{
    MqlDateTime dt;
    TimeToStruct(TimeCurrent(), dt);
    // Trade during London and NY sessions after Asia accumulation
    return (dt.hour >= InpAsiaEndHour && dt.hour < InpNYEndHour);
}

//+------------------------------------------------------------------+
//| Signal check: SMA Filter + AMD + CHOCH                           |
//+------------------------------------------------------------------+
void CheckEntrySignals()
{
    if(!asiaRange.set) return;

    // 1. Trend Filter: 200 SMA on M15
    if(CopyBuffer(handleSMA, 0, 0, 1, bufferSMA) <= 0) return;
    double sma = bufferSMA[0];
    double closeM15 = iClose(_Symbol, InpTrendTF, 0);

    bool trendUp = closeM15 > sma;
    bool trendDown = closeM15 < sma;

    // 2. AMD & CHOCH
    // For Buy: Manipulation (price went below Asia Low) then CHOCH (break above M5 high)
    // For Sell: Manipulation (price went above Asia High) then CHOCH (break below M5 low)

    double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);

    if(trendUp) {
        // Did we have manipulation below Asia Low?
        bool manipulated = iLow(_Symbol, PERIOD_M5, 1) < asiaRange.low;
        if(manipulated) {
            // CHOCH: Break of recent M5 high
            double recentHigh = iHigh(_Symbol, PERIOD_M5, 1);
            if(currentPrice > recentHigh) {
                ExecuteTrade(ORDER_TYPE_BUY, recentHigh - iLow(_Symbol, PERIOD_M5, 1));
            }
        }
    }
    else if(trendDown) {
        // Did we have manipulation above Asia High?
        bool manipulated = iHigh(_Symbol, PERIOD_M5, 1) > asiaRange.high;
        if(manipulated) {
            // CHOCH: Break of recent M5 low
            double recentLow = iLow(_Symbol, PERIOD_M5, 1);
            if(currentPrice < recentLow) {
                ExecuteTrade(ORDER_TYPE_SELL, iHigh(_Symbol, PERIOD_M5, 1) - recentLow);
            }
        }
    }
}

//+------------------------------------------------------------------+
//| Execute trade with risk management                               |
//+------------------------------------------------------------------+
void ExecuteTrade(ENUM_ORDER_TYPE type, double stopDist)
{
    double balance = AccountInfoDouble(ACCOUNT_BALANCE);
    double riskAmount = balance * (InpRiskPercent / 100.0);

    double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
    double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);

    if(stopDist <= 0) stopDist = 100 * _Point; // Default if something's wrong

    double lot = riskAmount / (stopDist / tickSize * tickValue);
    lot = MathMin(lot, symInfo.VolumeMax());
    lot = MathMax(lot, symInfo.VolumeMin());
    lot = NormalizeDouble(lot, 2);

    double sl, tp;
    double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
    double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);

    if(type == ORDER_TYPE_BUY) {
        sl = bid - stopDist;
        tp = bid + (stopDist * InpRR_Ratio);
        trade.Buy(lot, _Symbol, ask, sl, tp, "PTJ Hybrid Buy");
    } else {
        sl = ask + stopDist;
        tp = ask - (stopDist * InpRR_Ratio);
        trade.Sell(lot, _Symbol, bid, sl, tp, "PTJ Hybrid Sell");
    }
    partialClosed = false;
}

//+------------------------------------------------------------------+
//| Manage open trades: Partial close & Breakeven                    |
//+------------------------------------------------------------------+
void ManageTrades()
{
    for(int i = PositionsTotal() - 1; i >= 0; i--) {
        if(posInfo.SelectByIndex(i)) {
            if(posInfo.Symbol() == _Symbol && posInfo.Magic() == 123456) {
                double entry = posInfo.PriceOpen();
                double sl = posInfo.StopLoss();
                double tp = posInfo.TakeProfit();
                double current = posInfo.PriceCurrent();

                double initialRisk = MathAbs(entry - sl);
                if(initialRisk == 0) continue;

                double currentRR = MathAbs(current - entry) / initialRisk;

                // Partial Close at 1:3 RR
                if(!partialClosed && currentRR >= InpPartialRR) {
                    double closeVol = posInfo.Volume() * InpPartialVol;
                    if(trade.PositionClosePartial(posInfo.Ticket(), closeVol)) {
                        partialClosed = true;
                        // Move to Breakeven
                        trade.PositionModify(posInfo.Ticket(), entry, tp);
                        Print("Partial close at 1:3 RR. Moved to Breakeven.");
                    }
                }
            }
        }
    }
}
//+------------------------------------------------------------------+
