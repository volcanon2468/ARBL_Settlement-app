"use client";
import React, { useState } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ArrowLeft, DownloadCloud, Zap, Factory, Calculator, CalendarRange } from 'lucide-react';
import logoImage from '../../icon.png';
export default function GlobalRawDataPage() {
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const API_BASE = "/api/v1";
  const getExportUrl = (type: string) => {
    if (!startDate || !endDate) return '#';
    return `${API_BASE}/export/daterange?start=${startDate}&end=${endDate}&type=${type}`;
  };
  const isReady = startDate && endDate;
  return (
    <div className="min-h-screen bg-background p-8 md:p-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="max-w-5xl mx-auto space-y-10">
        <header className="relative overflow-hidden rounded-3xl bg-slate-900 text-white p-8 md:p-12 shadow-2xl space-y-6">
          <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
            <DownloadCloud className="w-64 h-64 text-white" />
          </div>
          <Link href="/settlement" className="relative z-10 inline-flex items-center text-sm font-medium text-slate-400 hover:text-white transition-colors bg-white/10 px-4 py-2 rounded-full w-fit backdrop-blur-md border border-white/10">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Link>
          <div className="relative z-10 flex items-center gap-6">
            <img src={logoImage.src} alt="Company Logo" className="w-16 md:w-20 h-auto drop-shadow-md bg-white rounded-full p-1 shrink-0" />
            <div>
              <h1 className="text-4xl font-extrabold tracking-tight mb-3 text-white flex items-center gap-3">
                Global Data Export
              </h1>
              <p className="text-lg text-slate-300 max-w-2xl">Extract raw and calculated block-wise data across any arbitrary date range spanning multiple months.</p>
            </div>
          </div>
        </header>
        <Card className="border-primary/10 shadow-md">
          <CardHeader className="bg-slate-50 border-b border-slate-100">
            <CardTitle className="flex items-center gap-2">
              <CalendarRange className="w-5 h-5 text-primary" />
              Define Date Range
            </CardTitle>
            <CardDescription>Select the exact continuous boundary to extract data from the database.</CardDescription>
          </CardHeader>
          <CardContent className="pt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-2xl">
              <div className="space-y-2">
                <Label htmlFor="start" className="text-sm font-semibold uppercase tracking-wider text-slate-500">Start Date</Label>
                <Input
                  id="start"
                  type="date"
                  className="h-12 text-lg"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end" className="text-sm font-semibold uppercase tracking-wider text-slate-500">End Date</Label>
                <Input
                  id="end"
                  type="date"
                  className="h-12 text-lg"
                  value={endDate}
                  onChange={e => setEndDate(e.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>
        <div className="space-y-6">
          <h2 className="text-2xl font-bold tracking-tight text-foreground">Available Exports</h2>
          {!isReady && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 px-6 py-4 rounded-xl flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              Please specify both Start and End dates to enable the extraction engines.
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <Card className={`relative overflow-hidden group transition-all duration-500 bg-white border-0 shadow-lg ${isReady ? 'hover:shadow-2xl hover:-translate-y-2' : 'opacity-60 cursor-not-allowed'}`}>
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-400 to-blue-600"></div>
              <CardContent className="p-10 flex flex-col items-center text-center h-full">
                <div className="h-20 w-20 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mb-6 shadow-inner group-hover:scale-110 transition-transform duration-500">
                  <Zap className="w-10 h-10" />
                </div>
                <h3 className="font-extrabold text-2xl mb-3 text-slate-800">Raw Generator</h3>
                <p className="text-slate-500 mb-10 flex-grow font-medium leading-relaxed">All aggregated 15-min generator Active KW data arrays.</p>
                <a href={getExportUrl('raw_gen')} onClick={(e) => !isReady && e.preventDefault()} className="w-full">
                  <Button disabled={!isReady} className="w-full h-14 text-lg font-bold bg-slate-900 text-white hover:bg-blue-600 shadow-xl rounded-xl transition-all">Extract Excel</Button>
                </a>
              </CardContent>
            </Card>
            <Card className={`relative overflow-hidden group transition-all duration-500 bg-white border-0 shadow-lg ${isReady ? 'hover:shadow-2xl hover:-translate-y-2' : 'opacity-60 cursor-not-allowed'}`}>
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-400 to-emerald-600"></div>
              <CardContent className="p-10 flex flex-col items-center text-center h-full">
                <div className="h-20 w-20 bg-emerald-50 text-emerald-600 rounded-2xl flex items-center justify-center mb-6 shadow-inner group-hover:scale-110 transition-transform duration-500">
                  <Factory className="w-10 h-10" />
                </div>
                <h3 className="font-extrabold text-2xl mb-3 text-slate-800">Raw Consumer</h3>
                <p className="text-slate-500 mb-10 flex-grow font-medium leading-relaxed">All parsed 15-min consumer Apparent KVA and KW data arrays.</p>
                <a href={getExportUrl('raw_con')} onClick={(e) => !isReady && e.preventDefault()} className="w-full">
                  <Button disabled={!isReady} className="w-full h-14 text-lg font-bold bg-slate-900 text-white hover:bg-emerald-600 shadow-xl rounded-xl transition-all">Extract Excel</Button>
                </a>
              </CardContent>
            </Card>
            <Card className={`relative overflow-hidden group transition-all duration-500 bg-white border-0 shadow-lg ${isReady ? 'hover:shadow-2xl hover:-translate-y-2' : 'opacity-60 cursor-not-allowed'}`}>
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-purple-400 to-purple-600"></div>
              <CardContent className="p-10 flex flex-col items-center text-center h-full">
                <div className="h-20 w-20 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center mb-6 shadow-inner group-hover:scale-110 transition-transform duration-500">
                  <Calculator className="w-10 h-10" />
                </div>
                <h3 className="font-extrabold text-2xl mb-3 text-slate-800">Calculated Blocks</h3>
                <p className="text-slate-500 mb-10 flex-grow font-medium leading-relaxed">Intermediate block-wise mathematical settlement allocations.</p>
                <a href={getExportUrl('calculated')} onClick={(e) => !isReady && e.preventDefault()} className="w-full">
                  <Button disabled={!isReady} className="w-full h-14 text-lg font-bold bg-slate-900 text-white hover:bg-purple-600 shadow-xl rounded-xl transition-all">Extract Excel</Button>
                </a>
              </CardContent>
            </Card>
          </div>
          <div className={`mt-8 relative overflow-hidden rounded-2xl shadow-xl flex flex-col md:flex-row items-center justify-between p-8 transition-all duration-500 ${isReady ? 'bg-slate-900 border-0' : 'bg-slate-800 opacity-60 cursor-not-allowed'}`}>
            <div className="absolute top-0 right-0 p-8 opacity-10 pointer-events-none">
              <DownloadCloud className="w-48 h-48 text-white" />
            </div>
            <div className="relative z-10 mb-6 md:mb-0">
              <h3 className="text-2xl font-bold text-white mb-2 flex items-center gap-3">
                <span className="text-3xl">📚</span> Full History Workbook
              </h3>
              <p className="text-slate-300 max-w-2xl">
                Download a single, consolidated Excel workbook containing all Raw Generator, Raw Consumer, IEX, and Calculated blocks separated by sheets for the selected date range.
              </p>
            </div>
            <a href={getExportUrl('history_workbook')} onClick={(e) => !isReady && e.preventDefault()} className="relative z-10 shrink-0">
              <Button disabled={!isReady} className="bg-white text-slate-900 px-8 py-6 rounded-xl font-bold text-lg hover:bg-slate-100 hover:scale-105 transition-all shadow-md">
                Download Workbook
              </Button>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
