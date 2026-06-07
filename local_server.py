#!/usr/bin/env python3
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from lambda_function import run_static_analysis, query_llm_review

class LocalReviewerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silence default log spam to keep terminal clean
        return

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            try:
                with open("index.html", "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"Error loading index.html: {e}".encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        if self.path == "/review":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                body = json.loads(post_data.decode('utf-8'))
            except Exception:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "Invalid JSON body"}).encode())
                return
                
            code = body.get("code", "").strip()
            guidelines = body.get("guidelines", "").strip()
            
            if not code:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "No python code provided"}).encode())
                return
                
            if not guidelines:
                guidelines = "Review code as a staff engineer about code and review on all important factors."
                
            try:
                # 1. Run AST Static Parsing
                total_lines, stats, functions = run_static_analysis(code)
                
                # 2. Get LLM review
                report = None
                try:
                    report = query_llm_review(code, total_lines, stats, functions, guidelines)
                except Exception as e:
                    print(f"Error calling LLM: {e}")
                    
                response_data = {
                    "total_lines": total_lines,
                    "stats": stats,
                    "functions": functions,
                    "report": report
                }
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
                
            except SyntaxError as se:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Python Syntax Error: {se.msg} (Line {se.lineno})"}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Internal server error: {e}"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

def run(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, LocalReviewerHandler)
    print(f"\n🚀 Smart Code Reviewer Local Web App running at:")
    print(f"👉 http://localhost:{port}\n")
    print("Press Ctrl+C to stop the server.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web server...")
        httpd.server_close()

if __name__ == "__main__":
    run()
