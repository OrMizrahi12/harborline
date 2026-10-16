"""codemap: where a Python name really comes from, as an MCP server.

Grep finds text. These tools read the code's structure: what a package
exports, and which module and function an exported name really is,
through every re-export and rename.
"""

import ast
from pathlib import Path

from mcp.server import MCPServer

ROOT = Path(__file__).resolve().parent.parent
app = MCPServer("codemap")


def source(module):
    """Parse a module like 'legacy.warehouse' from its file in the repo."""
    path = ROOT / Path(*module.split("."))
    path = path / "__init__.py" if path.is_dir() else path.with_suffix(".py")
    return path, ast.parse(path.read_text())


def names(tree):
    """{name: node} for every top-level def, class, assignment and import."""
    found = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            found[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    found[target.id] = node
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                found[alias.asname or alias.name] = node
    return found


@app.tool(description=(
    "List the public names a Python package or module exports, such as "
    "'legacy.warehouse', with the line of each and, for re-exports, the "
    "module it comes from. Use this instead of Grep or reading files to "
    "see a package's interface."))
def list_public_names(module: str) -> list[dict]:
    path, tree = source(module)
    found = names(tree)
    public = [n for n in found if not n.startswith("_")]
    rows = []
    for name in public:
        node = found[name]
        row = {"name": name, "line": node.lineno}
        if isinstance(node, ast.ImportFrom):
            row["from"] = node.module
        rows.append(row)
    return rows


@app.tool(description=(
    "Find where a name a module exports is really defined: follows "
    "re-exports and renames (import x as y) to the file, line and original "
    "name. Use this, not Grep, for 'where does this name come from?': "
    "a renamed export has no definition that text search can find."))
def trace_export(module: str, name: str) -> dict:
    chain = [f"{module}:{name}"]
    for _ in range(10):
        path, tree = source(module)
        node = names(tree).get(name)
        if node is None:
            raise ValueError(f"{module} has no top-level name {name!r}")
        if not isinstance(node, ast.ImportFrom):
            return {"defined_in": str(path.relative_to(ROOT)),
                    "line": node.lineno, "name": name, "chain": chain}
        alias = next(a for a in node.names if (a.asname or a.name) == name)
        module, name = node.module, alias.name
        chain.append(f"{module}:{name}")
    raise ValueError("more than 10 re-exports: " + " -> ".join(chain))


if __name__ == "__main__":
    app.run()  # stdio
