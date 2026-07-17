import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { AuthStatusBadge } from "../AuthStatusBadge";
import { OperatorIdentityCard } from "../OperatorIdentityCard";
import { StepUpRequiredBanner } from "../StepUpRequiredBanner";
import {
  ApprovalDisabledReason,
  approvalControlsEnabled,
  approvalDisabledReason,
} from "../ApprovalDisabledReason";
import {
  parseOperatorIdentity,
  containsRawToken,
  type OperatorAuthState,
  type OperatorIdentityView,
} from "../../auth/operatorIdentity";
import { computeStepUp } from "../../auth/useStepUp";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const kcIdentity: OperatorIdentityView = {
  provider: "keycloak",
  subject: "11111111-2222-3333-4444-555555555555",
  display_name: "Demo Operator",
  email: "demo-operator@example.local",
  roles: ["hg.operator", "hg.approver"],
  session_id_hash: "sha256:" + "a".repeat(64),
  assurance_level: "password",
  step_up_required: false,
  step_up_satisfied: false,
  production_operator_auth: true,
  demo_local_signing: false,
};

describe("KLR operator-auth UI kit components", () => {
  it("case 20: unauthenticated state disables approval controls", () => {
    const state: OperatorAuthState = { status: "unauthenticated" };
    expect(approvalControlsEnabled(state)).toBe(false);
    expect(approvalDisabledReason(state)).toMatch(/sign in/i);
    render(<AuthStatusBadge state={state} />);
    expect(screen.getByText("Signed out")).toBeInTheDocument();
  });

  it("case 21: authenticated operator identity is visible", () => {
    const state: OperatorAuthState = { status: "authenticated", identity: kcIdentity };
    expect(approvalControlsEnabled(state)).toBe(true);
    render(<OperatorIdentityCard identity={kcIdentity} />);
    expect(screen.getByText("Demo Operator")).toBeInTheDocument();
    expect(screen.getByText("keycloak-verified")).toBeInTheDocument();
    // subject shown truncated; session shown hashed
    expect(screen.getByText(/11111111/)).toBeInTheDocument();
  });

  it("case 22: step-up required state renders", () => {
    render(<StepUpRequiredBanner reason="step_up_missing" riskCategory="high" />);
    expect(screen.getByText("Step-up required")).toBeInTheDocument();
    expect(screen.getByText(/re-authentication/i)).toBeInTheDocument();
    const state: OperatorAuthState = {
      status: "step_up_required", identity: kcIdentity, reason: "step_up_missing",
    };
    expect(approvalControlsEnabled(state)).toBe(false);
    render(<ApprovalDisabledReason state={state} />);
    expect(screen.getByText("step_up_missing")).toBeInTheDocument();
  });

  it("demo-local is always flagged, never production", () => {
    const demo: OperatorIdentityView = {
      ...kcIdentity, provider: "demo_local", demo_local_signing: true,
      production_operator_auth: false, assurance_level: "demo_local",
    };
    render(<AuthStatusBadge state={{ status: "authenticated", identity: demo }} />);
    expect(screen.getByText(/demo-local/i)).toBeInTheDocument();
  });

  it("step-up derivation never fabricates satisfied", () => {
    expect(computeStepUp({ ...kcIdentity, step_up_required: true, step_up_satisfied: false }))
      .toEqual({ required: true, satisfied: false, needsReauth: true });
    expect(computeStepUp({ ...kcIdentity, step_up_required: true, step_up_satisfied: true }))
      .toEqual({ required: true, satisfied: true, needsReauth: false });
  });

  it("parses identity and rejects raw tokens", () => {
    expect(parseOperatorIdentity({ provider: "keycloak", subject: "x", roles: [] }))
      .not.toBeNull();
    expect(parseOperatorIdentity(null)).toBeNull();
    expect(containsRawToken({ name: "ok" })).toBe(false);
    expect(containsRawToken({ leak: "eyJhbGciOiJSUzI1NiJ9.x.y" })).toBe(true);
  });

  it("case 23/26: new kit components import nothing from the old multi-chat UI", () => {
    const dir = resolve(__dirname, "..");
    const authDir = resolve(__dirname, "../../auth");
    const files = [
      resolve(dir, "AuthStatusBadge.tsx"),
      resolve(dir, "OperatorIdentityCard.tsx"),
      resolve(dir, "StepUpRequiredBanner.tsx"),
      resolve(dir, "ApprovalDisabledReason.tsx"),
      resolve(authDir, "operatorIdentity.ts"),
      resolve(authDir, "useStepUp.ts"),
    ];
    for (const f of files) {
      const src = readFileSync(f, "utf8");
      expect(src).not.toMatch(/client_ui/);
      expect(src).not.toMatch(/multi-?chat/i);
      // only relative kit imports
      const imports = [...src.matchAll(/from\s+"([^"]+)"/g)].map((m) => m[1]);
      for (const imp of imports) {
        expect(imp.startsWith(".") || imp === "react").toBe(true);
      }
    }
  });
});
