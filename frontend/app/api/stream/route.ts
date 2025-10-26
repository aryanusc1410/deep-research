// frontend/app/api/stream/route.ts
export const runtime = "nodejs"; // ensure Node runtime

export async function POST(req: Request) {
  const body = await req.json();
  const resp = await fetch(process.env.BACKEND_URL + "/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });

  if (!resp.ok || !resp.body) {
    return new Response("Upstream error", { status: 502 });
  }

  const headers = new Headers(resp.headers);
  headers.set("Content-Type", "text/event-stream");
  headers.set("Cache-Control", "no-cache");
  headers.set("Connection", "keep-alive");
  headers.delete("Content-Length"); // let it stream

  return new Response(resp.body, { headers, status: 200 });
}
