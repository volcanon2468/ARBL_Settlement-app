"use client";
import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { toast } from 'sonner';
import { usePathname } from 'next/navigation';
import { ArrowLeft, Clock } from 'lucide-react';

export interface Timeframe {
  Id: number;
  Label: string;
  Start_Date: string;
  End_Date: string;
  Status: string;
  [key: string]: any;
}

export default function TimeframeLayout({ params, children }: { params: { id: string }, children: React.ReactNode }) {
  const [timeframe, setTimeframe] = useState<Timeframe | null>(null);
  const pathname = usePathname();
  const API_BASE = "/api/v1";

  const loadTimeframe = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/timeframes/${params.id}`);
      if (!res.ok) throw new Error("Failed to fetch timeframe metadata");
      const data = await res.json();
      if(data.success) {
        setTimeframe(data.data);
      } else {
        toast.error("Failed to load timeframe data from server.");
      }
    } catch(err) {
      console.error(err);
      toast.error("Network error: Could not load timeframe details. Please check your connection.");
    }
  }, [params.id]);

  useEffect(() => {
    loadTimeframe();
  }, [loadTimeframe]);
  return (
    <div className="min-h-screen bg-background p-8 md:p-12 animate-in">
      <div className="max-w-7xl mx-auto space-y-8">
        {timeframe ? (
          <div className="space-y-6">
            <Link href="/settlement" className="inline-flex items-center text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Link>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-b pb-6">
              <div>
                <h1 className="text-4xl font-extrabold tracking-tight mb-2 text-foreground flex items-center gap-3">
                  {timeframe.Label}
                </h1>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>{timeframe.Start_Date} to {timeframe.End_Date}</span>
                  <span className="mx-2">•</span>
                  <span>Status: </span>
                  <span className={`font-semibold ${timeframe.Status === 'COMPLETE' ? 'text-green-600' : 'text-blue-600'}`}>
                    {timeframe.Status || 'PENDING'}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex gap-2 mb-8">
              <Link
                href={`/settlement/${params.id}/inputs`}
                className={`py-2 px-6 rounded-full font-medium transition-all ${pathname.includes('/inputs') ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:bg-secondary'}`}
              >
                1. Setup & Upload
              </Link>
              <Link
                href={`/settlement/${params.id}/report`}
                className={`py-2 px-6 rounded-full font-medium transition-all ${pathname.includes('/report') ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:bg-secondary'}`}
              >
                2. Settlement Report
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
             <Link href="/settlement" className="inline-flex items-center text-sm font-medium text-muted-foreground hover:text-primary transition-colors">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Link>
             <div className="animate-pulse flex flex-col md:flex-row justify-between items-start md:items-end gap-6 border-b pb-6">
               <div>
                 <div className="h-10 w-64 bg-slate-200 rounded-lg mb-4"></div>
                 <div className="flex gap-2">
                   <div className="h-4 w-40 bg-slate-100 rounded"></div>
                   <div className="h-4 w-24 bg-slate-100 rounded"></div>
                 </div>
               </div>
             </div>
             <div className="flex gap-2 mb-8 animate-pulse">
               <div className="h-10 w-40 bg-slate-200 rounded-full"></div>
               <div className="h-10 w-48 bg-slate-200 rounded-full"></div>
             </div>
          </div>
        )}
        <main className="bg-white/50 backdrop-blur-sm rounded-2xl shadow-sm border border-slate-100 p-1">
          {children}
        </main>
      </div>
    </div>
  );
}
