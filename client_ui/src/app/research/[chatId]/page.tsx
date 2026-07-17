import { ResearchWorkspaceView } from "@/components/research/ResearchWorkspaceView";

export default async function ResearchWorkspacePage({ params }: { params: Promise<{ chatId: string }> }) {
  const { chatId } = await params;
  return <ResearchWorkspaceView chatId={chatId} />;
}
