import { useMemo } from "react";
import type { OperatorAuthState, OperatorIdentityView } from "./operatorIdentity";

// Derives step-up UI state from a verified operator identity. It never fabricates
// "satisfied": step_up_satisfied is whatever the backend receipt reports (which is
// derived from real token amr/acr evidence, never a bare boolean).
export type StepUpState = {
  required: boolean;
  satisfied: boolean;
  needsReauth: boolean;
};

export function computeStepUp(identity: OperatorIdentityView | null): StepUpState {
  if (!identity) return { required: false, satisfied: false, needsReauth: false };
  const required = identity.step_up_required;
  const satisfied = identity.step_up_satisfied;
  return { required, satisfied, needsReauth: required && !satisfied };
}

export function useStepUp(state: OperatorAuthState): StepUpState {
  return useMemo(() => {
    if (state.status === "authenticated" || state.status === "step_up_required") {
      return computeStepUp(state.identity);
    }
    return { required: false, satisfied: false, needsReauth: false };
  }, [state]);
}
