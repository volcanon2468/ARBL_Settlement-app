"use client";
import { toast } from 'sonner';
import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useRouter } from 'next/navigation';
import { Settings2, UploadCloud, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';

interface Vars {
  [key: string]: any;
}
interface Status {
  [key: string]: any;
}

export default function InputsPage({ params }: { params: Promise<{ id: string }> }) {
  // Next 14 / 15+ Compatibility
  const resolvedParams = params as any;
  const id = resolvedParams.then ? (React.use(resolvedParams) as any).id : resolvedParams.id;
  const [vars, setVars] = useState<Vars>({
    Share_Cons1: '', Share_Cons2: '', Bank_Usage_Start_Month: '', Bank_Usage_Start_Year: '', Bank_Usage_End_Month: '', Bank_Usage_End_Year: '', Bank_Loss_Pct: '2'
  });
  const [shutdownWindows, setShutdownWindows] = useState<{Window_Start: string, Window_End: string}[]>([]);
  const [customLosses, setCustomLosses] = useState<{Window_Start: string, Window_End: string, Loss_Pct: string}[]>([]);
  const [stagedFiles, setStagedFiles] = useState<Record<string, File>>({});
  const [status, setStatus] = useState<Status>({});
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null);
  const setErrorMsg = (msg: string | null) => { if (msg) toast.error(msg); };
  const router = useRouter();
  const API_BASE = "/api/v1";

  const loadVars = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/timeframes/${id}/variables`);
      if (res.ok) {
        const data = await res.json();
        if(data.success && data.data) setVars(data.data);
      }
      const swRes = await fetch(`${API_BASE}/timeframes/${id}/shutdown_windows`);
      if (swRes.ok) {
        const swData = await swRes.json();
        if(swData.success && swData.data) setShutdownWindows(swData.data);
      }
      const clRes = await fetch(`${API_BASE}/timeframes/${id}/custom_losses`);
      if (clRes.ok) {
        const clData = await clRes.json();
        if(clData.success && clData.data) setCustomLosses(clData.data);
      }
    } catch (e) {
      console.error(e);
      toast.error("Network Error: Could not fetch settlement setup parameters.");
    }
  }, [id]);
  const loadStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/timeframes/${id}/upload/status`);
      if (res.ok) {
        const data = await res.json();
        if(data.success) setStatus(data.data);
      }
    } catch (e) {
      console.error(e);
      toast.error("Network Error: Could not fetch upload status.");
    }
  }, [id]);

  useEffect(() => {
    loadVars();
    loadStatus();
  }, [loadVars, loadStatus]);
  const handleVarChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setVars({ ...vars, [e.target.name]: e.target.value });
  };
  const saveAll = async (e?: React.FormEvent) => {
    if(e) e.preventDefault();
    const form = document.getElementById('variables-form') as HTMLFormElement;
    if (form && !form.checkValidity()) {
      form.reportValidity();
      return;
    }
    const s1 = parseFloat(vars.Share_Cons1 as string) || 0;
    const s2 = parseFloat(vars.Share_Cons2 as string) || 0;
    if (s1 < 0 || s2 < 0 || s1 + s2 > 100) {
      setErrorMsg("Total Consumer Allocation Share cannot exceed 100% and must be positive.");
      return;
    }
    const bankLoss = parseFloat(vars.Bank_Loss_Pct as string) || 0;
    if (bankLoss < 0 || bankLoss > 100) {
      setErrorMsg("Bank Transmission Loss % must be between 0 and 100.");
      return;
    }
    for (let i = 0; i < shutdownWindows.length; i++) {
      const sw = shutdownWindows[i];
      const parseDateStr = (dateStr: string) => {
        const [datePart, timePart] = dateStr.split(' ');
        if (!datePart || !timePart) return new Date(0);
        const [d, m, y] = datePart.split('-');
        const [h, min] = timePart.split(':');
        return new Date(parseInt(y), parseInt(m)-1, parseInt(d), parseInt(h), parseInt(min));
      };
      
      const startD = parseDateStr(sw.Window_Start as string);
      const endD = parseDateStr(sw.Window_End as string);
      if (endD.getTime() < startD.getTime()) {
         setErrorMsg(`Shutdown Window ${i+1}: End Slot cannot be before Start Slot.`);
         return;
      }
    }
    for (let i = 0; i < customLosses.length; i++) {
      const cl = customLosses[i];
      if ((cl.Window_End as string) < (cl.Window_Start as string)) {
         setErrorMsg(`Custom Loss Window ${i+1}: End Date cannot be before Start Date.`);
         return;
      }
      const pct = parseFloat(cl.Loss_Pct as string) || 0;
      if (pct < 0 || pct > 100) {
         setErrorMsg(`Custom Loss Window ${i+1}: Loss % must be between 0 and 100.`);
         return;
      }
    }
    setSaving(true);
    setErrorMsg(null);
    try {
      const payload = { ...vars } as Record<string, unknown>;
      ['Bank_Usage_Start_Month', 'Bank_Usage_Start_Year', 'Bank_Usage_End_Month', 'Bank_Usage_End_Year'].forEach(k => {
        if (payload[k] === '') payload[k] = null;
        else if (payload[k] !== null && payload[k] !== undefined) payload[k] = parseInt(String(payload[k]));
      });
      const res = await fetch(`${API_BASE}/timeframes/${id}/variables`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const swRes = await fetch(`${API_BASE}/timeframes/${id}/shutdown_windows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ windows: shutdownWindows })
      });
      const clRes = await fetch(`${API_BASE}/timeframes/${id}/custom_losses`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ losses: customLosses.map(cl => ({...cl, Loss_Pct: parseFloat(cl.Loss_Pct) || 0})) })
      });
      if(!res.ok || !swRes.ok || !clRes.ok) {
         setErrorMsg("Failed to save variables, shutdown windows, or custom losses.");
         setSaving(false);
         return;
      }
      const fileTypes = Object.keys(stagedFiles);
      for(const type of fileTypes) {
        setUploading(type);
        const file = stagedFiles[type];
        const formData = new FormData();
        formData.append("file", file);
        try {
          const upRes = await fetch(`${API_BASE}/timeframes/${id}/upload/${type}`, {
            method: 'POST',
            body: formData
          });
          const data = await upRes.json();
          if(!data.success) {
            setErrorMsg(`Error on ${type}: ${data.error}`);
            setSaving(false);
            setUploading(null);
            return;
          }
        } catch {
          setErrorMsg(`Server Error uploading ${type}`);
          setSaving(false);
          setUploading(null);
          return;
        }
      }
      setStagedFiles({});
      setUploading(null);
      loadStatus();
      toast.success("Variables and files saved successfully!");
      router.push(`/settlement/${id}/report`);
    } catch {
      setErrorMsg("An unexpected network error occurred.");
    } finally {
      setSaving(false);
      setUploading(null);
    }
  };
  const addShutdownWindow = () => {
    setShutdownWindows([...shutdownWindows, { Window_Start: '', Window_End: '' }]);
  };
  const removeShutdownWindow = (index: number) => {
    const newWindows = [...shutdownWindows];
    newWindows.splice(index, 1);
    setShutdownWindows(newWindows);
  };
  const handleShutdownWindowChange = (index: number, field: string, value: string) => {
    const newWindows = [...shutdownWindows];
    newWindows[index] = { ...newWindows[index], [field]: value };
    setShutdownWindows(newWindows);
  };
  const addCustomLoss = () => {
    setCustomLosses([...customLosses, { Window_Start: '', Window_End: '', Loss_Pct: '' }]);
  };
  const removeCustomLoss = (index: number) => {
    const newLosses = [...customLosses];
    newLosses.splice(index, 1);
    setCustomLosses(newLosses);
  };
  const handleCustomLossChange = (index: number, field: string, value: string) => {
    const newLosses = [...customLosses];
    newLosses[index] = { ...newLosses[index], [field]: value };
    setCustomLosses(newLosses);
  };
  const stageFile = (e: React.ChangeEvent<HTMLInputElement>, fileType: string) => {
    if(!e.target.files || e.target.files.length === 0) return;
    setStagedFiles({ ...stagedFiles, [fileType]: e.target.files[0] });
    e.target.value = '';
  };
  const removeStagedFile = (fileType: string) => {
    const newStaged = { ...stagedFiles };
    delete newStaged[fileType];
    setStagedFiles(newStaged);
  };
  const renderUploadBox = (title: string, type: string, description: string) => {
    const isDone = status[type] === 'COMPLETED';
    const isWorking = uploading === type;
    const stagedFile = stagedFiles[type];
    return (
      <div className={`border rounded-xl p-6 relative overflow-hidden transition-all ${isDone && !stagedFile ? 'border-green-200 bg-green-50/30' : 'border-slate-200 bg-white hover:border-primary/30 hover:shadow-md'}`}>
        {isDone && !stagedFile && <div className="absolute top-0 right-0 w-16 h-16 bg-green-100 rounded-bl-full flex items-start justify-end p-2"><CheckCircle2 className="w-5 h-5 text-green-600" /></div>}
        <h3 className="font-semibold text-lg text-slate-800 mb-1">{title}</h3>
        <p className="text-sm text-slate-500 mb-6">{description}</p>
        {isWorking ? (
          <div className="flex items-center justify-center gap-3 py-4 text-primary font-medium animate-pulse">
            <RefreshCw className="w-5 h-5 animate-spin" /> Uploading & Parsing...
          </div>
        ) : stagedFile ? (
          <div className="flex items-center justify-between p-4 bg-slate-50 border border-slate-200 rounded-lg">
            <span className="text-sm font-medium text-slate-700 truncate flex-1 pr-2" title={stagedFile.name}>{stagedFile.name}</span>
            <Button type="button" variant="ghost" size="sm" onClick={() => removeStagedFile(type)} className="text-red-500 hover:text-red-700 hover:bg-red-50 flex-shrink-0">
              <AlertCircle className="w-4 h-4 mr-2" /> Discard
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            <Label htmlFor={type} className="cursor-pointer border-2 border-dashed border-slate-300 rounded-lg py-8 text-center hover:bg-slate-50 hover:border-primary/50 transition-colors">
              <div className="flex flex-col items-center gap-2">

                <UploadCloud className="w-8 h-8 text-slate-400" />
                <span className="text-sm font-medium text-slate-600">Click to browse file</span>
              </div>
              <input id={type} type="file" className="hidden" accept=".xlsx,.xls,.cdf" onChange={e => stageFile(e, type)} />
            </Label>
          </div>
        )}
      </div>
    );
  };
  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 p-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="xl:col-span-5 space-y-6">
        <Card className="shadow-lg border-slate-200">
          <CardHeader className="bg-slate-50 border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-xl">
              <Settings2 className="w-5 h-5 text-primary" />
              Settlement Variables
            </CardTitle>
            <CardDescription>Configure the mathematical variables required for this specific month&apos;s calculation engine.</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <form id="variables-form" onSubmit={saveAll} className="space-y-6">
              <div className="space-y-4 border-b border-slate-100 pb-6">
                <h4 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Share Allocations</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label>Share TPT145 (%)</Label><Input type="number" step="0.01" name="Share_Cons1" value={vars.Share_Cons1} onChange={handleVarChange} required /></div>
                  <div className="space-y-2"><Label>Share CTR2005 (%)</Label><Input type="number" step="0.01" name="Share_Cons2" value={vars.Share_Cons2} onChange={handleVarChange} required /></div>
                </div>
              </div>
              <div className="space-y-4 border-b border-slate-100 pb-6">
                <h4 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Banked Energy Usage Range</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="space-y-2">
                    <Label>Start Month</Label>
                    <select name="Bank_Usage_Start_Month" value={vars.Bank_Usage_Start_Month || ''} onChange={handleVarChange} className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                      <option value="">None</option>
                      {Array.from({length: 12}, (_, i) => <option key={i+1} value={i+1}>{new Date(0, i).toLocaleString('default', { month: 'long' })}</option>)}
                    </select>
                  </div>
                  <div className="space-y-2"><Label>Start Year</Label><Input type="number" name="Bank_Usage_Start_Year" value={vars.Bank_Usage_Start_Year || ''} onChange={handleVarChange} /></div>
                  <div className="space-y-2">
                    <Label>End Month</Label>
                    <select name="Bank_Usage_End_Month" value={vars.Bank_Usage_End_Month || ''} onChange={handleVarChange} className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                      <option value="">None</option>
                      {Array.from({length: 12}, (_, i) => <option key={i+1} value={i+1}>{new Date(0, i).toLocaleString('default', { month: 'long' })}</option>)}
                    </select>
                  </div>
                  <div className="space-y-2"><Label>End Year</Label><Input type="number" name="Bank_Usage_End_Year" value={vars.Bank_Usage_End_Year || ''} onChange={handleVarChange} /></div>
                </div>
                <div className="grid grid-cols-2 gap-4 pt-2">
                  <div className="space-y-2"><Label>Bank Loss (%)</Label><Input type="number" step="0.01" name="Bank_Loss_Pct" value={vars.Bank_Loss_Pct} onChange={handleVarChange} required /></div>
                </div>
              </div>
              <div className="space-y-4 pb-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Generator Shutdown Windows</h4>
                  <Button type="button" variant="outline" size="sm" onClick={addShutdownWindow}>+ Add Window</Button>
                </div>
                {shutdownWindows.length === 0 ? (
                  <p className="text-sm text-slate-500 italic">No shutdown windows added.</p>
                ) : (
                  <div className="space-y-3">
                    {shutdownWindows.map((win, idx) => (
                      <div key={idx} className="flex items-end gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg">
                        <div className="space-y-1 flex-1">
                          <Label className="text-xs">Start (DD-MM-YYYY HH:MM)</Label>
                          <Input
                            value={win.Window_Start}
                            onChange={(e) => handleShutdownWindowChange(idx, 'Window_Start', e.target.value)}
                            placeholder="e.g. 16-01-2026 09:30"
                            required
                          />
                        </div>
                        <div className="space-y-1 flex-1">
                          <Label className="text-xs">End (DD-MM-YYYY HH:MM)</Label>
                          <Input
                            value={win.Window_End}
                            onChange={(e) => handleShutdownWindowChange(idx, 'Window_End', e.target.value)}
                            placeholder="e.g. 16-01-2026 21:15"
                            required
                          />
                        </div>
                        <Button type="button" variant="destructive" size="icon" onClick={() => removeShutdownWindow(idx)}>
                          <AlertCircle className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="space-y-4 pb-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-slate-800 uppercase tracking-wider">Custom Loss Windows</h4>
                  <Button type="button" variant="outline" size="sm" onClick={addCustomLoss}>+ Add Loss Window</Button>
                </div>
                {customLosses.length === 0 ? (
                  <p className="text-sm text-slate-500 italic">No custom losses added. (Warning: Calculations will fail if blocks are not covered!)</p>
                ) : (
                  <div className="space-y-3">
                    {customLosses.map((win, idx) => (
                      <div key={idx} className="flex items-end gap-3 p-3 bg-slate-50 border border-slate-200 rounded-lg">
                        <div className="space-y-1 flex-1">
                          <Label className="text-xs">Start Date</Label>
                          <Input
                            type="date"
                            value={win.Window_Start}
                            onChange={(e) => handleCustomLossChange(idx, 'Window_Start', e.target.value)}
                            required
                          />
                        </div>
                        <div className="space-y-1 flex-1">
                          <Label className="text-xs">End Date</Label>
                          <Input
                            type="date"
                            value={win.Window_End}
                            onChange={(e) => handleCustomLossChange(idx, 'Window_End', e.target.value)}
                            required
                          />
                        </div>
                        <div className="space-y-1 w-24 flex-shrink-0">
                          <Label className="text-xs">Loss (%)</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={win.Loss_Pct}
                            onChange={(e) => handleCustomLossChange(idx, 'Loss_Pct', e.target.value)}
                            placeholder="2.88"
                            required
                          />
                        </div>
                        <Button type="button" variant="destructive" size="icon" onClick={() => removeCustomLoss(idx)}>
                          <AlertCircle className="w-4 h-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </form>
          </CardContent>
        </Card>
      </div>
      <div className="xl:col-span-7 space-y-6">
        <Card className="shadow-lg border-slate-200">
          <CardHeader className="bg-slate-50 border-b border-slate-100 pb-4">
            <CardTitle className="flex items-center gap-2 text-xl">
              <UploadCloud className="w-5 h-5 text-primary" />
              Data Source Ingestion
            </CardTitle>
            <CardDescription>Upload strictly verified CDF and IEX `.xlsx` files for this specific timeframe.</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {renderUploadBox("Generator CDF", "gen_cdf", "Upload the Gen-side CDF format file.")}
              {renderUploadBox("TPT145 CDF", "con1_cdf", "Upload TPT145 CDF format file.")}
              {renderUploadBox("CTR2005 CDF", "con2_cdf", "Upload CTR2005 CDF format file.")}
              {renderUploadBox("IEX Data (TPT145)", "iex1", "Upload IEX blockwise .xlsx file for TPT145.")}
              {renderUploadBox("IEX Data (CTR2005)", "iex2", "Upload IEX blockwise .xlsx file for CTR2005.")}
            </div>
            <div className="mt-8 p-4 bg-amber-50 border border-amber-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-amber-800">
                <p className="font-semibold mb-1">Strict Date Filtering is Active</p>
                <p>Any rows inside these files that do not fall exactly within this Timeframe&apos;s Start and End dates will be permanently discarded during upload.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      <div className="xl:col-span-12 mt-4 flex justify-end">
        <Button
          type="button"
          onClick={() => saveAll()}
          disabled={saving || uploading !== null}
          className="w-full md:w-auto px-12 text-lg h-14 shadow-xl shadow-primary/20 bg-primary hover:bg-primary/90 rounded-full"
        >
          {saving || uploading !== null ? 'Processing...' : 'Save Variables & Upload Files'}
        </Button>
      </div>
    </div>
  );
}
