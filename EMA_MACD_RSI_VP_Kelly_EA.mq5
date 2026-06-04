//+------------------------------------------------------------------+
//|                                  EMA_MACD_RSI_VP_Kelly_EA.mq5    |
//|                                  Copyright 2026, Jules           |
//|                                  https://www.mql5.com            |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Jules"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property strict

//--- Includes
#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\OrderInfo.mqh>

//--- Input parameters
input int      InpEMA_Fast          = 5;          // Fast EMA Period
input int      InpEMA_Slow          = 9;          // Slow EMA Period
input bool     InpUseMACD           = false;      // Use MACD Filter
input int      InpMACD_Fast         = 12;         // MACD Fast EMA
input int      InpMACD_Slow         = 26;         // MACD Slow EMA
input int      InpMACD_Signal       = 9;          // MACD Signal Period
input bool     InpUseRSI            = false;      // Use RSI Filter
input int      InpRSI_Period        = 14;         // RSI Period
input double   InpRSI_Level         = 50;         // RSI Level (Entry if > or <)
input int      InpVP_Lookback       = 60;         // Volume Profile Lookback (candles)
input int      InpVP_Bins           = 50;         // Volume Profile Bins
input double   InpKelly_P           = 0.5;        // Kelly Win Probability (p)
input double   InpKelly_B           = 5.0;        // Kelly Reward-to-Risk (b)
input double   InpKelly_Fraction    = 0.01;       // Fractional Kelly (Multiplier)
input int      InpMaxOrders         = 20;         // Max Open Positions/Orders
input int      InpTrailingStopPips  = 10;         // Trailing Stop (Pips)
input int      InpBreakevenPips     = 10;         // Breakeven Start (Pips)
input double   InpPartialCloseRatio = 2.0;        // Partial Close RR Ratio
input double   InpFullCloseRatio    = 5.0;        // Full Close RR Ratio

//--- Global variables
int      handleEMA_Fast;
int      handleEMA_Slow;
int      handleMACD;
int      handleRSI;
CTrade   trade;
CSymbolInfo sym;
CPositionInfo pos;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   handleEMA_Fast = iMA(_Symbol, _Period, InpEMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
   handleEMA_Slow = iMA(_Symbol, _Period, InpEMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
   handleMACD     = iMACD(_Symbol, _Period, InpMACD_Fast, InpMACD_Slow, InpMACD_Signal, PRICE_CLOSE);
   handleRSI      = iRSI(_Symbol, _Period, InpRSI_Period, PRICE_CLOSE);

   if(handleEMA_Fast == INVALID_HANDLE || handleEMA_Slow == INVALID_HANDLE ||
      handleMACD == INVALID_HANDLE || handleRSI == INVALID_HANDLE)
   {
      Print("Error creating indicator handles");
      return(INIT_FAILED);
   }

   sym.Name(_Symbol);
   trade.SetExpertMagicNumber(123456);

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(handleEMA_Fast);
   IndicatorRelease(handleEMA_Slow);
   IndicatorRelease(handleMACD);
   IndicatorRelease(handleRSI);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // 1. Manage existing positions (Trailing Stop, Partial TP, Breakeven, Reversal)
   ManagePositions();

   // 2. Check for new signals only on a new bar to avoid multiple entries
   if(!IsNewBar()) return;

   // 3. Check max orders (Positions + Pending)
   if(PositionsTotal() + OrdersTotal() >= InpMaxOrders) return;

   // 4. Get Indicators
   double emaFast[], emaSlow[], macdMain[], macdSignal[], rsiVal[];
   ArraySetAsSeries(emaFast, true);
   ArraySetAsSeries(emaSlow, true);
   ArraySetAsSeries(macdMain, true);
   ArraySetAsSeries(macdSignal, true);
   ArraySetAsSeries(rsiVal, true);

   if(CopyBuffer(handleEMA_Fast, 0, 0, 2, emaFast) < 2) return;
   if(CopyBuffer(handleEMA_Slow, 0, 0, 2, emaSlow) < 2) return;
   if(CopyBuffer(handleMACD, 0, 0, 2, macdMain) < 2) return;
   if(CopyBuffer(handleMACD, 1, 0, 2, macdSignal) < 2) return;
   if(CopyBuffer(handleRSI, 0, 0, 2, rsiVal) < 2) return;

   // 5. Volume Profile calculation
   double poc, vah, val;
   if(!CalculateVolumeProfile(poc, vah, val)) return;

   // 6. Signal Logic (EMA Crossover is mandatory, others optional)
   bool emaLong  = (emaFast[1] > emaSlow[1]) && (emaFast[2] <= emaSlow[2]);
   bool macdLong = !InpUseMACD || (macdMain[1] > macdSignal[1]);
   bool rsiLong  = !InpUseRSI  || (rsiVal[1] > InpRSI_Level);
   bool longCondition = emaLong && macdLong && rsiLong;

   bool emaShort  = (emaFast[1] < emaSlow[1]) && (emaFast[2] >= emaSlow[2]);
   bool macdShort = !InpUseMACD || (macdMain[1] < macdSignal[1]);
   bool rsiShort  = !InpUseRSI  || (rsiVal[1] < InpRSI_Level);
   bool shortCondition = emaShort && macdShort && rsiShort;

   // 7. Calculate Lot Size using Kelly
   double kellyRisk = InpKelly_P - (1.0 - InpKelly_P) / InpKelly_B;
   kellyRisk *= InpKelly_Fraction;
   if(kellyRisk <= 0) kellyRisk = 0.01; // Fallback to 1% if Kelly is negative

   // 8. Place Market and Limit Orders
   if(longCondition)
   {
      double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      double sl = val; // Outside value area
      if(sl >= currentPrice) sl = currentPrice - 100 * _Point; // Safety

      // Market Order (50% of Kelly Risk)
      double lotMarket = CalculateLotSize(kellyRisk * 0.5, currentPrice, sl);
      double riskM = currentPrice - sl;
      double tpM = currentPrice + InpFullCloseRatio * riskM;
      trade.Buy(lotMarket, _Symbol, currentPrice, sl, tpM, "EMA VP MARKET BUY");

      // Limit Order at POC (50% of Kelly Risk)
      if(poc < currentPrice)
      {
         if(sl >= poc) sl = poc - 100 * _Point;
         double lotLimit = CalculateLotSize(kellyRisk * 0.5, poc, sl);
         double riskL = poc - sl;
         double tpL = poc + InpFullCloseRatio * riskL;
         trade.BuyLimit(lotLimit, poc, _Symbol, sl, tpL, ORDER_TIME_GTC, 0, "EMA VP LIMIT BUY");
      }
   }
   else if(shortCondition)
   {
      double currentPrice = SymbolInfoDouble(_Symbol, SYMBOL_BID);
      double sl = vah; // Outside value area
      if(sl <= currentPrice) sl = currentPrice + 100 * _Point; // Safety

      // Market Order (50% of Kelly Risk)
      double lotMarket = CalculateLotSize(kellyRisk * 0.5, currentPrice, sl);
      double riskM = sl - currentPrice;
      double tpM = currentPrice - InpFullCloseRatio * riskM;
      trade.Sell(lotMarket, _Symbol, currentPrice, sl, tpM, "EMA VP MARKET SELL");

      // Limit Order at POC (50% of Kelly Risk)
      if(poc > currentPrice)
      {
         if(sl <= poc) sl = poc + 100 * _Point;
         double lotLimit = CalculateLotSize(kellyRisk * 0.5, poc, sl);
         double riskL = sl - poc;
         double tpL = poc - InpFullCloseRatio * riskL;
         trade.SellLimit(lotLimit, poc, _Symbol, sl, tpL, ORDER_TIME_GTC, 0, "EMA VP LIMIT SELL");
      }
   }
}

//+------------------------------------------------------------------+
//| Manage existing positions                                        |
//+------------------------------------------------------------------+
void ManagePositions()
{
   double point_mult = (_Digits == 3 || _Digits == 5) ? 10.0 : 1.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(pos.SelectByTicket(ticket))
      {
         if(pos.Symbol() == _Symbol && pos.Magic() == 123456)
         {
            double currentPrice = (pos.PositionType() == POSITION_TYPE_BUY) ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
            double openPrice = pos.PriceOpen();
            double sl = pos.StopLoss();
            double volume = pos.Volume();

            // A. Signal Reversal Check
            if(ShouldCloseOnReversal(pos.PositionType()))
            {
               trade.PositionClose(pos.Ticket());
               continue;
            }

            // B. Partial Close (50% at 1:2 RR)
            // We use the TP to back-calculate the initial risk: risk = (tp - openPrice) / 5
            double tp = pos.TakeProfit();

            double initialRisk = MathAbs(tp - openPrice) / InpFullCloseRatio;
            bool partialDone = (MathAbs(sl - openPrice) < _Point && sl != 0);

            if(!partialDone && initialRisk > 0)
            {
               bool takePartial = false;
               if(pos.PositionType() == POSITION_TYPE_BUY && currentPrice >= openPrice + InpPartialCloseRatio * initialRisk) takePartial = true;
               if(pos.PositionType() == POSITION_TYPE_SELL && currentPrice <= openPrice - InpPartialCloseRatio * initialRisk) takePartial = true;

               if(takePartial)
               {
                  double stepVol = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
                  int digits = (stepVol > 0) ? (int)-MathLog10(stepVol) : 2;
                  double closeVol = NormalizeDouble(volume / 2.0, digits);
                  if(trade.PositionClosePartial(pos.Ticket(), closeVol))
                  {
                     trade.PositionModify(pos.Ticket(), openPrice, tp);
                     partialDone = true;
                  }
               }
            }

            // C. Full Close at 1:5 RR (Handled by TP)

            // D. Trailing Stop
            if(InpTrailingStopPips > 0 && partialDone)
            {
               double tsPoints = InpTrailingStopPips * point_mult * _Point;
               if(pos.PositionType() == POSITION_TYPE_BUY)
               {
                  double newSL = NormalizeDouble(currentPrice - tsPoints, _Digits);
                  if(newSL > sl + point_mult * _Point) trade.PositionModify(pos.Ticket(), newSL, 0);
               }
               else
               {
                  double newSL = NormalizeDouble(currentPrice + tsPoints, _Digits);
                  if(sl == 0 || newSL < sl - point_mult * _Point) trade.PositionModify(pos.Ticket(), newSL, 0);
               }
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Check if signal reversed                                         |
//+------------------------------------------------------------------+
bool ShouldCloseOnReversal(ENUM_POSITION_TYPE type)
{
   double emaFast[], emaSlow[];
   ArraySetAsSeries(emaFast, true);
   ArraySetAsSeries(emaSlow, true);
   if(CopyBuffer(handleEMA_Fast, 0, 0, 2, emaFast) < 2) return false;
   if(CopyBuffer(handleEMA_Slow, 0, 0, 2, emaSlow) < 2) return false;

   if(type == POSITION_TYPE_BUY && emaFast[1] < emaSlow[1]) return true;
   if(type == POSITION_TYPE_SELL && emaFast[1] > emaSlow[1]) return true;

   return false;
}

//+------------------------------------------------------------------+
//| Calculate Volume Profile                                         |
//+------------------------------------------------------------------+
bool CalculateVolumeProfile(double &poc, double &vah, double &val)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, _Period, 0, InpVP_Lookback, rates) < InpVP_Lookback) return false;

   double high = rates[0].high;
   double low = rates[0].low;
   for(int i=1; i<InpVP_Lookback; i++)
   {
      if(rates[i].high > high) high = rates[i].high;
      if(rates[i].low < low) low = rates[i].low;
   }

   double range = high - low;
   if(range <= 0) return false;
   double binSize = range / InpVP_Bins;
   double volumes[];
   ArrayResize(volumes, InpVP_Bins);
   ArrayInitialize(volumes, 0);

   long totalVolume = 0;
   for(int i=0; i<InpVP_Lookback; i++)
   {
      int bin = (int)((rates[i].close - low) / binSize);
      if(bin >= InpVP_Bins) bin = InpVP_Bins - 1;
      if(bin < 0) bin = 0;
      volumes[bin] += (double)rates[i].tick_volume;
      totalVolume += rates[i].tick_volume;
   }

   int maxBin = 0;
   double maxVol = 0;
   for(int i=0; i<InpVP_Bins; i++)
   {
      if(volumes[i] > maxVol)
      {
         maxVol = volumes[i];
         maxBin = i;
      }
   }

   poc = low + (maxBin * binSize) + (binSize / 2.0);

   // Value Area (70%)
   double targetVol = totalVolume * 0.7;
   double currentVol = volumes[maxBin];
   int upper = maxBin;
   int lower = maxBin;

   while(currentVol < targetVol && (upper < InpVP_Bins - 1 || lower > 0))
   {
      double upVol = (upper < InpVP_Bins - 1) ? volumes[upper + 1] : 0;
      double downVol = (lower > 0) ? volumes[lower - 1] : 0;

      if(upVol >= downVol && upper < InpVP_Bins - 1)
      {
         upper++;
         currentVol += upVol;
      }
      else if(lower > 0)
      {
         lower--;
         currentVol += downVol;
      }
      else break;
   }

   vah = low + (upper * binSize) + binSize;
   val = low + (lower * binSize);

   return true;
}

//+------------------------------------------------------------------+
//| Calculate Lot Size based on risk                                 |
//+------------------------------------------------------------------+
double CalculateLotSize(double riskPercent, double entry, double sl)
{
   double balance = AccountInfoDouble(ACCOUNT_EQUITY);
   double riskAmount = balance * riskPercent;
   double tickValue = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);

   double pointsAtRisk = MathAbs(entry - sl) / tickSize;
   if(pointsAtRisk <= 0) return 0.01;

   double lotSize = riskAmount / (pointsAtRisk * tickValue);

   double minLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double stepLot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   lotSize = MathFloor(lotSize / stepLot) * stepLot;
   if(lotSize < minLot) lotSize = minLot;
   if(lotSize > maxLot) lotSize = maxLot;

   return lotSize;
}

//+------------------------------------------------------------------+
//| Helper for new bar detection                                     |
//+------------------------------------------------------------------+
bool IsNewBar()
{
   static datetime lastTime = 0;
   datetime currentTime = iTime(_Symbol, _Period, 0);
   if(currentTime != lastTime)
   {
      lastTime = currentTime;
      return true;
   }
   return false;
}
