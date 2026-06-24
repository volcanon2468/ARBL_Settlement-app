"use client";
import { toast } from 'sonner';
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Download, FileText, CheckCircle2, Zap, RefreshCw, BarChart3, UploadCloud } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Area, AreaChart } from 'recharts';
interface Result {
  Consumer_Label: string;
  [key: string]: any;
}
interface Variables {
  Share_Cons1?: number;
  Share_Cons2?: number;
  [key: string]: any;
}

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  // Next 14 / 15+ Compatibility
  const resolvedParams = params as any;
  const id = resolvedParams.then ? (React.use(resolvedParams) as any).id : resolvedParams.id;
  const [results, setResults] = useState<Result[]>([]);
  const [vars, setVars] = useState<Variables | null>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [calculating, setCalculating] = useState(false);
  const [verificationResults, setVerificationResults] = useState<any>(null);
  const [verifying, setVerifying] = useState(false);

  const setErrorMsg = (msg: string | null) => { if (msg) toast.error(msg); };
  const API_BASE = "/api/v1";

  const runCalculation = async () => {
    setCalculating(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE}/timeframes/${id}/calculate`, { method: 'POST' });
      const data = await res.json();
      if(data.success) {
        setTimeout(() => {
          setCalculating(false);
          loadResults();
        }, 1500);
      } else {
        setErrorMsg(`Error calculating: ${data.error}`);
        setCalculating(false);
      }
    } catch {
      setErrorMsg("Network Error running calculation");
      setCalculating(false);
    }
  };
    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    const formData = new FormData();
    formData.append("file", file);
    
    setVerifying(true);
    toast.info("Verifying check file...");
    
    try {
      const res = await fetch(`${API_BASE}/timeframes/${id}/verify-check-file`, {
        method: 'POST',
        body: formData,
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      const data = await res.json();
      if (data.success) {
        setVerificationResults(data.data);
        toast.success("Verification complete");
      } else {
        toast.error(`Verification failed: ${data.error}`);
      }
    } catch (err) {
      toast.error("Network error during verification");
    } finally {
      setVerifying(false);
      e.target.value = '';
    }
  };

  const loadResults = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/timeframes/${id}/results`);
      if (res.ok) {
        const data = await res.json();
        if(data.success) setResults(data.data);
      }
      const vRes = await fetch(`${API_BASE}/timeframes/${id}/variables`);
      if (vRes.ok) {
        const vData = await vRes.json();
        if(vData.success) setVars(vData.data);
      }
      const bRes = await fetch(`${API_BASE}/timeframes/${id}/calculated`);
      if (bRes.ok) {
        const bData = await bRes.json();
        if(bData.success && bData.data) {
           const grouped: Record<string, any> = {};
           
           
           bData.data.slice(0, 192).forEach((b: any) => {
             const key = `Slot ${b.Slot}`;
             if (!grouped[key]) {
               grouped[key] = { slot: key };
             }
             if (b.Consumer_Label === 'TPT145') {
               grouped[key].generation_tpt = b.Gen_Share_KW;
               grouped[key].consumption_tpt = b.Discom_KVA;
             } else if (b.Consumer_Label === 'CTR2005') {
               grouped[key].generation_ctr = b.Gen_Share_KW;
               grouped[key].consumption_ctr = b.Discom_KVA;
             }
           });
           
           setChartData(Object.values(grouped));
        }
      }
    } catch {
      console.error("Error loading results");
      toast.error("Network Error: Could not load settlement results. Please check your connection.");
    }
  }, [id]);

  useEffect(() => {
    loadResults();
  }, [loadResults]);
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-6xl mx-auto p-6">
      <Card className="border-primary/20 shadow-xl overflow-hidden relative glass-dark text-slate-100">
        <div className="absolute top-0 right-0 p-12 opacity-10 pointer-events-none">
          <Zap className="w-64 h-64 text-white" />
        </div>
        <CardContent className="p-10 flex flex-col md:flex-row justify-between items-center gap-8 relative z-10">
          <div>
            <h2 className="text-3xl font-bold mb-3 text-white">Settlement Engine</h2>
            <p className="text-slate-300 text-lg max-w-xl leading-relaxed">
              Execute the highly precise block-wise mathematical settlement using all uploaded variable constraints and strictly filtered data arrays.
            </p>
          </div>
          <Button
            className="h-12 px-8 font-bold text-lg bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg transition-transform hover:scale-105 rounded-xl"
            onClick={runCalculation}
            disabled={calculating}
          >
            {calculating ? (
              <span className="flex items-center gap-2"><RefreshCw className="w-5 h-5 animate-spin" /> Calculating...</span>
            ) : "Run Final Calculation"}
          </Button>
        </CardContent>
      </Card>
      <div className="pt-8">
        <div className="flex flex-col sm:flex-row justify-between items-end mb-8 gap-4">
          <div>
            <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
              <FileText className="w-6 h-6 text-primary" />
              Final Executive Report
            </h2>
            <p className="text-muted-foreground mt-1">Review the top-level aggregates generated by the settlement engine.</p>
          </div>
          <div className="flex gap-4">
            <div>
              <input type="file" id="verify-upload" accept=".xlsx, .xls" className="hidden" onChange={handleFileUpload} disabled={verifying} />
              <Button className="bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm p-0 cursor-pointer" disabled={verifying}>
                <label htmlFor="verify-upload" className="flex items-center gap-2 w-full h-full px-4 py-2 cursor-pointer">
                  {verifying ? <RefreshCw className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
                  {verifying ? "Verifying..." : "Verify Official File"}
                </label>
              </Button>
            </div>
            
            <Button
              className="bg-slate-900 text-white hover:bg-slate-800 shadow-sm gap-2"
              onClick={async () => {
                try {
                  const token = localStorage.getItem('token');
                  const res = await fetch(`${API_BASE}/timeframes/${id}/export?type=final`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                  });
                  if (!res.ok) throw new Error("Export failed");
                  const blob = await res.blob();
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `Settlement_History_${id}.xlsx`;
                  document.body.appendChild(a);
                  a.click();
                  a.remove();
                  window.URL.revokeObjectURL(url);
                } catch {
                  setErrorMsg("Failed to download export");
                }
              }}
            >
              <Download className="w-4 h-4" /> Export Official Excel
            </Button>
          </div>
        </div>
        {results.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-slate-500 bg-slate-50/50 rounded-3xl border border-slate-200 shadow-inner">
            <div className="bg-white p-6 rounded-full shadow-sm mb-6">
              <FileText className="w-12 h-12 text-primary/40" />
            </div>
            <h3 className="text-2xl font-bold mb-2 text-slate-700">Awaiting Calculation</h3>
            <p className="text-base max-w-md text-center text-slate-500">Run the high-precision settlement engine above to generate the final verified billing metrics for this timeframe.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
            {results.map((r, i) => (
              <Card key={i} className="overflow-hidden border-0 shadow-2xl hover:shadow-3xl transition-all duration-500 bg-white rounded-3xl group">
                <div className="bg-gradient-to-r from-slate-900 to-slate-800 px-8 py-6 flex justify-between items-center relative overflow-hidden">
                  <div className="absolute right-0 top-0 w-32 h-32 bg-white opacity-5 rounded-full -mr-10 -mt-10 blur-2xl"></div>
                  <h3 className="text-2xl font-extrabold text-white flex items-center gap-3 relative z-10 tracking-tight">
                    <CheckCircle2 className="w-7 h-7 text-emerald-400" />
                    {r.Consumer_Label}
                  </h3>
                  <span className="bg-white/10 text-white backdrop-blur-md font-bold px-4 py-1.5 rounded-full text-sm border border-white/20 shadow-sm relative z-10">
                    {vars ? (r.Consumer_Label === 'TPT145' ? vars.Share_Cons1 : vars.Share_Cons2) : '0'}% Allocation
                  </span>
                </div>
                <CardContent className="p-0">
                  <div className="divide-y divide-slate-100/60">
                    <div className="px-8 py-5 flex justify-between items-center hover:bg-slate-50/80 transition-colors">
                      <span className="text-slate-500 font-semibold uppercase tracking-wider text-xs">Gen Allocated (Entry)</span>
                      <span className="font-mono text-xl font-bold text-slate-800">{r.Revised_Gen_Allocated_KWH?.toFixed(2)} <span className="text-sm text-slate-400 font-sans">KWH</span></span>
                    </div>
                    <div className="px-8 py-5 flex justify-between items-center bg-red-50/40 hover:bg-red-50/80 transition-colors">
                      <span className="text-red-800 font-bold uppercase tracking-wider text-xs flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-red-500"></span> Discom Billing
                      </span>
                      <span className="font-mono font-black text-2xl text-red-600">{r.Discom_KVAH?.toFixed(2)} <span className="text-sm text-red-400 font-sans">KVAH</span></span>
                    </div>
                    <div className="px-8 py-5 flex justify-between items-center hover:bg-slate-50/80 transition-colors">
                      <span className="text-slate-500 font-semibold uppercase tracking-wider text-xs">Sch. From Bank</span>
                      <span className="font-mono text-xl font-bold text-slate-700">{r.Sch_From_Bank_KWH?.toFixed(2)} <span className="text-sm text-slate-400 font-sans">KWH</span></span>
                    </div>
                    <div className="px-8 py-5 flex justify-between items-center bg-emerald-50/40 hover:bg-emerald-50/80 transition-colors">
                      <span className="text-emerald-800 font-bold uppercase tracking-wider text-xs flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Energy Banked
                      </span>
                      <span className="font-mono font-black text-2xl text-emerald-600">{r.Bank_KWH?.toFixed(2)} <span className="text-sm text-emerald-400 font-sans">KWH</span></span>
                    </div>
                    <div className="px-8 py-6 flex justify-between items-center bg-slate-900 text-white group-hover:bg-slate-800 transition-colors">
                      <div className="flex flex-col">
                        <span className="text-slate-400 font-semibold uppercase tracking-wider text-xs mb-1">Max Recorded Demand</span>
                        <span className="text-xs text-slate-500">{r.Max_Demand_Slot_Str || 'N/A'}</span>
                      </div>
                      <span className="font-mono font-black text-3xl text-white tracking-tight">{r.Max_Demand_KVA?.toFixed(2)} <span className="text-base text-slate-400 font-sans font-medium">KVA</span></span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        
        
        {verificationResults && (
          <div className="mt-12 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-300">
            <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2 mb-6">
              <CheckCircle2 className="w-6 h-6 text-emerald-500" />
              Official Verification Results
            </h2>
            <div className="grid grid-cols-1 gap-10">
              {verificationResults.map((vr: any, i: number) => (
                <Card key={i} className="overflow-hidden border-0 shadow-xl bg-white rounded-3xl">
                  <div className="bg-slate-800 px-8 py-4">
                    <h3 className="text-xl font-bold text-white">{vr.consumer} - Difference Analysis</h3>
                  </div>
                  <CardContent className="p-0 overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-slate-50 border-b border-slate-200">
                          <th className="p-4 font-semibold text-slate-600">Metric</th>
                          <th className="p-4 font-semibold text-slate-600">App Calculated</th>
                          <th className="p-4 font-semibold text-slate-600">Official File</th>
                          <th className="p-4 font-semibold text-slate-600">Difference</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {vr.metrics.map((m: any, j: number) => {
                          const isMatch = Math.abs(m.diff) < 0.05;
                          return (
                            <tr key={j} className="hover:bg-slate-50/50">
                              <td className="p-4 text-slate-700 font-medium">{m.name}</td>
                              <td className="p-4 font-mono text-slate-600">{m.app_val.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 3})}</td>
                              <td className="p-4 font-mono text-slate-600">{m.check_val.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 3})}</td>
                              <td className={`p-4 font-mono font-bold ${isMatch ? 'text-emerald-500' : 'text-red-500'}`}>
                                {m.diff > 0 ? '+' : ''}{m.diff.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 3})}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {chartData.length > 0 && (
          <div className="mt-12 animate-in fade-in slide-in-from-bottom-4 duration-700 delay-200">
            <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2 mb-6">
              <BarChart3 className="w-6 h-6 text-primary" />
              Dynamic Block-wise Settlement Graph
            </h2>
            <Card className="p-6 border-0 shadow-xl bg-white rounded-3xl">
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="slot" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} minTickGap={30} />
                    <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)' }}
                    />
                    <Legend iconType="circle" wrapperStyle={{ paddingTop: '20px' }} />
                    <Line type="monotone" dataKey="generation_tpt" name="TPT145 Gen (KWH)" stroke="#0ea5e9" strokeWidth={3} dot={false} />
                    <Line type="monotone" dataKey="consumption_tpt" name="TPT145 Cons (KVAH)" stroke="#ef4444" strokeWidth={3} dot={false} />
                    <Line type="monotone" dataKey="generation_ctr" name="CTR2005 Gen (KWH)" stroke="#10b981" strokeWidth={3} dot={false} strokeDasharray="5 5" />
                    <Line type="monotone" dataKey="consumption_ctr" name="CTR2005 Cons (KVAH)" stroke="#f59e0b" strokeWidth={3} dot={false} strokeDasharray="5 5" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
