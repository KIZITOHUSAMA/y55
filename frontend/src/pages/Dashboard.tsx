import React, { useState, useEffect } from 'react';
import { TrendingUp, Activity, Wallet, ShieldCheck, RefreshCw } from 'lucide-react';
import axios from 'axios';

const StatCard = ({ icon: Icon, label, value, change, color }: any) => (
  <div className="bg-card p-6 rounded-xl border border-slate-800">
    <div className="flex items-center justify-between mb-4">
      <div className={`p-2 rounded-lg ${color}`}>
        <Icon size={24} className="text-white" />
      </div>
      <span className={`text-sm font-medium ${change.startsWith('+') ? 'text-green-400' : 'text-red-400'}`}>
        {change}
      </span>
    </div>
    <p className="text-slate-400 text-sm mb-1">{label}</p>
    <h3 className="text-2xl font-bold">{value}</h3>
  </div>
);

export const Dashboard = () => {
  const [signals, setSignals] = useState<any[]>([]);
  const [bots, setBots] = useState<any[]>([]);
  const [mt5, setMt5] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [sigRes, botRes, mt5Res] = await Promise.all([
        axios.get('http://localhost:8000/api/signals'),
        axios.get('http://localhost:8000/api/bots'),
        axios.get('http://localhost:8000/api/mt5/status')
      ]);
      setSignals(sigRes.data);
      setBots(botRes.data);
      setMt5(mt5Res.data);
    } catch (err) {
      console.error("Failed to fetch dashboard data", err);
    } finally {
      setLoading(false);
    }
  };

  const toggleBot = async (id: number) => {
    try {
      await axios.post(`http://localhost:8000/api/bots/${id}/toggle`);
      fetchData();
    } catch (err) {
      console.error("Failed to toggle bot", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Auto-refresh every 30s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-8">
      {/* Welcome Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold">Welcome back, Kasha!</h2>
          <p className="text-slate-400">Account: {mt5?.account_id} • Broker: {mt5?.broker}</p>
        </div>
        <div className="flex items-center space-x-3 bg-primary/10 border border-primary/20 p-4 rounded-xl">
          <ShieldCheck className="text-primary" />
          <span className="text-sm font-medium text-primary">All Premium Features Unlocked</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={Wallet}
          label="Total Balance"
          value={mt5 ? `$${mt5.balance.toLocaleString()}` : "$0.00"}
          change="+12.5%"
          color="bg-blue-500"
        />
        <StatCard
          icon={TrendingUp}
          label="Equity"
          value={mt5 ? `$${mt5.equity.toLocaleString()}` : "$0.00"}
          change="+4.2%"
          color="bg-green-500"
        />
        <StatCard
          icon={Activity}
          label="Active Bots"
          value={bots.filter(b => b.status === 'Running').length.toString()}
          change="+1"
          color="bg-purple-500"
        />
        <StatCard
          icon={Activity}
          label="Margin Level"
          value={mt5 ? `${mt5.margin_level}%` : "0%"}
          change="+2.4%"
          color="bg-orange-500"
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Signals */}
        <div className="lg:col-span-2 bg-card rounded-xl border border-slate-800 overflow-hidden">
          <div className="p-6 border-b border-slate-800 flex items-center justify-between">
            <h3 className="font-bold text-lg">Live AI Signals (Real Data)</h3>
            <button onClick={fetchData} className="p-2 hover:bg-slate-800 rounded transition-colors">
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>
          </div>
          <div className="divide-y divide-slate-800">
            {signals.map((signal, i) => (
              <div key={i} className="p-4 flex items-center justify-between hover:bg-slate-800/50 transition-colors">
                <div className="flex items-center space-x-4">
                  <div className={`w-2 h-12 rounded-full ${signal.type === 'BUY' ? 'bg-green-500' : 'bg-red-500'}`} />
                  <div>
                    <p className="font-bold">{signal.pair}</p>
                    <p className="text-xs text-slate-400">{signal.time} • {signal.strength} Strength</p>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm text-center">
                  <div>
                    <p className="text-slate-400 text-xs">Entry</p>
                    <p className="font-medium">{signal.entry}</p>
                  </div>
                  <div>
                    <p className="text-slate-400 text-xs">TP</p>
                    <p className="font-medium text-green-400">{signal.tp}</p>
                  </div>
                  <div>
                    <p className="text-slate-400 text-xs">SL</p>
                    <p className="font-medium text-red-400">{signal.sl}</p>
                  </div>
                </div>
                <div className="hidden md:block">
                  <button className="bg-primary hover:bg-primary/90 text-white px-4 py-2 rounded-lg text-sm font-bold transition-all">
                    Copy Trade
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Active Bots */}
        <div className="bg-card rounded-xl border border-slate-800 flex flex-col">
          <div className="p-6 border-b border-slate-800">
            <h3 className="font-bold text-lg">Active Cloud Bots</h3>
          </div>
          <div className="flex-1 p-6 space-y-4">
            {bots.map((bot, i) => (
              <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-slate-700">
                <div>
                  <p className="font-medium text-sm">{bot.name}</p>
                  <p className={`text-xs ${bot.status === 'Running' ? 'text-green-400' : 'text-slate-400'}`}>{bot.status}</p>
                </div>
                <div className="text-right">
                  <p className={`font-bold text-sm ${bot.profit >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {bot.profit >= 0 ? '+' : ''}{bot.profit.toFixed(2)}
                  </p>
                  <button onClick={() => toggleBot(bot.id)} className="text-[10px] text-primary hover:underline">
                    {bot.status === 'Running' ? 'Pause' : 'Start'}
                  </button>
                </div>
              </div>
            ))}
            <button className="w-full py-3 rounded-xl border-2 border-dashed border-slate-700 text-slate-400 hover:text-white hover:border-primary transition-all text-sm font-medium">
              + Deploy New Bot
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
