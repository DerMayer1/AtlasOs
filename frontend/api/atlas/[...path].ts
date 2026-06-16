const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-encoding",
  "content-length",
  "host",
  "keep-alive",
  "transfer-encoding",
  "upgrade"
]);

const RATE_LIMIT_WINDOW_MS = Number(process.env.ATLAS_PROXY_RATE_LIMIT_WINDOW_MS ?? 60_000);
const RATE_LIMIT_REQUESTS = Number(process.env.ATLAS_PROXY_RATE_LIMIT_REQUESTS ?? 120);
const MAX_BODY_BYTES = Number(process.env.ATLAS_PROXY_MAX_BODY_BYTES ?? 1_000_000);
const rateLimitBuckets = new Map<string, { count: number; resetAt: number }>();

function requiredEnv(name: string) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`${name} is not configured`);
  }
  return value;
}

function resolveTargetUrl(request: { query: Record<string, unknown>; url?: string }) {
  const baseUrl = requiredEnv("ATLAS_API_URL").replace(/\/$/, "");
  const pathQuery = request.query.path;
  const path = Array.isArray(pathQuery) ? pathQuery.join("/") : String(pathQuery ?? "");
  const sourceUrl = new URL(request.url ?? "/api/atlas", "https://atlas.local");
  return `${baseUrl}/${path}${sourceUrl.search}`;
}

function clientIp(request: any) {
  const forwardedFor = request.headers?.["x-forwarded-for"];
  if (typeof forwardedFor === "string" && forwardedFor) {
    return forwardedFor.split(",", 1)[0].trim();
  }
  return request.socket?.remoteAddress ?? "unknown";
}

function enforceRateLimit(request: any, response: any) {
  const now = Date.now();
  const key = clientIp(request);
  const bucket = rateLimitBuckets.get(key);
  if (!bucket || bucket.resetAt <= now) {
    rateLimitBuckets.set(key, { count: 1, resetAt: now + RATE_LIMIT_WINDOW_MS });
    return true;
  }
  bucket.count += 1;
  if (bucket.count > RATE_LIMIT_REQUESTS) {
    response.setHeader("Retry-After", Math.ceil((bucket.resetAt - now) / 1000).toString());
    response.status(429).json({ detail: "rate limit exceeded" });
    return false;
  }
  return true;
}

function readBody(request: any): Promise<Buffer | undefined> {
  if (["GET", "HEAD"].includes(request.method)) {
    return Promise.resolve(undefined);
  }
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks: Buffer[] = [];
    request.on("data", (chunk: Buffer | string) => {
      const buffer = Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk);
      size += buffer.length;
      if (size > MAX_BODY_BYTES) {
        reject(new Error("request body too large"));
        request.destroy();
        return;
      }
      chunks.push(buffer);
    });
    request.on("end", () => resolve(Buffer.concat(chunks)));
    request.on("error", reject);
  });
}

export default async function handler(request: any, response: any) {
  let targetUrl: string;
  let apiKey: string;

  try {
    if (!enforceRateLimit(request, response)) {
      return;
    }
    targetUrl = resolveTargetUrl(request);
    apiKey = requiredEnv("ATLAS_API_KEY");
  } catch (error) {
    response.status(500).json({
      detail: error instanceof Error ? error.message : "Atlas proxy is not configured"
    });
    return;
  }

  const headers = new Headers();
  for (const [name, value] of Object.entries(request.headers ?? {})) {
    const lowerName = name.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lowerName) || lowerName === "x-api-key") {
      continue;
    }
    if (Array.isArray(value)) {
      headers.set(name, value.join(","));
    } else if (typeof value === "string") {
      headers.set(name, value);
    }
  }
  headers.set("X-API-Key", apiKey);

  let body: Buffer | undefined;
  try {
    body = await readBody(request);
  } catch (error) {
    response.status(413).json({
      detail: error instanceof Error ? error.message : "request body too large"
    });
    return;
  }
  const upstream = await fetch(targetUrl, {
    method: request.method,
    headers,
    body
  });

  response.status(upstream.status);
  upstream.headers.forEach((value, name) => {
    if (!HOP_BY_HOP_HEADERS.has(name.toLowerCase())) {
      response.setHeader(name, value);
    }
  });
  response.send(Buffer.from(await upstream.arrayBuffer()));
}
