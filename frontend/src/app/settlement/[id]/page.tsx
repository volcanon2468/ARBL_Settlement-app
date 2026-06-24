import React from 'react';
import { redirect } from 'next/navigation';
export default function TimeframeIndex({ params }: { params: Promise<{ id: string }> }) {
  const { id } = React.use(params);
  redirect(`/settlement/${id}/inputs`);
}
