from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import os
import re
import zipfile

_ROUTE_RE = re.compile(r'@router\.(get|post|put|delete|patch|options|head)\s*\(\s*[\'"]([^\'"]+)[\'"]([^)]*)\)', re.I)
_PREFIX_RE = re.compile(r'router\s*=\s*APIRouter\s*\((.*?)\)\s*', re.S)
_PREFIX_KV_RE = re.compile(r'prefix\s*=\s*[\'"]([^\'"]+)[\'"]')
_DEF_RE = re.compile(r'\n\s*(async\s+def|def)\s+([a-zA-Z0-9_]+)\s*\(')

@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    file: Optional[str] = None
    func_name: Optional[str] = None
    summary: Optional[str] = None

def _get_prefix(code: str) -> str:
    m = _PREFIX_RE.search(code)
    if not m:
        return ""
    args = m.group(1)
    pm = _PREFIX_KV_RE.search(args)
    return pm.group(1) if pm else ""

def _parse_endpoints_from_code(code: str, file: str) -> List[Endpoint]:
    prefix = _get_prefix(code)
    eps: List[Endpoint] = []
    for m in _ROUTE_RE.finditer(code):
        method = m.group(1).upper()
        raw_path = m.group(2)
        start = m.end()
        dm = _DEF_RE.search(code[start:])
        func = dm.group(2) if dm else None
        # eps.append(Endpoint(method=method, path=f"{prefix}{raw_path}", file=file, func_name=func))
        # Normalización profesional de path
        full_path = (prefix.rstrip("/") + "/" + raw_path.lstrip("/")).rstrip("/")
        if full_path == "":
            full_path = "/"

        eps.append(
            Endpoint(
                method=method,
                path=full_path,
                file=file,
                func_name=func
            )
        )
    return eps

def load_endpoints(path: str) -> List[Endpoint]:
    if os.path.isfile(path) and path.lower().endswith(".zip"):
        return _load_from_zip(path)
    if os.path.isdir(path):
        return _load_from_dir(path)
    raise FileNotFoundError(f"No existe o no es válido: {path}")

def _load_from_zip(zip_path: str) -> List[Endpoint]:
    eps: List[Endpoint] = []
    with zipfile.ZipFile(zip_path) as zf:
        names = [n for n in zf.namelist() if n.endswith(".py") and "__pycache__" not in n]
        preferred = [n for n in names if "routers/" in n.replace("\\","/")]
        scan = preferred if preferred else names
        for name in scan:
            code = zf.read(name).decode("utf-8", errors="replace")
            eps.extend(_parse_endpoints_from_code(code, file=name))
    return sorted(eps, key=lambda e: (e.path, e.method))

def _load_from_dir(dir_path: str) -> List[Endpoint]:
    eps: List[Endpoint] = []
    candidate = os.path.join(dir_path, "routers")
    root = candidate if os.path.isdir(candidate) else dir_path
    for base, _dirs, files in os.walk(root):
        for fn in files:
            if not fn.endswith(".py"):
                continue
            if "__pycache__" in base:
                continue
            full = os.path.join(base, fn)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    code = f.read()
            except UnicodeDecodeError:
                with open(full, "r", encoding="latin-1") as f:
                    code = f.read()
            rel = os.path.relpath(full, dir_path)
            eps.extend(_parse_endpoints_from_code(code, file=rel))
    return sorted(eps, key=lambda e: (e.path, e.method))
