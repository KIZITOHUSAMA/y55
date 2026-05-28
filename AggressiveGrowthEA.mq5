//+------------------------------------------------------------------+
//|                                         AggressiveGrowthEA.mq5    |
//|                                  Copyright 2024, Trading Robot   |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, Trading Robot"
#property link      "https://www.mql5.com"
#property version   "2.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- INPUT PARAMETERS
input double   InpRiskPercent = 2.0;       // Risk per trade (%)
input double   InpFibEntry    = 0.618;     // Fibonacci Entry Level
input double   InpFibStop     = 1.0;       // Fibonacci Stop Level (1.0 = Swing Low/High)
input int      InpMACD_Fast   = 12;        // MACD Fast
input int      InpMACD_Slow   = 26;        // MACD Slow
input int      InpMACD_Signal = 9;         // MACD Signal
input int      InpATR_Period  = 14;        // ATR Period for Trailing SL
input double   InpATR_Mult_SL = 2.0;       // ATR Multiplier for Trailing SL
input double   InpProfitToBE  = 5.0;       // Profit per lot to move to Break Even ($)
input int      InpMaxPositions = 10;       // Max positions per symbol
input int      InpMagicNumber = 123456;    // Magic Number

//--- GLOBAL VARIABLES
CTrade         trade;
CPositionInfo  posInfo;
CSymbolInfo    symInfo;

struct SymbolData
{
   string symbol;
   int hMACD, hATR;
   datetime lastM1Time;
   double cachedPOC;
   datetime lastPOCUpdate;

   // Performance caching
   double poiHigh, poiLow;
   datetime lastH1Time;
   double prev5mHigh, prev5mLow;
   datetime lastM5Time;
   double cachedATR;

   // SMC State
   bool poiTouched;
   ENUM_POSITION_TYPE poiType; // BUY if hit Low (demand), SELL if hit High (supply)
   double swingHigh;
   double swingLow;
   bool chochOccurred;
};
SymbolData Handles[];

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   trade.SetExpertMagicNumber(InpMagicNumber);

   int total = SymbolsTotal(true);
   ArrayResize(Handles, total);
   for(int i=0; i<total; i++)
   {
      Handles[i].symbol = SymbolName(i, true);
      Handles[i].hMACD  = iMACD(Handles[i].symbol, PERIOD_M5, InpMACD_Fast, InpMACD_Slow, InpMACD_Signal, PRICE_CLOSE);
      Handles[i].hATR   = iATR(Handles[i].symbol, PERIOD_CURRENT, InpATR_Period);
      Handles[i].lastM1Time = 0;
      Handles[i].cachedPOC = 0;
      Handles[i].lastPOCUpdate = 0;

      Handles[i].poiHigh = 0;
      Handles[i].poiLow = 0;
      Handles[i].lastH1Time = 0;
      Handles[i].prev5mHigh = 0;
      Handles[i].prev5mLow = 0;
      Handles[i].lastM5Time = 0;
      Handles[i].cachedATR = 0;

      Handles[i].poiTouched = false;
      Handles[i].chochOccurred = false;
      Handles[i].swingHigh = 0;
      Handles[i].swingLow = 0;
   }

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   for(int i=0; i<ArraySize(Handles); i++)
   {
      IndicatorRelease(Handles[i].hMACD);
      IndicatorRelease(Handles[i].hATR);
   }
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   for(int i=0; i<ArraySize(Handles); i++)
   {
      string symbol = Handles[i].symbol;

      // 0. Update performance caches
      datetime h1_time = iTime(symbol, PERIOD_H1, 0);
      if(Handles[i].lastH1Time != h1_time)
      {
         Handles[i].poiHigh = iHigh(symbol, PERIOD_H1, 1);
         Handles[i].poiLow  = iLow(symbol, PERIOD_H1, 1);
         Handles[i].lastH1Time = h1_time;
      }

      datetime m5_time = iTime(symbol, PERIOD_M5, 0);
      if(Handles[i].lastM5Time != m5_time)
      {
         Handles[i].prev5mHigh = iHigh(symbol, PERIOD_M5, 1);
         Handles[i].prev5mLow  = iLow(symbol, PERIOD_M5, 1);
         Handles[i].lastM5Time = m5_time;
      }

      Handles[i].cachedATR = GetATR(Handles[i].hATR, 1);

      // Update POC every hour
      if(Handles[i].lastPOCUpdate != h1_time)
      {
         Handles[i].cachedPOC = CalculatePOC(symbol, PERIOD_H1);
         Handles[i].lastPOCUpdate = h1_time;
      }

      // 1. Price Action Signal Logic
      UpdateSMCState(i);

      // 2. Entry Logic
      if(CountPositions(symbol) == 0)
      {
         CheckEntrySignal(i);
      }

      // 3. Add Positions on M1
      datetime currentM1 = iTime(symbol, PERIOD_M1, 0);
      if(currentM1 != Handles[i].lastM1Time)
      {
         if(Handles[i].lastM1Time != 0) AddTrendPosition(i);
         Handles[i].lastM1Time = currentM1;
      }
   }

   ManageExistingPositions();
}

//+------------------------------------------------------------------+
//| Detect POI (1H) and ChoCh (5M)                                   |
//+------------------------------------------------------------------+
void UpdateSMCState(int idx)
{
   string symbol = Handles[idx].symbol;

   // Use cached 1H POI (Recent Swing High/Low)
   double poiHigh = Handles[idx].poiHigh;
   double poiLow  = Handles[idx].poiLow;
   double currentPrice = SymbolInfoDouble(symbol, SYMBOL_BID);

   // Reset if price moves too far from potential POI
   if(!Handles[idx].poiTouched)
   {
      if(currentPrice >= poiHigh) { Handles[idx].poiTouched = true; Handles[idx].poiType = POSITION_TYPE_SELL; }
      else if(currentPrice <= poiLow) { Handles[idx].poiTouched = true; Handles[idx].poiType = POSITION_TYPE_BUY; }
   }

   // Detect ChoCh using cached 5M values
   if(Handles[idx].poiTouched && !Handles[idx].chochOccurred)
   {
      double prev5mHigh = Handles[idx].prev5mHigh;
      double prev5mLow  = Handles[idx].prev5mLow;

      if(Handles[idx].poiType == POSITION_TYPE_BUY) // Look for Bullish ChoCh
      {
         if(currentPrice > prev5mHigh)
         {
            Handles[idx].chochOccurred = true;
            Handles[idx].swingLow = poiLow; // Fib anchor low
            Handles[idx].swingHigh = currentPrice; // Fib anchor high
         }
      }
      else // Look for Bearish ChoCh
      {
         if(currentPrice < prev5mLow)
         {
            Handles[idx].chochOccurred = true;
            Handles[idx].swingHigh = poiHigh; // Fib anchor high
            Handles[idx].swingLow = currentPrice; // Fib anchor low
         }
      }
   }

   // Reset if trend fails (Price breaks Fib 1.0)
   if(Handles[idx].chochOccurred)
   {
      if(Handles[idx].poiType == POSITION_TYPE_BUY && currentPrice < Handles[idx].swingLow) ResetSMC(idx);
      else if(Handles[idx].poiType == POSITION_TYPE_SELL && currentPrice > Handles[idx].swingHigh) ResetSMC(idx);
   }
}

void ResetSMC(int idx)
{
   Handles[idx].poiTouched = false;
   Handles[idx].chochOccurred = false;
}

//+------------------------------------------------------------------+
//| Entry based on Fib Retracement + MACD + POC                      |
//+------------------------------------------------------------------+
void CheckEntrySignal(int idx)
{
   if(!Handles[idx].chochOccurred) return;

   string symbol = Handles[idx].symbol;
   double currentPrice = SymbolInfoDouble(symbol, SYMBOL_BID);
   double macd_main=0, macd_sig=0;
   GetMACD(Handles[idx].hMACD, macd_main, macd_sig, 1);

   double poc = Handles[idx].cachedPOC;

   if(Handles[idx].poiType == POSITION_TYPE_BUY)
   {
      // Calculate Fib Entry (61.8%)
      double entryLevel = Handles[idx].swingHigh - (Handles[idx].swingHigh - Handles[idx].swingLow) * InpFibEntry;

      if(currentPrice <= entryLevel && macd_main > macd_sig && poc > currentPrice)
      {
         double sl = Handles[idx].swingLow; // Stop at swing low
         OpenPosition(symbol, ORDER_TYPE_BUY, sl, poc);
         ResetSMC(idx); // Clear state after entry
      }
   }
   else
   {
      // Calculate Fib Entry (61.8%)
      double entryLevel = Handles[idx].swingLow + (Handles[idx].swingHigh - Handles[idx].swingLow) * InpFibEntry;

      if(currentPrice >= entryLevel && macd_main < macd_sig && (poc < currentPrice && poc > 0))
      {
         double sl = Handles[idx].swingHigh; // Stop at swing high
         OpenPosition(symbol, ORDER_TYPE_SELL, sl, poc);
         ResetSMC(idx); // Clear state after entry
      }
   }
}

//+------------------------------------------------------------------+
//| Add position on M1 candle close if Price Action is Bullish/Bearish|
//+------------------------------------------------------------------+
void AddTrendPosition(int idx)
{
   string symbol = Handles[idx].symbol;
   int posCount = CountPositions(symbol);
   if(posCount <= 0 || posCount >= InpMaxPositions) return;

   ENUM_POSITION_TYPE type = GetFirstPositionType(symbol);
   double m1_close = iClose(symbol, PERIOD_M1, 1);
   double m1_open  = iOpen(symbol, PERIOD_M1, 1);
   double poc = Handles[idx].cachedPOC;
   double atr = Handles[idx].cachedATR;

   if(type == POSITION_TYPE_BUY && m1_close > m1_open && m1_close < poc)
   {
      double price = SymbolInfoDouble(symbol, SYMBOL_ASK);
      OpenPosition(symbol, ORDER_TYPE_BUY, price - (atr * InpATR_Mult_SL), poc);
   }
   else if(type == POSITION_TYPE_SELL && m1_close < m1_open && (m1_close > poc && poc > 0))
   {
      double price = SymbolInfoDouble(symbol, SYMBOL_BID);
      OpenPosition(symbol, ORDER_TYPE_SELL, price + (atr * InpATR_Mult_SL), poc);
   }
}

//+------------------------------------------------------------------+
//| Manage existing positions (BE, Trailing, POC Exit)               |
//+------------------------------------------------------------------+
void ManageExistingPositions()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(posInfo.SelectByIndex(i))
      {
         if(posInfo.Magic() != InpMagicNumber) continue;

         string symbol = posInfo.Symbol();
         double profit = posInfo.Profit();
         double lots = posInfo.Volume();
         double entry = posInfo.PriceOpen();
         double currentSL = posInfo.StopLoss();
         double currentTP = posInfo.TakeProfit();

         if(!symInfo.Name(symbol)) continue;

         // 1. Break Even logic: $5 profit per lot
         if(profit / lots >= InpProfitToBE)
         {
            if(posInfo.PositionType() == POSITION_TYPE_BUY && (currentSL < entry || currentSL == 0))
               trade.PositionModify(posInfo.Ticket(), entry + symInfo.Point() * 10, currentTP);
            else if(posInfo.PositionType() == POSITION_TYPE_SELL && (currentSL > entry || currentSL == 0))
               trade.PositionModify(posInfo.Ticket(), entry - symInfo.Point() * 10, currentTP);
         }

         // 2. POC Update
         int idx = GetHandleIndex(symbol);
         if(idx != -1)
         {
            double poc = Handles[idx].cachedPOC;
            if(poc > 0 && MathAbs(currentTP - poc) > symInfo.Point() * 10)
               trade.PositionModify(posInfo.Ticket(), currentSL, poc);
         }

         // 3. ATR Trailing Stop
         if(idx != -1)
         {
            double atr = Handles[idx].cachedATR;
            if(posInfo.PositionType() == POSITION_TYPE_BUY)
            {
               double newSL = SymbolInfoDouble(symbol, SYMBOL_BID) - (atr * InpATR_Mult_SL);
               if(newSL > currentSL + symInfo.Point() * 10)
                  trade.PositionModify(posInfo.Ticket(), newSL, currentTP);
            }
            else
            {
               double newSL = SymbolInfoDouble(symbol, SYMBOL_ASK) + (atr * InpATR_Mult_SL);
               if(newSL < currentSL - symInfo.Point() * 10 || currentSL == 0)
                  trade.PositionModify(posInfo.Ticket(), newSL, currentTP);
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| POC Calculation (Volume Profile)                                 |
//+------------------------------------------------------------------+
double CalculatePOC(string symbol, ENUM_TIMEFRAMES timeframe)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(symbol, timeframe, 1, 1, rates) <= 0) return 0;

   datetime startTime = rates[0].time;
   datetime endTime = startTime + PeriodSeconds(timeframe);
   MqlRates m1_rates[];
   ArraySetAsSeries(m1_rates, true);
   int copied = CopyRates(symbol, PERIOD_M1, startTime, endTime, m1_rates);
   if(copied <= 0) return (rates[0].high + rates[0].low) / 2.0;

   double step = SymbolInfoDouble(symbol, SYMBOL_POINT) * 10;
   if(step == 0) step = 0.0001;
   double minPrice = rates[0].low;
   double maxPrice = rates[0].high;
   int bins = (int)((maxPrice - minPrice) / step) + 1;
   if(bins <= 0) bins = 1;
   double volumes[];
   ArrayResize(volumes, bins);
   ArrayInitialize(volumes, 0);
   for(int i = 0; i < copied; i++)
   {
      int bin = (int)((m1_rates[i].close - minPrice) / step);
      if(bin >= 0 && bin < bins) volumes[bin] += (double)m1_rates[i].tick_volume;
   }
   int maxBin = 0; double maxV = 0;
   for(int i = 0; i < bins; i++) if(volumes[i] > maxV) { maxV = volumes[i]; maxBin = i; }
   return minPrice + (maxBin * step);
}

//+------------------------------------------------------------------+
//| Trade Execution Helpers                                          |
//+------------------------------------------------------------------+
void OpenPosition(string symbol, ENUM_ORDER_TYPE type, double sl, double tp)
{
   double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(symbol, SYMBOL_ASK) : SymbolInfoDouble(symbol, SYMBOL_BID);
   double slDist = MathAbs(price - sl);
   if(slDist == 0) slDist = 100 * SymbolInfoDouble(symbol, SYMBOL_POINT);
   double lotSize = CalculateLotSize(symbol, slDist);
   trade.PositionOpen(symbol, type, lotSize, price, sl, tp, "Price Action Growth");
}

double CalculateLotSize(string symbol, double slDistInPrice)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * (InpRiskPercent / 100.0);
   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);
   if(slDistInPrice == 0 || tickValue == 0 || tickSize == 0) return SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double lotSize = riskAmount / ((slDistInPrice / tickSize) * tickValue);
   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   if(lotSize < minLot) lotSize = minLot;
   if(lotSize > maxLot) lotSize = maxLot;
   return lotSize;
}

int GetHandleIndex(string symbol)
{
   for(int i=0; i<ArraySize(Handles); i++) if(Handles[i].symbol == symbol) return i;
   return -1;
}

void GetMACD(int handle, double &main, double &sig, int shift)
{
   double main_buf[], sig_buf[];
   if(CopyBuffer(handle, 0, shift, 1, main_buf) > 0 && CopyBuffer(handle, 1, shift, 1, sig_buf) > 0)
   { main = main_buf[0]; sig = sig_buf[0]; }
}

double GetATR(int handle, int shift)
{
   double buffer[];
   if(CopyBuffer(handle, 0, shift, 1, buffer) > 0) return buffer[0];
   return 0;
}

int CountPositions(string symbol)
{
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(posInfo.SelectByIndex(i) && posInfo.Symbol() == symbol && posInfo.Magic() == InpMagicNumber) count++;
   }
   return count;
}

ENUM_POSITION_TYPE GetFirstPositionType(string symbol)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(posInfo.SelectByIndex(i) && posInfo.Symbol() == symbol && posInfo.Magic() == InpMagicNumber) return posInfo.PositionType();
   }
   return -1;
}
