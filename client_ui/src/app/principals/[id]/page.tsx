import { PrincipalDetailView } from "@/components/principals/PrincipalDetailView";

export default async function PrincipalDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PrincipalDetailView id={id} />;
}
