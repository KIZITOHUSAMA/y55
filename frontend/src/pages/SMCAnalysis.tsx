import React, { useState, useEffect } from 'react';
import { Activity, Search, ShieldCheck } from 'lucide-react';
import axios from 'axios';

export const SMCAnalysis = () => {
  const [analysis, setAnalysis] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const pairs = ["XAUUSD", "EURUSD", "BTCUSD", "GBPUSD", "USDJPY"];

  const runAnalysis = async () => {
    setLoading(true);
    try {
      // In a full implementation, we'd have a specific endpoint for deep analysis
      const res = await axios.get('http://localhost:8000/api/signals');
      setAnalysis(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runAnalysis();
  }, []);

  return (
    <div className="space-y-8">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold">SMC Chart Analysis</h2>
          <p className="text-slate-400">Smart Money Concepts: Order Blocks, BOS, and CHOCH</p>
        </div>
        <button
          onClick={runAnalysis}
          className="bg-primary hover:bg-primary/90 text-white px-6 py-2 rounded-lg font-bold flex items-center space-x-2"
        >
          {loading ? <Activity className="animate-spin" /> : <Search size={20} />}
          <span>Run New Analysis</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {analysis.map((item, i) => (
          <div key={i} className="bg-card border border-slate-800 rounded-xl p-6 space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-xl font-bold">{item.pair}</h3>
              <span className={`px-3 py-1 rounded-full text-xs font-bold ${item.type === 'BUY' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                {item.type === 'BUY' ? 'BULLISH BIAS' : 'BEARISH BIAS'}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                <p className="text-xs text-slate-400 uppercase">Market Structure</p>
                <p className="font-semibold">{item.strength} Trend</p>
              </div>
              <div className="bg-slate-800/50 p-3 rounded-lg border border-slate-700">
                <p className="text-xs text-slate-400 uppercase">Order Block</p>
                <p className="font-semibold text-primary">{item.entry}</p>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-slate-400">Probability</span>
                <span className="text-green-400 font-bold">85%</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div className="bg-primary h-full w-[85%]"></div>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800 flex gap-4">
              <div className="flex-1">
                <p className="text-[10px] text-slate-500 uppercase">Take Profit</p>
                <p className="text-sm font-bold text-green-400">{item.tp}</p>
              </div>
              <div className="flex-1">
                <p className="text-[10px] text-slate-500 uppercase">Stop Loss</p>
                <p className="text-sm font-bold text-red-400">{item.sl}</p>
              </div>
              <button className="bg-slate-800 hover:bg-slate-700 px-4 py-1 rounded text-xs font-bold">
                View Chart
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
