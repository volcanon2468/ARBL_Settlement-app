"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

export default function SettlementDashboard() {
  const [timeframes, setTimeframes] = useState([]);
  const [newLabel, setNewLabel] = useState('');
  const [newStart, setNewStart] = useState('');
  const [newEnd, setNewEnd] = useState('');
  
  const API_BASE = "http://localhost:8000/api/v1";

  const loadTimeframes = async () => {
    try {
      const res = await fetch(`${API_BASE}/timeframes`);
      const data = await res.json();
      if(data.success) {
        setTimeframes(data.data);
      }
    } catch(e) {
      console.error("Error loading timeframes:", e);
    }
  };

  useEffect(() => {
    loadTimeframes();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/timeframes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ Label: newLabel, Start_Date: newStart, End_Date: newEnd })
      });
      if(res.ok) {
        setNewLabel('');
        setNewStart('');
        setNewEnd('');
        loadTimeframes();
      }
    } catch(e) {
      console.error(e);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Energy Revenue Settlement</h1>
        <p className="text-slate-500">APSPDCL Open-Access Settlement</p>
      </header>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-8 max-w-4xl">
        <h2 className="text-xl font-semibold mb-4">Create New Timeframe</h2>
        <form onSubmit={handleCreate} className="flex gap-4 items-end flex-wrap">
          <div>
            <label className="block text-sm text-slate-600 mb-1">Label (e.g. Jan 2024)</label>
            <input required type="text" className="border border-slate-300 p-2 rounded w-full" value={newLabel} onChange={e => setNewLabel(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">Start Date</label>
            <input required type="date" className="border border-slate-300 p-2 rounded w-full" value={newStart} onChange={e => setNewStart(e.target.value)} />
          </div>
          <div>
            <label className="block text-sm text-slate-600 mb-1">End Date</label>
            <input required type="date" className="border border-slate-300 p-2 rounded w-full" value={newEnd} onChange={e => setNewEnd(e.target.value)} />
          </div>
          <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition-colors font-medium h-[42px]">Create Timeframe</button>
        </form>
      </div>

      <h2 className="text-2xl font-bold text-slate-800 mb-4">Existing Timeframes</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {timeframes.length === 0 && <p className="text-slate-500">No timeframes created yet.</p>}
        {timeframes.map((tf: any) => (
          <Link href={`/settlement/${tf.Id}`} key={tf.Id}>
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 hover:shadow-md hover:border-blue-400 cursor-pointer transition-all">
              <h2 className="text-xl font-semibold mb-2">{tf.Label}</h2>
              <div className="text-sm text-slate-500">Status: <span className={`font-semibold ${tf.Status === 'COMPLETE' ? 'text-green-600' : 'text-blue-600'}`}>{tf.Status || 'PENDING'}</span></div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
