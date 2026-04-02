import { PublicHumanProfilePage } from "../../../components/public/public-human-profile-page";

type PublicHumanProfileRoutePageProps = {
  params: Promise<{
    humanId: string;
  }>;
};

export default async function PublicHumanProfileRoutePage({
  params
}: PublicHumanProfileRoutePageProps) {
  const { humanId } = await params;
  return <PublicHumanProfilePage humanId={humanId} />;
}
