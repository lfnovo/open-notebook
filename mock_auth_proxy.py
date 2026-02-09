"""
Mock auth proxy for browser testing of multi-tenant mode.

Forwards all requests to the upstream Open Notebook instance with
an X-Forwarded-User header injected, simulating what OAuth2 Proxy does.

Usage:
    python mock_auth_proxy.py --user alice --port 9000
    python mock_auth_proxy.py --user bob --port 9001 --upstream http://localhost:8502

Then open http://localhost:9000 in browser — all requests go to Open Notebook as "alice".
"""

import argparse
import http.client
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse


class ProxyHandler(BaseHTTPRequestHandler):
    def _proxy(self):
        upstream = urlparse(self.server.upstream)
        if upstream.scheme == "https":
            conn = http.client.HTTPSConnection(upstream.hostname, upstream.port)
        else:
            conn = http.client.HTTPConnection(upstream.hostname, upstream.port)

        # Read request body if present
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Build headers, inject X-Forwarded-User
        headers = {}
        for key, val in self.headers.items():
            if key.lower() != "host":
                headers[key] = val
        headers["X-Forwarded-User"] = self.server.user
        headers["Host"] = f"{upstream.hostname}:{upstream.port}"
        # Force non-chunked response so read() doesn't hang
        headers["Accept-Encoding"] = "identity"

        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()

            self.send_response(resp.status)
            # Collect response body first, then set Content-Length
            resp_body = resp.read()
            hop_by_hop = {"transfer-encoding", "connection", "keep-alive"}
            for key, val in resp.getheaders():
                if key.lower() not in hop_by_hop:
                    if key.lower() == "content-length":
                        continue  # We'll set our own
                    self.send_header(key, val)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            self.wfile.write(resp_body)
        except Exception as e:
            self.send_error(502, f"Proxy error: {e}")
        finally:
            conn.close()

    # Handle all HTTP methods
    do_GET = _proxy
    do_POST = _proxy
    do_PUT = _proxy
    do_DELETE = _proxy
    do_PATCH = _proxy
    do_OPTIONS = _proxy
    do_HEAD = _proxy

    def log_message(self, fmt, *args):
        # Prefix log with user for clarity
        print(f"[{self.server.user}] {fmt % args}")


def main():
    parser = argparse.ArgumentParser(description="Mock auth proxy for Open Notebook")
    parser.add_argument("--user", required=True, help="User identity to inject")
    parser.add_argument("--port", type=int, default=9000, help="Proxy listen port")
    parser.add_argument(
        "--upstream",
        default="http://localhost:8502",
        help="Upstream Open Notebook URL",
    )
    args = parser.parse_args()

    server = HTTPServer(("0.0.0.0", args.port), ProxyHandler)
    server.user = args.user
    server.upstream = args.upstream

    print(f"Mock auth proxy listening on http://localhost:{args.port}")
    print(f"  Upstream: {args.upstream}")
    print(f"  User:     {args.user}")
    print(f"  Header:   X-Forwarded-User: {args.user}")
    print()
    print(f"Open http://localhost:{args.port} in browser to use as '{args.user}'")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
