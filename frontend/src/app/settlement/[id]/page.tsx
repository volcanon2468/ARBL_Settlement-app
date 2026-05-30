"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';

export default function TimeframeDetails({ params }: { params: { id: string } }) {
  const [activeTab, setActiveTab] = useState('variables');
  const [timeframe, setTimeframe] = useState<any>(null);
  
  // Variables state
  const [vars, setVars] = useState({
    Share_Cons1: 30,
    Share_Cons2: 70,
    Default_Loss: 4.0,
    Old_Bank_KWH: 0,
    Bank_Loss_Pct: 4.0,
    Cap_Gen_KW: 4000,
    Cap_Cons1_KW: 1000,
    Cap_Cons2_KW: 3000,
    CT_Ratio: 1,
    Con1_Label: 'TPT145',
    Con2_Label: 'CTR2005'
  });

  // Upload status
  const [uploadStatus, setUploadStatus] = useState<any>({});
  
  // Results
  const [results, setResults] = useState<any[]>([]);

  const API_BASE = "http://localhost:8000/api/v1";

  useEffect(() => {
    loadTimeframe();
    loadVariables();
    loadUploadStatus();
    loadResults();
  }, [params.id]);

  const loadTimeframe = async () => {
    const res = await fetch(`${API_BASE}/timeframes/${params.id}`);
    const data = await res.json();
    if(data.success) setTimeframe(data.data);
  };

  const loadVariables = async () => {
    const res = await fetch(`${API_BASE}/timeframes/${params.id}/variables`);
    const data = await res.json();
    if(data.success && data.data) setVars(data.data);
  };

  const saveVariables = async (e: React.FormEvent) => {
    e.preventDefault();
    await fetch(`${API_BASE}/timeframes/${params.id}/variables`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(vars)
    });
    alert("Variables saved!");
  };

  const loadUploadStatus = async () => {
    const res = await fetch(`${API_BASE}/timeframes/${params.id}/upload/status`);
    const data = await res.json();
    if(data.success) setUploadStatus(data.data);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>, fileType: string) => {
    if(!e.target.files || !e.target.files[0]) return;
    const formData = new FormData();
    formData.append("file", e.target.files[0]);
    
    const res = await fetch(`${API_BASE}/timeframes/${params.id}/upload/${fileType}`, {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if(data.success) {
      alert(`${fileType} uploaded successfully!`);
      loadUploadStatus();
    } else {
      alert(`Error: ${data.error}`);
    }
  };

  const runCalculation = async () => {
    const res = await fetch(`${API_BASE}/timeframes/${params.id}/calculate`, { method: 'POST' });
    const data = await res.json();
    if(data.success) {
      alert("Calculation started! Wait a few seconds and refresh the results.");
      // Polling can be added here
    }
  };

  const loadResults = async () => {
    const res = await fetch(`${API_BASE}/timeframes/${params.id}/results`);
    const data = await res.json();
    if(data.success) setResults(data.data);
  };

  const exportUrl = `${API_BASE}/timeframes/${params.id}/export?type=final&consumer=ALL`;

  if(!timeframe) return <div className="p-8">Loading...</div>;

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <header className="mb-8 flex justify-between items-end border-b pb-4">
        <div>
          <Link href="/settlement" className="text-blue-600 hover:underline mb-2 block">&larr; Back to Dashboard</Link>
          <h1 className="text-3xl font-bold text-slate-900">{timeframe.Label}</h1>
          <p className="text-slate-500">{timeframe.Start_Date} to {timeframe.End_Date} - Status: <span className="font-semibold text-blue-600">{timeframe.Status || 'PENDING'}</span></p>
        </div>
        <button onClick={runCalculation} className="bg-green-600 text-white px-6 py-2 rounded-lg font-bold hover:bg-green-700 shadow-md">
          Run Calculation
        </button>
      </header>

      <div className="flex gap-4 mb-6 border-b">
        <button className={`py-2 px-4 ${activeTab === 'variables' ? 'border-b-2 border-blue-600 font-semibold text-blue-600' : 'text-slate-500'}`} onClick={() => setActiveTab('variables')}>Variables</button>
        <button className={`py-2 px-4 ${activeTab === 'uploads' ? 'border-b-2 border-blue-600 font-semibold text-blue-600' : 'text-slate-500'}`} onClick={() => setActiveTab('uploads')}>Upload Data</button>
        <button className={`py-2 px-4 ${activeTab === 'results' ? 'border-b-2 border-blue-600 font-semibold text-blue-600' : 'text-slate-500'}`} onClick={() => setActiveTab('results')}>Results</button>
      </div>

      {activeTab === 'variables' && (
        <form onSubmit={saveVariables} className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 max-w-4xl grid grid-cols-2 gap-4">
          {Object.keys(vars).map(key => (
            <div key={key}>
              <label className="block text-sm text-slate-600 mb-1">{key}</label>
              <input 
                type={key.includes('Label') ? 'text' : 'number'} step="any"
                className="border p-2 rounded w-full bg-slate-50"
                value={(vars as any)[key]} 
                onChange={e => setVars({...vars, [key]: key.includes('Label') ? e.target.value : parseFloat(e.target.value)})} 
              />
            </div>
          ))}
          <div className="col-span-2 mt-4">
            <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 w-full">Save Variables</button>
          </div>
        </form>
      )}

      {activeTab === 'uploads' && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 max-w-4xl">
          <h2 className="text-xl font-semibold mb-4">Required Files</h2>
          <div className="space-y-4">
            {[
              { type: 'gen_cdf', label: 'Generator CDF File (.csv)' },
              { type: 'con1_cdf', label: `Consumer 1 (${vars.Con1_Label}) CDF File (.csv)` },
              { type: 'con2_cdf', label: `Consumer 2 (${vars.Con2_Label}) CDF File (.csv)` },
              { type: 'iex1', label: `Consumer 1 IEX Data (.xlsx)` },
              { type: 'iex2', label: `Consumer 2 IEX Data (.xlsx)` }
            ].map(f => (
              <div key={f.type} className="flex items-center justify-between p-4 border rounded bg-slate-50">
                <div className="w-1/3 font-medium">{f.label}</div>
                <div className="w-1/3 text-center">
                  {uploadStatus[f.type] === 'OK' ? <span className="text-green-600 font-bold">✓ Uploaded & Parsed</span> : <span className="text-amber-500">Missing</span>}
                </div>
                <div className="w-1/3 text-right">
                  <input type="file" onChange={(e) => handleFileUpload(e, f.type)} className="text-sm" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'results' && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold">Final Settlement Results</h2>
            <div className="flex gap-4">
              <button onClick={loadResults} className="text-blue-600 hover:underline">Refresh</button>
              <a href={exportUrl} download className="bg-slate-800 text-white px-4 py-2 rounded text-sm hover:bg-slate-700">Export Excel</a>
            </div>
          </div>
          
          {results.length === 0 ? (
            <div className="text-slate-500 py-8 text-center">No results available. Run calculation first.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {results.map((r, i) => (
                <div key={i} className="border p-6 rounded-xl bg-slate-50">
                  <h3 className="text-lg font-bold mb-4">{r.Consumer_Label} ({r.Share_Pct}%)</h3>
                  <div className="space-y-2">
                    <div className="flex justify-between border-b pb-1"><span className="text-slate-600">Total Gen Allocated (KWH)</span><span className="font-mono">{r.Total_Gen_Allocated_KWH?.toFixed(2)}</span></div>
                    <div className="flex justify-between border-b pb-1"><span className="text-slate-600">Billed Units Discom (KVAH)</span><span className="font-mono font-bold text-red-600">{r.Billed_Units_Discom_KVAH?.toFixed(2)}</span></div>
                    <div className="flex justify-between border-b pb-1"><span className="text-slate-600">Old Bank (KWH)</span><span className="font-mono">{r.Old_Bank_KWH?.toFixed(2)}</span></div>
                    <div className="flex justify-between border-b pb-1"><span className="text-slate-600">Energy Banked (KWH)</span><span className="font-mono text-green-600">{r.Energy_Banked_KWH?.toFixed(2)}</span></div>
                    <div className="flex justify-between pt-2"><span className="text-slate-600">Max Demand (KVA)</span><span className="font-mono font-bold">{r.Max_Demand_KVA?.toFixed(2)}</span></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
