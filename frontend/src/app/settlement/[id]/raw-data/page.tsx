"use client";
import React from 'react';
export default function RawDataPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  const API_BASE = "/api/v1";
  const exportRawGen = `${API_BASE}/timeframes/${id}/export?type=raw_gen`;
  const exportRawCon = `${API_BASE}/timeframes/${id}/export?type=raw_con`;
  const exportCalculated = `${API_BASE}/timeframes/${id}/export?type=calculated`;
  const exportHistoryWorkbook = `${API_BASE}/timeframes/${id}/export?type=history_workbook`;
  return (
    <div className="space-y-6 max-w-4xl">
      <h2 className="text-xl font-semibold mb-4 text-slate-800">Block-wise Data Exports</h2>
      <p className="text-slate-600 mb-8">
        Download the exact block-wise (15-minute intervals) data that has been parsed and stored in the database.
        Use these files to verify the integrity of the uploaded data before running the final calculation.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 text-center flex flex-col items-center">
          <div className="h-12 w-12 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-4 text-xl">⚡</div>
          <h3 className="font-semibold text-lg mb-2">Raw Generator Blocks</h3>
          <p className="text-sm text-slate-500 mb-6 flex-grow">All parsed 15-min generator Active KW data within the timeframe.</p>
          <a href={exportRawGen} download className="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 transition-all w-full text-center shadow-sm">
            Download Excel
          </a>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 text-center flex flex-col items-center">
          <div className="h-12 w-12 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mb-4 text-xl">🏭</div>
          <h3 className="font-semibold text-lg mb-2">Raw Consumer Blocks</h3>
          <p className="text-sm text-slate-500 mb-6 flex-grow">All parsed 15-min consumer Apparent KVA and Active KW data.</p>
          <a href={exportRawCon} download className="bg-emerald-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-emerald-700 transition-all w-full text-center shadow-sm">
            Download Excel
          </a>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 text-center flex flex-col items-center">
          <div className="h-12 w-12 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center mb-4 text-xl">🧮</div>
          <h3 className="font-semibold text-lg mb-2">Calculated Blocks</h3>
          <p className="text-sm text-slate-500 mb-6 flex-grow">Intermediate block-wise mathematical allocations after calculation.</p>
          <a href={exportCalculated} download className="bg-purple-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-purple-700 transition-all w-full text-center shadow-sm">
            Download Excel
          </a>
        </div>
      </div>
      <div className="mt-8 bg-slate-900 p-8 rounded-2xl shadow-xl flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white mb-2 flex items-center gap-2">
            <span className="text-2xl">📚</span> Full History Workbook
          </h3>
          <p className="text-slate-300">
            Download a single, consolidated Excel workbook containing all Raw Generator, Raw Consumer, IEX, and Calculated blocks separated by sheets.
          </p>
        </div>
        <a href={exportHistoryWorkbook} download className="bg-white text-slate-900 px-8 py-3 rounded-xl font-bold hover:bg-slate-100 hover:scale-105 transition-all shadow-md shrink-0">
          Download Workbook
        </a>
      </div>
    </div>
  );
}
