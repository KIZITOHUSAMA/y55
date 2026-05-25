//+------------------------------------------------------------------+
//|                                         AggressiveGrowthEA.mq5    |
//|                                  Copyright 2024, Trading Robot   |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
#property copyright "Copyright 2024, Trading Robot"
#property link      "https://www.mql5.com"
#property version   "1.10"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\SymbolInfo.mqh>

//--- INPUT PARAMETERS
input double   InpRiskPercent = 2.0;       // Risk per trade (%)
input int      InpEMA_Fast    = 9;         // Fast EMA
input int      InpEMA_Med     = 21;        // Medium EMA
input int      InpEMA_Slow    = 50;        // Slow EMA
input int      InpMACD_Fast   = 12;        // MACD Fast
input int      InpMACD_Slow   = 26;        // MACD Slow
input int      InpMACD_Signal = 9;         // MACD Signal
input int      InpATR_Period  = 14;        // ATR Period for SL/TP
input double   InpATR_Mult_SL = 2.0;       // ATR Multiplier for SL
input double   InpATR_Mult_TP = 4.0;       // ATR Multiplier for TP
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
   int hEMA9, hEMA21, hEMA50, hMACD, hATR;
   datetime lastM1Time;
   double cachedPOC;
   datetime lastPOCUpdate;
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
      Handles[i].hEMA9  = iMA(Handles[i].symbol, PERIOD_CURRENT, InpEMA_Fast, 0, MODE_EMA, PRICE_CLOSE);
      Handles[i].hEMA21 = iMA(Handles[i].symbol, PERIOD_CURRENT, InpEMA_Med, 0, MODE_EMA, PRICE_CLOSE);
      Handles[i].hEMA50 = iMA(Handles[i].symbol, PERIOD_CURRENT, InpEMA_Slow, 0, MODE_EMA, PRICE_CLOSE);
      Handles[i].hMACD  = iMACD(Handles[i].symbol, PERIOD_CURRENT, InpMACD_Fast, InpMACD_Slow, InpMACD_Signal, PRICE_CLOSE);
      Handles[i].hATR   = iATR(Handles[i].symbol, PERIOD_CURRENT, InpATR_Period);
      Handles[i].lastM1Time = 0;
      Handles[i].cachedPOC = 0;
      Handles[i].lastPOCUpdate = 0;
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
      IndicatorRelease(Handles[i].hEMA9);
      IndicatorRelease(Handles[i].hEMA21);
      IndicatorRelease(Handles[i].hEMA50);
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
      if(!SymbolSelect(symbol, true)) continue;

      // Update POC every hour
      datetime hourStart = iTime(symbol, PERIOD_H1, 0);
      if(Handles[i].lastPOCUpdate != hourStart)
      {
         Handles[i].cachedPOC = CalculatePOC(symbol, PERIOD_H1);
         Handles[i].lastPOCUpdate = hourStart;
      }

      // Check for first entry
      if(CountPositions(symbol) == 0)
      {
         CheckEntrySignal(i);
      }

      // Check for M1 candle close to add positions
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
//| Check indicators for Buy/Sell signals                            |
//+------------------------------------------------------------------+
void CheckEntrySignal(int idx)
{
   string symbol = Handles[idx].symbol;
   double ema9 = GetEMA(Handles[idx].hEMA9, 1);
   double ema21 = GetEMA(Handles[idx].hEMA21, 1);
   double ema50 = GetEMA(Handles[idx].hEMA50, 1);

   double macd_main = 0, macd_sig = 0;
   GetMACD(Handles[idx].hMACD, macd_main, macd_sig, 1);

   double atr = GetATR(Handles[idx].hATR, 1);
   double poc = Handles[idx].cachedPOC;

   // BUY Signal: EMA Alignment + MACD + POC Confirmation (Price below POC for Buy TP potential)
   if(ema9 > ema21 && ema21 > ema50 && macd_main > macd_sig)
   {
      double price = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(poc > price) // Room to grow to POC
      {
         double sl = price - (atr * InpATR_Mult_SL);
         double tp = poc; // Use POC as TP
         OpenPosition(symbol, ORDER_TYPE_BUY, sl, tp);
      }
   }
   // SELL Signal: EMA Alignment + MACD + POC Confirmation (Price above POC for Sell TP potential)
   else if(ema9 < ema21 && ema21 < ema50 && macd_main < macd_sig)
   {
      double price = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(poc < price && poc > 0)
      {
         double sl = price + (atr * InpATR_Mult_SL);
         double tp = poc; // Use POC as TP
         OpenPosition(symbol, ORDER_TYPE_SELL, sl, tp);
      }
   }
}

//+------------------------------------------------------------------+
//| Add position on M1 candle close                                  |
//+------------------------------------------------------------------+
void AddTrendPosition(int idx)
{
   string symbol = Handles[idx].symbol;
   int posCount = CountPositions(symbol);
   if(posCount <= 0 || posCount >= InpMaxPositions) return;

   double ema9 = GetEMA(Handles[idx].hEMA9, 1);
   double ema21 = GetEMA(Handles[idx].hEMA21, 1);
   double ema50 = GetEMA(Handles[idx].hEMA50, 1);
   double macd_main = 0, macd_sig = 0;
   GetMACD(Handles[idx].hMACD, macd_main, macd_sig, 1);

   ENUM_POSITION_TYPE type = GetFirstPositionType(symbol);
   double atr = GetATR(Handles[idx].hATR, 1);
   double poc = Handles[idx].cachedPOC;

   if(type == POSITION_TYPE_BUY && ema9 > ema21 && ema21 > ema50 && macd_main > macd_sig)
   {
      double price = SymbolInfoDouble(symbol, SYMBOL_ASK);
      if(poc > price)
         OpenPosition(symbol, ORDER_TYPE_BUY, price - (atr * InpATR_Mult_SL), poc);
   }
   else if(type == POSITION_TYPE_SELL && ema9 < ema21 && ema21 < ema50 && macd_main < macd_sig)
   {
      double price = SymbolInfoDouble(symbol, SYMBOL_BID);
      if(poc < price && poc > 0)
         OpenPosition(symbol, ORDER_TYPE_SELL, price + (atr * InpATR_Mult_SL), poc);
   }
}

//+------------------------------------------------------------------+
//| Manage trailing stop, BE, and POC exit                           |
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

         // 2. POC Update (Keep TP at latest POC)
         int idx = GetHandleIndex(symbol);
         if(idx != -1)
         {
            double poc = Handles[idx].cachedPOC;
            if(poc > 0 && MathAbs(currentTP - poc) > symInfo.Point() * 10)
            {
               trade.PositionModify(posInfo.Ticket(), currentSL, poc);
            }
         }

         // 3. ATR Trailing Stop
         if(idx != -1)
         {
            double atr = GetATR(Handles[idx].hATR, 1);
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
//| Calculate Point of Control (POC) for last 1h candle              |
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

   // Find price level with maximum volume
   // We'll use a simple approach: group by price steps
   double step = SymbolInfoDouble(symbol, SYMBOL_POINT) * 10; // 1 pip steps
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

   int maxBin = 0;
   double maxV = 0;
   for(int i = 0; i < bins; i++)
   {
      if(volumes[i] > maxV) { maxV = volumes[i]; maxBin = i; }
   }

   return minPrice + (maxBin * step);
}

//+------------------------------------------------------------------+
//| Open a position with risk-based lot sizing                       |
//+------------------------------------------------------------------+
void OpenPosition(string symbol, ENUM_ORDER_TYPE type, double sl, double tp)
{
   double price = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(symbol, SYMBOL_ASK) : SymbolInfoDouble(symbol, SYMBOL_BID);
   double slDist = MathAbs(price - sl);
   if(slDist == 0) slDist = 100 * SymbolInfoDouble(symbol, SYMBOL_POINT);

   double lotSize = CalculateLotSize(symbol, slDist);

   trade.PositionOpen(symbol, type, lotSize, price, sl, tp, "Aggressive Growth");
}

//+------------------------------------------------------------------+
//| Calculate Lot Size based on Risk %                               |
//+------------------------------------------------------------------+
double CalculateLotSize(string symbol, double slDistInPrice)
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * (InpRiskPercent / 100.0);

   double tickValue = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickSize = SymbolInfoDouble(symbol, SYMBOL_TRADE_TICK_SIZE);
   double lotStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   if(slDistInPrice == 0 || tickValue == 0 || tickSize == 0) return SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);

   double lotSize = riskAmount / ( (slDistInPrice / tickSize) * tickValue );

   lotSize = MathFloor(lotSize / lotStep) * lotStep;
   double minLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double maxLot = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);

   if(lotSize < minLot) lotSize = minLot;
   if(lotSize > maxLot) lotSize = maxLot;

   return lotSize;
}

//--- HELPER FUNCTIONS
int GetHandleIndex(string symbol)
{
   for(int i=0; i<ArraySize(Handles); i++)
      if(Handles[i].symbol == symbol) return i;
   return -1;
}

double GetEMA(int handle, int shift)
{
   double buffer[];
   if(CopyBuffer(handle, 0, shift, 1, buffer) > 0) return buffer[0];
   return 0;
}

void GetMACD(int handle, double &main, double &sig, int shift)
{
   double main_buf[], sig_buf[];
   if(CopyBuffer(handle, 0, shift, 1, main_buf) > 0 && CopyBuffer(handle, 1, shift, 1, sig_buf) > 0)
   {
      main = main_buf[0];
      sig = sig_buf[0];
   }
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
      if(posInfo.SelectByIndex(i))
      {
         if(posInfo.Symbol() == symbol && posInfo.Magic() == InpMagicNumber) count++;
      }
   }
   return count;
}

ENUM_POSITION_TYPE GetFirstPositionType(string symbol)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(posInfo.SelectByIndex(i))
      {
         if(posInfo.Symbol() == symbol && posInfo.Magic() == InpMagicNumber) return posInfo.PositionType();
      }
   }
   return -1;
}
