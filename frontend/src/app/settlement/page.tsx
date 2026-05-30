"use client";

import React, { useState } from 'react';

export default function SettlementDashboard() {
  const [timeframes, setTimeframes] = useState([]);
  
  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Energy Revenue Settlement Dashboard</h1>
        <p className="text-slate-500">APSPDCL Open-Access Settlement</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* TPT145 Consumer */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="text-xl font-semibold mb-4">TPT145 (30% Share)</h2>
          <div className="space-y-4">
            <div className="flex justify-between py-2 border-b">
              <span className="text-slate-600">Total Generation Allocated</span>
              <span className="font-mono font-medium">---</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-slate-600">Max Demand (KVA)</span>
              <span className="font-mono font-medium">---</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-slate-600">Discom Accountable (KVAH)</span>
              <span className="font-mono font-medium">---</span>
            </div>
          </div>
        </div>

        {/* TPT2005 Consumer */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="text-xl font-semibold mb-4">CTR2005 (70% Share)</h2>
          <div className="space-y-4">
            <div className="flex justify-between py-2 border-b">
              <span className="text-slate-600">Total Generation Allocated</span>
              <span className="font-mono font-medium">---</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-slate-600">Max Demand (KVA)</span>
              <span className="font-mono font-medium">---</span>
            </div>
            <div className="flex justify-between py-2 border-b">
              <span className="text-slate-600">Discom Accountable (KVAH)</span>
              <span className="font-mono font-medium">---</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
