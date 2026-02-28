# Why: Regenerate machine-readable LLM context from codebase
# Deps: pathlib, re
# How: Parse api/main.py and frontend lib/api.ts; emit internal/llm-context.yaml

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_MAIN = ROOT / "api" / "main.py"
FRONTEND_API = ROOT / "frontend" / "src" / "lib" / "api.ts"
OUT = ROOT / "internal" / "llm-context.yaml"


def extract_backend_routes() -> list[dict]:
    text = API_MAIN.read_text()
    routes = []
    # Match @app.get("...") or @app.post("...") and next def name
    for m in re.finditer(
        r'@app\.(get|post)\s*\(\s*["\']([^"\']+)["\']\s*\)\s*\n\s*def\s+(\w+)\s*\(',
        text,
    ):
        method, path, handler = m.group(1).upper(), m.group(2), m.group(3)
        routes.append({"path": path, "method": method, "handler": handler})
    return routes


def extract_frontend_api() -> list[dict]:
    text = FRONTEND_API.read_text()
    functions = []
    export_positions = list(re.finditer(r"export\s+const\s+(\w+)\s*=", text))
    for i, m in enumerate(export_positions):
        name = m.group(1)
        end = export_positions[i + 1].start() if i + 1 < len(export_positions) else len(text)
        chunk = text[m.end() : end]
        # First fetchAPI call in this function body; path is /api/... in quotes or backticks
        path_m = re.search(r"fetchAPI[^/]*[\"'`](/api/[^\"'`?]+)", chunk)
        if not path_m:
            path_m = re.search(r"`(/api/[^`${]+)", chunk)
        path = path_m.group(1).rstrip("/") if path_m else "/api/unknown"
        if "${" in path or "?" in path:
            path = path.split("${")[0].split("?")[0].rstrip("/") or "/api/unknown"
        method = "POST" if ("method:" in chunk and "POST" in chunk) or name in (
            "generateBrief", "generateEmail", "generateBattlecard", "smartSearch", "seedDatabase", "rescoreAll"
        ) else "GET"
        functions.append({"name": name, "path": path, "method": method})
    return functions


def yaml_routes(routes: list[dict]) -> str:
    lines = []
    for r in routes:
        lines.append("  - path: " + repr(r["path"]))
        lines.append("    method: " + r["method"])
        lines.append("    handler: " + r["handler"])
    return "\n".join(lines) if lines else " []"


def yaml_functions(functions: list[dict]) -> str:
    lines = []
    for f in functions:
        lines.append("  - name: " + f["name"])
        lines.append("    path: " + repr(f["path"]))
        lines.append("    method: " + f["method"])
    return "\n".join(lines) + "\n" if lines else " []\n"


def main() -> None:
    routes = extract_backend_routes()
    functions = extract_frontend_api()

    # Read existing file and replace generated sections
    content = OUT.read_text()
    # Replace backend routes block: between "routes:" and "\n\nfrontend_api:"
    routes_marker = "  routes:"
    fe_api_marker = "\n\nfrontend_api:"
    rx = content.find(routes_marker)
    fe_start = content.find(fe_api_marker)
    if rx != -1 and fe_start != -1 and fe_start > rx:
        block_start = content.find("\n", rx) + 1
        content = content[:block_start] + yaml_routes(routes).rstrip() + "\n" + content[fe_start:]
    # Replace frontend functions block: between "functions:" and "\ntypes:"
    func_marker = "  functions:"
    types_marker = "\ntypes:"
    start = content.find(func_marker)
    end = content.find(types_marker)
    if start != -1 and end != -1 and end > start:
        block_start = content.find("\n", start) + 1  # first line after "  functions:"
        new_functions = yaml_functions(functions).rstrip()
        content = content[:block_start] + new_functions + "\n" + content[end:]
    OUT.write_text(content)
    print(f"Updated {OUT} with {len(routes)} backend routes and {len(functions)} frontend API functions.")


if __name__ == "__main__":
    main()
