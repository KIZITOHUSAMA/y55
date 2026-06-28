import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { DashboardLayout } from './layouts/DashboardLayout';
import { Dashboard } from './pages/Dashboard';
import { SMCAnalysis } from './pages/SMCAnalysis';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route
          path="/dashboard"
          element={
            <DashboardLayout>
              <Dashboard />
            </DashboardLayout>
          }
        />
        <Route
          path="/signals"
          element={
            <DashboardLayout>
              <div className="p-8"><h2 className="text-2xl font-bold">AI Signals (Premium)</h2><p className="text-slate-400">Real-time signals from our SMC Engine.</p></div>
            </DashboardLayout>
          }
        />
        <Route
          path="/bots"
          element={
            <DashboardLayout>
              <div className="p-8"><h2 className="text-2xl font-bold">Cloud Bots</h2><p className="text-slate-400">Manage your automated strategies.</p></div>
            </DashboardLayout>
          }
        />
        <Route
          path="/analysis"
          element={
            <DashboardLayout>
              <SMCAnalysis />
            </DashboardLayout>
          }
        />
        <Route
          path="/settings"
          element={
            <DashboardLayout>
              <div className="p-8"><h2 className="text-2xl font-bold">Settings</h2><p className="text-slate-400">Account and connection settings.</p></div>
            </DashboardLayout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
