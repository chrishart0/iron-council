import { PublicAgentProfilePage } from "../../../components/public/public-agent-profile-page";

type PublicAgentProfileRoutePageProps = {
  params: Promise<{
    agentId: string;
  }>;
};

export default async function PublicAgentProfileRoutePage({
  params
}: PublicAgentProfileRoutePageProps) {
  const { agentId } = await params;
  return <PublicAgentProfilePage agentId={agentId} />;
}
