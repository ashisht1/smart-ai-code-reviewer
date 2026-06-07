#!/usr/bin/env python3
import os
import sys
import ast
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

# Initialize rich console
console = Console()

class StaticCodeAnalyzer(ast.NodeVisitor):
    """AST visitor to gather basic static metrics of a Python file."""
    def __init__(self):
        self.stats = {
            "functions": 0,
            "classes": 0,
            "decision_points": 0,  # Proxy for complexity
            "docstrings_missing": 0,
            "global_statements": 0
        }
        self.function_list = []

    def visit_FunctionDef(self, node):
        self.stats["functions"] += 1
        # Check if the function has a docstring
        docstring = ast.get_docstring(node)
        if not docstring:
            self.stats["docstrings_missing"] += 1
        
        # Calculate size of function
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

def run_static_analysis(file_path):
    """Parses a Python file and extracts AST-based metrics."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
            tree = ast.parse(code)
        
        analyzer = StaticCodeAnalyzer()
        analyzer.visit(tree)
        
        total_lines = len(code.splitlines())
        return total_lines, analyzer.stats, analyzer.function_list, code
    except Exception as e:
        console.print(f"[bold red]Error parsing file for static analysis: {e}[/bold red]")
        sys.exit(1)

def query_llm_review(file_name, code_content, total_lines, stats, functions, guidelines):
    """Sends the source code, static metrics, and guidelines to Gemini API for a deep semantic review."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("\n[yellow]⚠️ GEMINI_API_KEY environment variable not found.[/yellow]")
        console.print("[yellow]Skipping AI review. Set your API key using:[/yellow]")
        console.print("[bold cyan]export GEMINI_API_KEY=\"your_key_here\"[/bold cyan]\n")
        return None

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        # Use gemini-1.5-flash as default, or fallback to any available model
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        prompt = f"""
You are a Code Reviewer. 

Your Review Persona and Core Instructions:
{guidelines}

Please perform a professional code review of the following Python file: `{file_name}`.

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
        with console.status("[bold green]Querying Gemini AI for review..."):
            response = model.generate_content(prompt)
        return response.text
    except ImportError:
        console.print("[red]google-generativeai package is not installed. Run 'pip install -r requirements.txt'[/red]")
        return None
    except Exception as e:
        console.print(f"[red]Error contacting Gemini API: {e}[/red]")
        return None

def main():
    if len(sys.argv) < 2:
        console.print("[bold red]Usage:[/bold red] python3 smart_reviewer.py <path_to_python_file> [path_to_guidelines]")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        console.print(f"[bold red]File not found:[/bold red] {file_path}")
        sys.exit(1)

    # Determine coding guidelines to follow
    guidelines_file = "guidelines.txt"
    if len(sys.argv) >= 3:
        guidelines_file = sys.argv[2]
        
    default_guidelines = "Review code as a staff engineer about code and review on all important factors."
    
    if os.path.exists(guidelines_file):
        try:
            with open(guidelines_file, "r", encoding="utf-8") as f:
                guidelines = f.read().strip()
            if not guidelines:
                guidelines = default_guidelines
                console.print(f"[cyan]ℹ️ guidelines.txt is empty. Using default staff engineer guidelines.[/cyan]")
            else:
                console.print(f"[green]✓ Loaded custom coding guidelines from: {guidelines_file}[/green]")
        except Exception as e:
            guidelines = default_guidelines
            console.print(f"[yellow]⚠️ Error reading guidelines file: {e}. Using default staff engineer guidelines.[/yellow]")
    else:
        guidelines = default_guidelines
        console.print(f"[cyan]ℹ️ No guidelines.txt found. Using default staff engineer guidelines.[/cyan]")

    console.print(Panel(f"[bold green]Smart Code Reviewer[/bold green]\nAnalyzing: {os.path.basename(file_path)}", expand=False))
    
    # Run AST Static Analysis
    total_lines, stats, functions, code_content = run_static_analysis(file_path)
    
    # Print AST Metrics Table
    table = Table(title="AST-Based Static Analysis Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta", justify="right")
    
    table.add_row("Total Lines of Code", str(total_lines))
    table.add_row("Classes Defined", str(stats["classes"]))
    table.add_row("Functions Defined", str(stats["functions"]))
    table.add_row("Decision Points (Complexity)", str(stats["decision_points"]))
    table.add_row("Global Statement Declarations", str(stats["global_statements"]))
    table.add_row("Functions Missing Docstrings", str(stats["docstrings_missing"]))
    
    console.print(table)
    
    # Detailed functions table
    if functions:
        func_table = Table(title="Function Sizes")
        func_table.add_column("Function Name", style="yellow")
        func_table.add_column("Lines", style="green", justify="right")
        for fn_name, fn_lines in functions:
            func_table.add_row(fn_name, str(fn_lines))
        console.print(func_table)

    # Run AI Review
    ai_report = query_llm_review(os.path.basename(file_path), code_content, total_lines, stats, functions, guidelines)
    
    if ai_report:
        console.print(Panel("[bold green]Gemini AI Code Review Report[/bold green]"))
        console.print(Markdown(ai_report))
        
        # Save to file
        report_file = "review_report.md"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(ai_report)
            console.print(f"\n[bold green]✓ Report successfully saved to [underline]{report_file}[/underline][/bold green]")
        except Exception as e:
            console.print(f"[red]Error saving report to file: {e}[/red]")

if __name__ == "__main__":
    main()
