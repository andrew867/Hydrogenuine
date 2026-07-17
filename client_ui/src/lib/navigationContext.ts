export function getCurrentPathWithSearch(): string {
  if (typeof window === "undefined") return "/";
  const path = window.location.pathname || "/";
  const search = window.location.search || "";
  return `${path}${search}`;
}

export function appendReturnUrl(href: string, returnUrl = getCurrentPathWithSearch()): string {
  if (typeof window === "undefined") return href;
  const url = new URL(href, window.location.origin);
  if (returnUrl) url.searchParams.set("returnUrl", returnUrl);
  return `${url.pathname}${url.search}${url.hash}`;
}

export function readReturnUrl(searchParams: URLSearchParams, fallback = "/"): string {
  return searchParams.get("returnUrl") || fallback;
}
