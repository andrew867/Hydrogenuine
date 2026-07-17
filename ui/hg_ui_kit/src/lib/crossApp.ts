export type CrossAppConfig = {
  clientBase?: string;
  operatorBase?: string;
  productBase?: string;
};

export type CrossAppContext = {
  tenantId?: string;
  runId?: string;
  entityId?: string;
  returnUrl?: string;
};

function trimSlash(value: string): string {
  return value.replace(/\/$/, "");
}

export function operatorHashUrl(path: string, config: CrossAppConfig = {}): string {
  const base = trimSlash(config.operatorBase ?? "/operator");
  const hashPath = path.startsWith("#") ? path : `#${path.startsWith("/") ? path : `/${path}`}`;
  return `${base}/${hashPath.replace(/^#/, "#")}`.replace("/#", "/#");
}

export function productHashUrl(path: string, config: CrossAppConfig = {}): string {
  const base = trimSlash(config.productBase ?? "/product");
  const hashPath = path.startsWith("#") ? path : `#${path.startsWith("/") ? path : `/${path}`}`;
  return `${base}/${hashPath.replace(/^#/, "#")}`.replace("/#", "/#");
}

export function clientUrl(path: string, config: CrossAppConfig = {}): string {
  const base = trimSlash(config.clientBase ?? "");
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}`;
}

export function withCrossAppReturn(url: string, ctx: CrossAppContext = {}): string {
  const params = new URLSearchParams();
  if (ctx.returnUrl) params.set("returnUrl", ctx.returnUrl);
  if (ctx.tenantId) params.set("tenant", ctx.tenantId);
  if (ctx.runId) params.set("run", ctx.runId);
  if (ctx.entityId) params.set("entity", ctx.entityId);
  const qs = params.toString();
  if (!qs) return url;
  return `${url}${url.includes("?") ? "&" : "?"}${qs}`;
}
