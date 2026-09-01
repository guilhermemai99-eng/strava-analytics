import { redirect } from "next/navigation";
import { AuthScreen } from "@/components/auth/AuthScreen";
import { getCurrentUser } from "@/lib/auth";
import { oauthErrorMessage } from "@/lib/oauth-errors";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const user = await getCurrentUser();
  if (user) redirect("/");
  const { error } = await searchParams;
  return <AuthScreen oauthError={oauthErrorMessage(error)} />;
}
