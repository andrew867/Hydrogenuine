"use client";

import { operatorHashUrl as kitOperatorHashUrl } from "hg_ui_kit";
import { env } from "@/lib/env";

export function operatorHashUrl(path: string) {
  const base = env.operatorProofsUrl.includes("#")
    ? env.operatorProofsUrl.split("#")[0]
    : env.operatorProofsUrl;
  return kitOperatorHashUrl(path, { operatorBase: base });
}
