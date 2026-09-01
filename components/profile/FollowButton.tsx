"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";

export function FollowButton({
  username,
  initialFollowing,
}: {
  username: string;
  initialFollowing: boolean;
}) {
  const router = useRouter();
  const [following, setFollowing] = useState(initialFollowing);
  const [pending, setPending] = useState(false);

  async function toggle() {
    setPending(true);
    const response = await fetch(`/api/users/${username}/follow`, {
      method: following ? "DELETE" : "POST",
    });
    setPending(false);
    if (!response.ok) return;
    setFollowing(!following);
    router.refresh();
  }

  return (
    <Button onClick={() => void toggle()} disabled={pending}>
      {following ? "Following" : "Follow"}
    </Button>
  );
}
