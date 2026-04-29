"use client";

import { Suspense } from "react";
import { PurchaseCompleteView } from "@/features/hub/views/PurchaseCompleteView";

export default function PurchaseCompletePage() {
  return (
    <Suspense fallback={null}>
      <PurchaseCompleteView />
    </Suspense>
  );
}
