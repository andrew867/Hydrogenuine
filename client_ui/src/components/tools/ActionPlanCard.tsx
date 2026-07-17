"use client";

import { Card } from "@/components/ui/Card";

/** Client action plan card and approval-required banner (Social Media Entity Tools). */
export function ActionPlanCard({
  plan,
  pending,
  proofLink,
}: {
  plan?: { proposed_steps?: unknown[]; required_approvals?: string[] };
  pending?: boolean;
  proofLink?: string | null;
}) {
  return (
    <Card className="p-4">
      {pending ? (
        <div className="text-sm font-medium text-amber-600">Approval required — waiting on operator</div>
      ) : proofLink ? (
        <div className="text-sm">
          <span className="text-muted-foreground">Completed. </span>
          <a href={proofLink} className="text-primary underline">View proof</a>
        </div>
      ) : plan?.proposed_steps?.length ? (
        <div className="text-sm">
          <div className="font-medium mb-1">Plan</div>
          <ul className="list-disc list-inside text-muted-foreground">
            {(plan.proposed_steps as { description?: string }[]).slice(0, 5).map((s, i) => (
              <li key={i}>{s.description ?? "Step"}</li>
            ))}
          </ul>
          {plan.required_approvals?.length ? (
            <div className="mt-2 text-amber-600">Approval required</div>
          ) : null}
        </div>
      ) : (
        <div className="text-sm text-muted-foreground">No plan yet.</div>
      )}
    </Card>
  );
}
