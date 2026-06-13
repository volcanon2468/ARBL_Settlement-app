"use client";
import { toast } from 'sonner';
import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PlusCircle, CalendarDays, Activity, Trash2, Search } from 'lucide-react';
interface Timeframe {
  Id: number;
  Label: string;
  Status: string;
  [key: string]: any;
}
export default function SettlementDashboard() {
  const [timeframes, setTimeframes] = useState<Timeframe[]>([]);
  const [newMonth, setNewMonth] = useState('1');
  const [newYear, setNewYear] = useState(new Date().getFullYear().toString());
  const [searchTerm, setSearchTerm] = useState('');
  const [creating, setCreating] = useState(false);
  const setErrorMsg = (msg: string | null) => { if (msg) toast.error(msg); };
  const API_BASE = "/api/v1";
  const loadTimeframes = async () => {
    try {
      const res = await fetch(`${API_BASE}/timeframes`);
      if (!res.ok) throw new Error("Failed to fetch timeframes");
      const data = await res.json();
      if(data.success) {
        setTimeframes(data.data);
      } else {
        toast.error("Failed to load timeframes from server.");
      }
    } catch(e) {
      console.error("Error loading timeframes:", e);
      toast.error("Network error: Could not load timeframes. Please check your connection.");
    }
  };
  useEffect(() => {
    loadTimeframes();
  }, []);
  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setErrorMsg(null);
    try {
      const res = await fetch(`${API_BASE}/timeframes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ Month: parseInt(newMonth), Year: parseInt(newYear) })
      });
      if(res.ok) {
        toast.success("Timeframe created successfully!");
        loadTimeframes();
      } else {
        const errData = await res.json().catch(() => null);
        setErrorMsg(errData?.detail || "Failed to create timeframe. Please try again.");
      }
    } catch(e) {
      console.error(e);
      setErrorMsg("Network error. Please try again.");
    } finally {
      setCreating(false);
    }
  };
  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.preventDefault();
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this timeframe and all its associated data?")) return;
    try {
      const res = await fetch(`${API_BASE}/timeframes/${id}`, {
        method: 'DELETE'
      });
      if(res.ok) {
        toast.success("Timeframe deleted successfully.");
        loadTimeframes();
      } else {
        const data = await res.json();
        setErrorMsg(data.detail || "Failed to delete timeframe.");
      }
    } catch(err) {
      console.error("Error deleting timeframe:", err);
      setErrorMsg("Network error while deleting.");
    }
  };
  const filteredTimeframes = timeframes.filter((tf: Timeframe) =>
    String(tf.Label).toLowerCase().includes(searchTerm.toLowerCase())
  );
  return (
    <div className="min-h-screen bg-background p-8 md:p-12 animate-in">
      <div className="max-w-7xl mx-auto space-y-12">
        <header className="relative overflow-hidden rounded-3xl bg-slate-900 text-white p-8 md:p-12 shadow-2xl flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
            <Activity className="w-64 h-64 text-white" />
          </div>
          <div className="relative z-10">
            <h1 className="text-4xl font-extrabold tracking-tight lg:text-5xl mb-3 text-white">
              Energy Settlement
            </h1>
            <p className="text-lg text-slate-300 font-medium">APSPDCL Open-Access Management Platform</p>
          </div>
          <div className="relative z-10 flex flex-col md:flex-row gap-4">
            <Link href="/settlement/raw-data">
              <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 gap-2 shadow-xl font-bold rounded-xl h-14 px-8 transition-transform hover:scale-105">
                <Search className="w-5 h-5" /> Browse Database
              </Button>
            </Link>
            <Button size="lg" className="bg-slate-800 text-white hover:bg-slate-700 gap-2 font-bold rounded-xl h-14 px-8 transition-transform hover:scale-105" onClick={async () => {
              await fetch('/api/v1/auth/logout', { method: 'POST' });
              window.location.href = "/login";
            }}>
              Logout
            </Button>
          </div>
        </header>
        <Card className="glass border-primary/10">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-primary" />
              Create New Timeframe
            </CardTitle>
            <CardDescription>Initialize a new monthly settlement period to begin uploading data.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleCreate} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-6 items-end">
              <div className="lg:col-span-4 space-y-2">
                <Label htmlFor="month">Month</Label>
                <select
                  id="month"
                  value={newMonth}
                  onChange={e => setNewMonth(e.target.value)}
                  className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="1">January</option>
                  <option value="2">February</option>
                  <option value="3">March</option>
                  <option value="4">April</option>
                  <option value="5">May</option>
                  <option value="6">June</option>
                  <option value="7">July</option>
                  <option value="8">August</option>
                  <option value="9">September</option>
                  <option value="10">October</option>
                  <option value="11">November</option>
                  <option value="12">December</option>
                </select>
              </div>
              <div className="lg:col-span-4 space-y-2">
                <Label htmlFor="year">Year</Label>
                <Input id="year" type="number" required value={newYear} onChange={e => setNewYear(e.target.value)} />
              </div>
              <div className="lg:col-span-4">
                <Button type="submit" className="w-full" disabled={creating}>
                  {creating ? "Creating..." : "Create Timeframe"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
        <div>
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
            <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <CalendarDays className="w-6 h-6 text-slate-400" />
              Existing Timeframes
            </h2>
            <div className="relative w-full sm:w-72">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-slate-400" />
              </div>
              <Input
                placeholder="Search by label (e.g. Jan)..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-10 w-full bg-white shadow-sm"
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredTimeframes.length === 0 && (
              <div className="col-span-full py-12 text-center text-muted-foreground bg-slate-50 rounded-xl border border-dashed border-slate-200">
                {timeframes.length === 0 ? "No timeframes created yet. Start by creating one above." : "No timeframes match your search."}
              </div>
            )}
            {filteredTimeframes.map((tf: Timeframe) => (
              <Link href={`/settlement/${tf.Id}`} key={String(tf.Id)}>
                <Card className="hover:shadow-2xl hover:-translate-y-1 hover:border-primary/50 transition-all duration-300 cursor-pointer group h-full flex flex-col bg-white border-slate-200/60 shadow-md rounded-2xl overflow-hidden relative">
                  <div className={`absolute top-0 left-0 w-1 h-full ${tf.Status === 'COMPLETE' ? 'bg-green-500' : 'bg-blue-500'}`}></div>
                  <div className="absolute top-3 right-3 z-20">
                    <button
                      onClick={(e) => handleDelete(e, tf.Id)}
                      className="text-slate-400 hover:text-red-500 transition-colors p-2 rounded-full hover:bg-red-50"
                      title="Delete Timeframe"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <CardHeader className="bg-slate-50/50 border-b border-slate-100 pb-4">
                    <CardTitle className="group-hover:text-primary transition-colors text-xl font-bold flex items-center justify-between">
                      {tf.Label}
                      <span className="bg-white shadow-sm border border-slate-200 text-slate-600 rounded-full w-8 h-8 flex items-center justify-center">
                        <CalendarDays className="w-4 h-4" />
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-grow pt-6">
                    <div className="flex items-center gap-3 text-sm">
                      <div className={`p-2 rounded-full ${tf.Status === 'COMPLETE' ? 'bg-green-100' : 'bg-blue-100'}`}>
                        <Activity className={`w-4 h-4 ${tf.Status === 'COMPLETE' ? 'text-green-600' : 'text-blue-600'}`} />
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wider">Current Status</span>
                        <span className={`font-bold text-base ${tf.Status === 'COMPLETE' ? 'text-green-600' : 'text-blue-600'}`}>
                          {tf.Status || 'PENDING UPLOAD'}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
