from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Tuple
import re
import requests

def _norm_path(p: str) -> str:
    return p

@dataclass
class OpenAPISpec:
    base_url: str
    spec: Dict[str, Any]

    @classmethod
    def from_base_url(cls, base_url: str, verify: bool=True, timeout: int=20) -> "OpenAPISpec":
        url = base_url.rstrip("/") + "/openapi.json"
        r = requests.get(url, timeout=timeout, verify=verify)
        r.raise_for_status()
        return cls(base_url=base_url.rstrip("/"), spec=r.json())

    def iter_operations(self) -> Iterator[Tuple[Tuple[str,str], Dict[str, Any]]]:
        paths: Dict[str, Any] = self.spec.get("paths", {})
        for path, item in paths.items():
            if not isinstance(item, dict):
                continue
            for method, op in item.items():
                if method.lower() not in ("get","post","put","patch","delete","options","head"):
                    continue
                yield (method.upper(), _norm_path(path)), (op or {})

    def get_operation(self, method: str, path: str) -> Optional[Dict[str, Any]]:
        item = self.spec.get("paths", {}).get(_norm_path(path))
        if not item:
            return None
        return item.get(method.lower()) or item.get(method.upper())

    def preferred_content_type(self, op: Dict[str, Any]) -> Optional[str]:
        rb = op.get("requestBody") or {}
        content = rb.get("content") or {}
        if "application/json" in content:
            return "application/json"
        for ct in content.keys():
            if "json" in ct:
                return ct
        return next(iter(content.keys()), None)

    def suggest_auth_headers(self, op: Dict[str, Any]) -> Dict[str, str]:
        headers: Dict[str,str] = {}
        comps = (self.spec.get("components") or {})
        sec_schemes = (comps.get("securitySchemes") or {})
        security_reqs = op.get("security")
        if security_reqs is None:
            security_reqs = self.spec.get("security")
        if not security_reqs:
            return headers
        req0 = security_reqs[0] if isinstance(security_reqs, list) and security_reqs else {}
        if not isinstance(req0, dict):
            return headers
        for scheme_name in req0.keys():
            scheme = sec_schemes.get(scheme_name, {})
            stype = (scheme.get("type") or "").lower()
            if stype == "http" and (scheme.get("scheme") or "").lower() == "bearer":
                headers["Authorization"] = "Bearer <token>"
            elif stype == "apikey":
                where = (scheme.get("in") or "").lower()
                name = scheme.get("name") or "X-API-KEY"
                if where == "header":
                    headers[name] = "<api_key>"
        return headers

    def suggest_parameters(self, op: Dict[str, Any], path: str) -> Dict[str, str]:
        out: Dict[str,str] = {}
        params = op.get("parameters") or []
        for p in params:
            if "$ref" in p:
                p = self._resolve_ref(p["$ref"]) or {}
            name = p.get("name")
            if not name:
                continue
            schema = p.get("schema") or {}
            if "$ref" in schema:
                schema = self._resolve_ref(schema["$ref"]) or {}
            out[name] = self._example_scalar(schema, name=name)
        for token in re.findall(r"\{([^}]+)\}", path):
            out.setdefault(token, "")
        return out

    def build_request_body_template(self, op: Dict[str, Any]) -> Optional[Any]:
        rb = op.get("requestBody") or {}
        content = rb.get("content") or {}
        if not content:
            return None
        ct = self.preferred_content_type(op)
        if not ct or ct not in content:
            ct = next(iter(content.keys()), None)
            if not ct:
                return None
        media = content.get(ct) or {}
        if "example" in media:
            return media["example"]
        if "examples" in media and isinstance(media["examples"], dict) and media["examples"]:
            ex0 = next(iter(media["examples"].values()))
            if isinstance(ex0, dict) and "value" in ex0:
                return ex0["value"]
        schema = media.get("schema") or {}
        return self._build_from_schema(schema, depth=0)

    def _resolve_ref(self, ref: str) -> Optional[Dict[str, Any]]:
        if not ref.startswith("#/"):
            return None
        parts = ref[2:].split("/")
        node: Any = self.spec
        for p in parts:
            if not isinstance(node, dict):
                return None
            node = node.get(p)
        return node if isinstance(node, dict) else None

    def _example_scalar(self, schema: Dict[str, Any], name: str="value") -> str:
        if "example" in schema:
            return str(schema["example"])
        if "default" in schema:
            return str(schema["default"])
        if "enum" in schema and schema["enum"]:
            return str(schema["enum"][0])
        t = (schema.get("type") or "").lower()
        fmt = (schema.get("format") or "").lower()
        if t == "integer":
            return "0"
        if t == "number":
            return "0.0"
        if t == "boolean":
            return "false"
        if t == "string":
            if "email" in name.lower() or fmt == "email":
                return "user@example.com"
            if "password" in name.lower():
                return "Password123!"
            if fmt == "uuid":
                return "00000000-0000-0000-0000-000000000000"
            if fmt == "date":
                return "2026-01-01"
            if fmt in ("date-time","datetime"):
                return "2026-01-01T00:00:00Z"
            return f"<{name}>"
        return f"<{name}>"

    def _build_from_schema(self, schema: Dict[str, Any], depth: int):
        if depth > 6:
            return None
        if "$ref" in schema:
            resolved = self._resolve_ref(schema["$ref"]) or {}
            return self._build_from_schema(resolved, depth=depth+1)
        if "example" in schema:
            return schema["example"]
        if "default" in schema:
            return schema["default"]
        if "enum" in schema and schema["enum"]:
            return schema["enum"][0]
        if "allOf" in schema and isinstance(schema["allOf"], list):
            obj = {}
            for sub in schema["allOf"]:
                val = self._build_from_schema(sub, depth=depth+1)
                if isinstance(val, dict):
                    obj.update(val)
            return obj
        for key in ("oneOf","anyOf"):
            if key in schema and isinstance(schema[key], list) and schema[key]:
                return self._build_from_schema(schema[key][0], depth=depth+1)

        t = (schema.get("type") or "").lower()
        if t == "object" or ("properties" in schema):
            props = schema.get("properties") or {}
            required = set(schema.get("required") or [])
            keys = list(props.keys())
            keys.sort(key=lambda k: (0 if k in required else 1, k))
            return {k: self._build_from_schema(props[k] or {}, depth=depth+1) for k in keys}
        if t == "array":
            items = schema.get("items") or {}
            return [self._build_from_schema(items, depth=depth+1)]
        if t == "string":
            return self._example_scalar(schema, name="value")
        if t == "integer":
            return 0
        if t == "number":
            return 0.0
        if t == "boolean":
            return False
        return None
