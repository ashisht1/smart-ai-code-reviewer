import os
import json
import ast
import urllib.request

# Try loading the HTML template
try:
    with open("index.html", "r", encoding="utf-8") as f:
        INDEX_HTML = f.read()
except FileNotFoundError:
    INDEX_HTML = "<h1>index.html template not found!</h1>"

class StaticCodeAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.stats = {
            "functions": 0,
            "classes": 0,
            "decision_points": 0,
            "docstrings_missing": 0,
            "global_statements": 0
        }
        self.function_list = []

    def visit_FunctionDef(self, node):
        self.stats["functions"] += 1
        docstring = ast.get_docstring(node)
        if not docstring:
            self.stats["docstrings_missing"] += 1
        func_lines = node.end_lineno - node.lineno
        self.function_list.append((node.name, func_lines))
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.stats["classes"] += 1
        self.generic_visit(node)

    def visit_If(self, node):
        self.stats["decision_points"] += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.stats["decision_points"] += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.stats["decision_points"] += 1
        self.generic_visit(node)

    def visit_Global(self, node):
        self.stats["global_statements"] += len(node.names)
        self.generic_visit(node)

def run_static_analysis(code_content):
    """Parses Python code and extracts AST-based metrics."""
    tree = ast.parse(code_content)
    analyzer = StaticCodeAnalyzer()
    analyzer.visit(tree)
    total_lines = len(code_content.splitlines())
    return total_lines, analyzer.stats, analyzer.function_list

def query_llm_review(code_content, total_lines, stats, functions, guidelines):
    """Sends source code to Gemini API for a review using pure standard libraries (no SDK dependencies)."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    prompt = f"""
You are a Code Reviewer. 

Your Review Persona and Core Instructions:
{guidelines}

Please perform a professional code review of this Python code.

Here are the AST-based static metrics for context:
- Total Lines of Code: {total_lines}
- Number of Classes: {stats['classes']}
- Number of Functions: {stats['functions']}
- Missing Docstrings: {stats['docstrings_missing']}
- Decision Points (Complexity): {stats['decision_points']}
- Global State Statements: {stats['global_statements']}
- Functions detail (name, line count): {functions}

Here is the source code:
```python
{code_content}
```

Format your review in clean Markdown with these sections:
1. ### 🌟 Executive Summary: General rating/vibe of the code.
2. ### 🛠️ Readability & Styling: Naming conventions, style improvements, comment quality.
3. ### 📐 Design & Structure: Nesting complexity, modularity, usage of globals, architectural flaws.
4. ### 🐛 Maintainability & Potential Bugs: Error handling, edge cases, inefficiencies.
5. ### 🚀 Actionable Recommendations: List of concrete refactoring steps, with a brief code example showing the improved structure.
"""
    # Raw HTTP POST Request to Gemini REST API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    with urllib.request.urlopen(req) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        # Parse Gemini response candidate structure
        candidates = res_data.get("candidates", [])
        if candidates:
            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text", "")
    return None

def lambda_handler(event, context):
    """AWS Lambda proxy handler for both GET and POST requests."""
    # Routing based on HTTP Method
    method = event.get("httpMethod", "GET")
    if not method:
        # Check API Gateway HTTP API structure
        method = event.get("requestContext", {}).get("http", {}).get("method", "GET")

    if method == "GET":
        # Return index.html web page
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "text/html"},
            "body": INDEX_HTML
        }
        
    elif method == "POST":
        # Parse body payload
        try:
            body = json.loads(event.get("body", "{}"))
        except Exception:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Invalid JSON payload in request body"})
            }
            
        code = body.get("code", "").strip()
        guidelines = body.get("guidelines", "").strip()
        
        if not code:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "No python code provided in 'code' field"})
            }
            
        if not guidelines:
            guidelines = "Review code as a staff engineer about code and review on all important factors."
            
        try:
            # 1. AST Analysis
            total_lines, stats, functions = run_static_analysis(code)
            
            # 2. LLM Review
            report = None
            try:
                report = query_llm_review(code, total_lines, stats, functions, guidelines)
            except Exception as e:
                # Fallback return info about failure if key is not configured or HTTP error
                report = f"AI review was skipped: {str(e)}"
                
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "total_lines": total_lines,
                    "stats": stats,
                    "functions": functions,
                    "report": report
                })
            }
            
        except SyntaxError as se:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Python Syntax Error: {se.msg} (Line {se.lineno})"})
            }
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"Server Error during analysis: {str(e)}"})
            }
            
    return {
        "statusCode": 405,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": "Method Not Allowed"})
    }
