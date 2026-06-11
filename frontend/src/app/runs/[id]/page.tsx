import { Suspense } from "react";

import { RunDetailView } from "@/components/run-detail";
import { LoadingState } from "@/components/ui";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <Suspense fallback={<LoadingState label="Loading run" />}>
      <RunDetailView runId={id} />
    </Suspense>
  );
}

