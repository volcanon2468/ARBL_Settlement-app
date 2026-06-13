import { redirect } from 'next/navigation';
export default function TimeframeIndex({ params }: { params: { id: string } }) {
  redirect(`/settlement/${params.id}/inputs`);
}
