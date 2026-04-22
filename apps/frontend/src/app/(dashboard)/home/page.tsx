"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/**
 * Placeholder landing route. A real "Home" dashboard will live here later.
 * For now, forward signed-in + verified users to the existing Libraries page
 * so the auth redirect chain has a stable target.
 */
export default function HomePage() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/libraries");
  }, [router]);
  return null;
}
