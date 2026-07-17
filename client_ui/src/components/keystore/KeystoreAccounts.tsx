"use client";

import { useQuery } from "@tanstack/react-query";
import { hgApi } from "@/lib/hgApi";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export function KeystoreAccounts() {
  const { data: items = [], isLoading, error } = useQuery({
    queryKey: ["keystore-accounts"],
    queryFn: () => hgApi.listKeystoreAccounts(),
  });

  if (isLoading) return <p className="text-sm text-muted-foreground">Loading accounts…</p>;
  if (error) return <p className="text-sm text-destructive">Failed to load accounts.</p>;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Keystore accounts</h3>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No social accounts linked. Start supervised login to add one.</p>
      ) : (
        <div className="grid gap-2">
          {items.map((acc) => (
            <Card key={acc.social_account_id} className="p-3 flex items-center justify-between">
              <span className="text-sm font-medium">{acc.platform} · {acc.account_alias}</span>
              <span className="text-xs text-muted-foreground">{acc.state}</span>
              <Button disabled className="px-2 py-1 text-xs">Start supervised login</Button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
