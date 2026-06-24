"use client";
import { toast } from 'sonner';
import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import logoImage from '../icon.png';

import { Lock, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
export default function LoginPage() {
  const [password, setPassword] = useState('');
  const setError = (msg: string | null) => { if (msg) toast.error(msg); };
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      });
      const data = await res.json();
      if (res.ok) {

        toast.success("Access Granted.");
        router.push('/settlement');
      } else {
        setError(data.detail || 'Invalid password. Please try again.');
      }
    } catch {
      setError('A network error occurred. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-slate-50 relative overflow-hidden">
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-blue-500/10 blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-500/10 blur-[120px] pointer-events-none" />
      <div className="w-full max-w-md p-8 relative z-10">
        <div className="bg-white border border-slate-200 rounded-3xl p-8 shadow-xl">
          <div className="flex flex-col items-center mb-10">
            <img src={logoImage.src} alt="Company Logo" className="w-24 h-auto mb-6" />
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight text-center">Settlement App</h1>
            <p className="text-slate-500 mt-2 text-sm text-center">Enter the master password to access the energy ledger</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-6">
            <div className="space-y-2">
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <Input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-12 h-14 bg-white border-slate-300 text-slate-900 placeholder:text-slate-400 focus-visible:ring-blue-500 rounded-xl"
                  required
                />
              </div>
            </div>
            <Button
              type="submit"
              className="w-full h-14 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-xl group transition-all"
              disabled={loading}
            >
              {loading ? 'Authenticating...' : 'Access Dashboard'}
              {!loading && <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
