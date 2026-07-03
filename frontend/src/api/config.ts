const trimTrailingSlash = (value: string) => value.replace(/\/+$/, "");

const explicitApiBase = (import.meta.env.VITE_API_BASE_URL || "").trim();
const originBasedApiBase = `${window.location.origin}/api`;

export const apiBaseUrl = trimTrailingSlash(explicitApiBase || originBasedApiBase);
export const wsBaseUrl = `${apiBaseUrl.replace(/^http/i, "ws")}/ws`;
