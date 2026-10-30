"""Count the tokens an agent loads from each MCP server's tools/list (names, descriptions, input schemas).
Plain JSON-RPC over Streamable HTTP: initialize, initialized notification, tools/list."""
import json, os
import requests, tiktoken
enc = tiktoken.get_encoding("o200k_base")
def rpc(s, url, headers, body):
    r = s.post(url, json=body, headers={**headers, "Accept": "application/json, text/event-stream", "Content-Type": "application/json"}, timeout=60)
    if "Mcp-Session-Id" in r.headers: headers["Mcp-Session-Id"] = r.headers["Mcp-Session-Id"]
    text = r.content.decode("utf-8")  # SSE responses carry no charset, so requests would guess latin-1
    if not text.strip(): return None
    if r.headers.get("content-type", "").startswith("text/event-stream"):
        data = [l[5:].strip() for l in text.splitlines() if l.startswith("data:")]
        return json.loads(data[-1])
    return json.loads(text)
def count(name, url, headers):
    s = requests.Session()
    rpc(s, url, headers, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "token-count", "version": "1"}}})
    rpc(s, url, headers, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    tools, cursor = [], None
    while True:
        res = rpc(s, url, headers, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {"cursor": cursor} if cursor else {}})["result"]
        tools += res["tools"]; cursor = res.get("nextCursor")
        if not cursor: break
    blob = [{"name": t["name"], "description": t.get("description"), "inputSchema": t.get("inputSchema")} for t in tools]
    json.dump(blob, open(f"results/mcp/{name}-tools.json", "w"), indent=1)
    print(name, "tools", len(tools), "tokens", len(enc.encode(json.dumps(blob))), "| largest:", sorted(((len(enc.encode(json.dumps(b))), b["name"]) for b in blob), reverse=True)[:3])
count("scrapingbee", "https://mcp.scrapingbee.com/mcp", {"Authorization": f"Bearer {os.environ['SB_KEY']}"})
count("firecrawl", "https://mcp.firecrawl.dev/v2/mcp", {"Authorization": f"Bearer {os.environ['FC_KEY']}"})
