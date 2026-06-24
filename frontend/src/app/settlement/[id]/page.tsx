import React from 'react';
import { redirect } from 'next/navigation';
export default function TimeframeIndex({ params }: { params: Promise<{ id: string }> }) {
  // Next 14 / 15+ Compatibility
  const resolvedParams = params as any;
  const id = resolvedParams.then ? (React.use(resolvedParams) as any).id : resolvedParams.id;
  redirect(`/settlement/${id}/inputs`);
}
