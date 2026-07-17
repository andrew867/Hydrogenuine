// Operator-identity view model for the new UX — mirrors the backend
// hg-operator-identity receipt block (display-safe; never carries tokens).
export type OperatorAssurance =
  | "password"
  | "otp"
  | "webauthn"
  | "fido2"
  | "x509_smartcard"
  | "demo_local"
  | "unknown";

export type OperatorIdentityView = {
  provider: "keycloak" | "demo_local";
  subject: string; // Keycloak sub UUID — the identity key
  display_name: string;
  email?: string;
  roles: string[];
  session_id_hash?: string; // sha256 only
  assurance_level: OperatorAssurance;
  step_up_required: boolean;
  step_up_satisfied: boolean;
  production_operator_auth: boolean;
  demo_local_signing: boolean;
};

export type OperatorAuthState =
  | { status: "unauthenticated" }
  | { status: "authenticated"; identity: OperatorIdentityView }
  | { status: "step_up_required"; identity: OperatorIdentityView; reason: string }
  | { status: "lockdown"; reason: string }; // future PC/SC lane placeholder

export function parseOperatorIdentity(data: unknown): OperatorIdentityView | null {
  if (!data || typeof data !== "object") return null;
  const r = data as Record<string, unknown>;
  if (!r.subject || !r.provider) return null;
  return {
    provider: r.provider === "keycloak" ? "keycloak" : "demo_local",
    subject: String(r.subject),
    display_name: String(r.display_name ?? ""),
    email: r.email ? String(r.email) : undefined,
    roles: Array.isArray(r.roles) ? r.roles.map(String) : [],
    session_id_hash: r.session_id_hash ? String(r.session_id_hash) : undefined,
    assurance_level: (String(r.assurance_level ?? "unknown") as OperatorAssurance),
    step_up_required: Boolean(r.step_up_required),
    step_up_satisfied: Boolean(r.step_up_satisfied),
    production_operator_auth: Boolean(r.production_operator_auth),
    demo_local_signing: Boolean(r.demo_local_signing),
  };
}

// The client must never receive raw tokens; this guard makes that testable.
export function containsRawToken(value: unknown): boolean {
  return JSON.stringify(value ?? "").includes("eyJ");
}
