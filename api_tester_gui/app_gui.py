#!/usr/bin/env python3
"""
API Tester GUI PRO (Tkinter)

Nivel profesional:
- Lista endpoints desde ZIP/carpeta (routers FastAPI) *y* opcionalmente desde OpenAPI (/openapi.json)
- Autoprecarga dinámica:
  - Body JSON desde schema OpenAPI (requestBody) con ejemplos realistas
  - Query/path params desde OpenAPI parameters
  - Headers requeridos sugeridos según securitySchemes (Bearer, ApiKey)
- Cachea OpenAPI localmente en memoria.

Requisitos:
    pip install requests
"""
from __future__ import annotations

import json
import time
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Dict, List, Optional, Tuple

import requests

from endpoints_loader import load_endpoints, Endpoint
from openapi_support import OpenAPISpec


class KeyValueTable(ttk.Frame):
    """Tabla simple key/value editable, con botones para agregar/quitar filas."""
    def __init__(self, master: tk.Misc, title: str, columns: Tuple[str, str]=("Key","Value")) -> None:
        super().__init__(master)
        self.title = title
        self.columns = columns

        lbl = ttk.Label(self, text=title, font=("Segoe UI", 10, "bold"))
        lbl.grid(row=0, column=0, sticky="w", padx=2, pady=(0,4), columnspan=3)

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=6)
        for c in self.columns:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=180, anchor="w")
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(0,6))

        sb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.grid(row=1, column=1, sticky="ns")

        btns = ttk.Frame(self)
        btns.grid(row=1, column=2, sticky="ns")
        ttk.Button(btns, text="+", width=3, command=self.add_row).grid(row=0, column=0, pady=(0,4))
        ttk.Button(btns, text="-", width=3, command=self.remove_selected).grid(row=1, column=0)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.tree.bind("<Double-1>", self._on_double_click)

    def add_row(self, key: str="", value: str="") -> None:
        self.tree.insert("", "end", values=(key, value))

    def remove_selected(self) -> None:
        for item in self.tree.selection():
            self.tree.delete(item)

    def set_items(self, d: Dict[str,str]) -> None:
        for i in self.tree.get_children():
            self.tree.delete(i)
        for k,v in d.items():
            self.add_row(k, v)

    def get_items(self) -> Dict[str,str]:
        out: Dict[str,str] = {}
        for item in self.tree.get_children():
            k,v = self.tree.item(item, "values")
            k = (k or "").strip()
            if not k:
                continue
            out[k] = v
        return out

    def _on_double_click(self, event) -> None:
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item or not col:
            return
        col_index = int(col.replace("#","")) - 1
        x,y,w,h = self.tree.bbox(item, col)
        old = self.tree.item(item, "values")[col_index]

        entry = ttk.Entry(self.tree)
        entry.place(x=x, y=y, width=w, height=h)
        entry.insert(0, old)
        entry.focus_set()

        def save(_evt=None):
            vals = list(self.tree.item(item, "values"))
            vals[col_index] = entry.get()
            self.tree.item(item, values=tuple(vals))
            entry.destroy()

        entry.bind("<Return>", save)
        entry.bind("<FocusOut>", save)


class ApiTesterApp(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master)
        self.master.title("API Tester PRO (GUI)")
        self.master.geometry("1280x800")
        self.master.minsize(1150, 720)

        self.endpoints: List[Endpoint] = []
        self.filtered_endpoints: List[Endpoint] = []
        self.openapi: Optional[OpenAPISpec] = None

        self._build_ui()

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)

        ttk.Label(top, text="Fuente endpoints (ZIP/carpeta):").pack(side="left")
        self.source_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.source_var, width=55).pack(side="left", padx=(8,6))
        ttk.Button(top, text="Buscar…", command=self._browse_source).pack(side="left")
        ttk.Button(top, text="Cargar desde ZIP", command=self._load_endpoints_from_zip).pack(side="left", padx=(6,10))

        ttk.Label(top, text="Base URL:").pack(side="left")
        self.base_url_var = tk.StringVar(value="http://localhost:8000")
        ttk.Entry(top, textvariable=self.base_url_var, width=38).pack(side="left", padx=(6,6))

        self.verify_tls_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, text="Verificar TLS", variable=self.verify_tls_var).pack(side="left", padx=(0,6))

        ttk.Button(top, text="Sincronizar OpenAPI", command=self._sync_openapi).pack(side="left")

        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=10, pady=(0,10))

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=1)
        main.add(right, weight=3)

        lf = ttk.LabelFrame(left, text="Endpoints")
        lf.pack(fill="both", expand=True)

        filter_row = ttk.Frame(lf)
        filter_row.pack(fill="x", padx=8, pady=6)

        ttk.Label(filter_row, text="Filtro:").pack(side="left")
        self.filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_row, textvariable=self.filter_var)
        filter_entry.pack(side="left", fill="x", expand=True, padx=(6,0))
        filter_entry.bind("<KeyRelease>", lambda e: self._apply_filter())

        self.ep_tree = ttk.Treeview(lf, columns=("method","path","summary","file"), show="headings")
        self.ep_tree.heading("method", text="M")
        self.ep_tree.heading("path", text="Path")
        self.ep_tree.heading("summary", text="Summary")
        self.ep_tree.heading("file", text="Archivo")
        self.ep_tree.column("method", width=40, anchor="center")
        self.ep_tree.column("path", width=310, anchor="w")
        self.ep_tree.column("summary", width=220, anchor="w")
        self.ep_tree.column("file", width=130, anchor="w")

        ep_sb = ttk.Scrollbar(lf, orient="vertical", command=self.ep_tree.yview)
        self.ep_tree.configure(yscroll=ep_sb.set)

        self.ep_tree.pack(side="left", fill="both", expand=True, padx=(8,0), pady=(0,8))
        ep_sb.pack(side="left", fill="y", pady=(0,8))
        self.ep_tree.bind("<<TreeviewSelect>>", lambda e: self._on_select_endpoint())

        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        req_frame = ttk.LabelFrame(right, text="Request")
        req_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0,8))
        req_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(req_frame, text="Endpoint seleccionado:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        self.endpoint_var = tk.StringVar(value="(seleccioná un endpoint)")
        ttk.Entry(req_frame, textvariable=self.endpoint_var, state="readonly").grid(row=0, column=1, sticky="ew", padx=8, pady=6)

        tabs = ttk.Notebook(req_frame)
        tabs.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=(0,8))

        self.headers_table = KeyValueTable(tabs, "Headers")
        tabs.add(self.headers_table, text="Headers")

        self.params_table = KeyValueTable(tabs, "Query params / Path params")
        tabs.add(self.params_table, text="Query")

        body_frame = ttk.Frame(tabs)
        tabs.add(body_frame, text="Body (JSON)")

        self.body_hint_var = tk.StringVar(value="Pegá/edita JSON para el body (POST/PUT/PATCH). Con OpenAPI, se precarga automáticamente.")
        ttk.Label(body_frame, textvariable=self.body_hint_var).pack(anchor="w", padx=6, pady=(6,4))
        self.body_text = ScrolledText(body_frame, height=12)
        self.body_text.pack(fill="both", expand=True, padx=6, pady=(0,6))
        self.body_text.insert("1.0", "{\n  \n}")

        btn_row = ttk.Frame(req_frame)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0,8))
        btn_row.grid_columnconfigure(0, weight=1)

        self.timeout_var = tk.IntVar(value=30)
        ttk.Label(btn_row, text="Timeout (s):").pack(side="left")
        ttk.Spinbox(btn_row, from_=1, to=300, textvariable=self.timeout_var, width=5).pack(side="left", padx=(6,10))

        ttk.Button(btn_row, text="Precargar desde OpenAPI", command=self._prefill_from_openapi).pack(side="right")
        ttk.Button(btn_row, text="Enviar", command=self._send_request).pack(side="right", padx=(0,6))
        ttk.Button(btn_row, text="Limpiar respuesta", command=self._clear_response).pack(side="right", padx=(0,6))

        resp_frame = ttk.LabelFrame(right, text="Response")
        resp_frame.grid(row=1, column=0, sticky="nsew")
        resp_frame.grid_rowconfigure(1, weight=1)
        resp_frame.grid_columnconfigure(0, weight=1)

        self.resp_meta_var = tk.StringVar(value="(sin respuesta)")
        ttk.Label(resp_frame, textvariable=self.resp_meta_var).grid(row=0, column=0, sticky="w", padx=8, pady=6)

        self.resp_text = ScrolledText(resp_frame)
        self.resp_text.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0,8))

        self.pack(fill="both", expand=True)

        self.headers_table.set_items({
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer <token>",
        })

    def _browse_source(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleccionar ZIP",
            filetypes=[("ZIP", "*.zip"), ("Todos", "*.*")]
        )
        if not path:
            path = filedialog.askdirectory(title="Seleccionar carpeta")
        if path:
            self.source_var.set(path)

    def _load_endpoints_from_zip(self) -> None:
        path = self.source_var.get().strip()
        if not path:
            messagebox.showwarning("Falta fuente", "Seleccioná un ZIP o carpeta con routers.")
            return
        try:
            self.endpoints = load_endpoints(path)
        except Exception as e:
            messagebox.showerror("Error cargando endpoints", f"{e}\n\n{traceback.format_exc()}")
            return
        self._apply_filter()
        messagebox.showinfo("OK", f"Cargados {len(self.endpoints)} endpoints desde ZIP/carpeta.")

    def _sync_openapi(self) -> None:
        base_url = (self.base_url_var.get() or "").strip().rstrip("/")
        if not base_url:
            messagebox.showwarning("Falta Base URL", "Indicá Base URL para descargar /openapi.json.")
            return

        try:
            self.openapi = OpenAPISpec.from_base_url(base_url, verify=bool(self.verify_tls_var.get()))
        except Exception as e:
            messagebox.showerror("No se pudo sincronizar OpenAPI", f"{e}\n\nTip: verificá que exista {base_url}/openapi.json")
            self.openapi = None
            return

        merged = { (ep.method.upper(), ep.path): ep for ep in self.endpoints }
        for (m,p), op in self.openapi.iter_operations():
            if (m,p) not in merged:
                merged[(m,p)] = Endpoint(method=m, path=p, file="openapi", func_name=None, summary=op.get("summary") or op.get("operationId"))
            else:
                old = merged[(m,p)]
                merged[(m,p)] = Endpoint(method=old.method, path=old.path, file=old.file, func_name=old.func_name, summary=op.get("summary") or op.get("operationId"))

        self.endpoints = sorted(list(merged.values()), key=lambda e: (e.path, e.method))
        self._apply_filter()
        messagebox.showinfo("OpenAPI OK", f"OpenAPI sincronizado. Endpoints disponibles: {len(self.endpoints)}")

    def _apply_filter(self) -> None:
        flt = (self.filter_var.get() or "").strip().lower()
        if not flt:
            self.filtered_endpoints = list(self.endpoints)
        else:
            def ok(ep: Endpoint) -> bool:
                hay = f"{ep.method} {ep.path} {ep.summary or ''} {ep.func_name or ''} {ep.file or ''}".lower()
                return flt in hay
            self.filtered_endpoints = [ep for ep in self.endpoints if ok(ep)]

        for i in self.ep_tree.get_children():
            self.ep_tree.delete(i)
        for idx, ep in enumerate(self.filtered_endpoints):
            self.ep_tree.insert("", "end", iid=str(idx), values=(ep.method, ep.path, ep.summary or "", ep.file or ""))

    def _selected_endpoint(self) -> Optional[Endpoint]:
        sel = self.ep_tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        return self.filtered_endpoints[idx]

    def _on_select_endpoint(self) -> None:
        ep = self._selected_endpoint()
        if not ep:
            return
        self.endpoint_var.set(f"{ep.method} {ep.path}")

        self._prefill_from_openapi(auto=True)

        if not self.openapi:
            if "{" in ep.path and "}" in ep.path:
                params = self.params_table.get_items()
                for part in ep.path.split("/"):
                    if part.startswith("{") and part.endswith("}"):
                        k = part[1:-1]
                        params.setdefault(k, "")
                self.params_table.set_items(params)

            if ep.method in ("POST", "PUT", "PATCH"):
                if self.body_text.get("1.0", "end").strip() in ("", "{}", "{\n  \n}"):
                    self.body_text.delete("1.0", "end")
                    self.body_text.insert("1.0", "{\n  \n}")

    def _prefill_from_openapi(self, auto: bool=False) -> None:
        ep = self._selected_endpoint()
        if not ep or not self.openapi:
            if not auto:
                messagebox.showinfo("OpenAPI", "Sin OpenAPI cargado. Tocá 'Sincronizar OpenAPI' primero.")
            return

        op = self.openapi.get_operation(ep.method, ep.path)
        if not op:
            if not auto:
                messagebox.showinfo("OpenAPI", "No se encontró la operación en OpenAPI para ese endpoint.")
            return

        headers = self.headers_table.get_items()
        headers.setdefault("accept", "application/json")
        ct = self.openapi.preferred_content_type(op) or "application/json"
        headers.setdefault("Content-Type", ct)
        for hkey, hval in self.openapi.suggest_auth_headers(op).items():
            headers.setdefault(hkey, hval)
        self.headers_table.set_items(headers)

        params = self.openapi.suggest_parameters(op, ep.path)
        existing = self.params_table.get_items()
        for k,v in params.items():
            existing.setdefault(k, v)
        self.params_table.set_items(existing)

        if ep.method in ("POST", "PUT", "PATCH", "DELETE"):
            tmpl = self.openapi.build_request_body_template(op)
            if tmpl is not None:
                self.body_text.delete("1.0", "end")
                self.body_text.insert("1.0", json.dumps(tmpl, indent=2, ensure_ascii=False))

    def _clear_response(self) -> None:
        self.resp_meta_var.set("(sin respuesta)")
        self.resp_text.delete("1.0", "end")

    def _send_request(self) -> None:
        ep = self._selected_endpoint()
        if not ep:
            messagebox.showwarning("Sin endpoint", "Seleccioná un endpoint en la lista.")
            return

        base_url = (self.base_url_var.get() or "").strip().rstrip("/")
        if not base_url:
            messagebox.showwarning("Falta Base URL", "Indicá la Base URL (ej: https://api.midominio.com).")
            return

        path = ep.path
        qparams = self.params_table.get_items()

        for k, v in list(qparams.items()):
            token = "{" + k + "}"
            if token in path and v:
                path = path.replace(token, str(v))
                qparams.pop(k, None)

        url = base_url + path
        headers = self.headers_table.get_items()

        body_obj = None
        if ep.method in ("POST", "PUT", "PATCH", "DELETE"):
            body_raw = self.body_text.get("1.0", "end").strip()
            if body_raw and body_raw not in ("{}", ""):
                try:
                    body_obj = json.loads(body_raw)
                except Exception:
                    messagebox.showerror("JSON inválido", "El body no es JSON válido. Corregilo e intentá de nuevo.")
                    return

        timeout_s = max(1, int(self.timeout_var.get()))
        verify_tls = bool(self.verify_tls_var.get())

        self.resp_meta_var.set(f"Enviando {ep.method} {url} …")
        self.resp_text.delete("1.0", "end")
        self.update_idletasks()

        try:
            t0 = time.perf_counter()
            resp = requests.request(
                method=ep.method,
                url=url,
                headers=headers,
                params=qparams or None,
                json=body_obj,
                timeout=timeout_s,
                verify=verify_tls,
            )
            dt_ms = (time.perf_counter() - t0) * 1000.0
            meta = f"HTTP {resp.status_code} • {dt_ms:.0f} ms • {resp.headers.get('content-type','(sin content-type)')}"
            self.resp_meta_var.set(meta)

            try:
                data = resp.json()
                body = json.dumps(data, indent=2, ensure_ascii=False)
            except Exception:
                body = resp.text

            hdr_lines = "\n".join([f"{k}: {v}" for k,v in resp.headers.items()])
            out = f"URL: {url}\n\n--- REQUEST ---\nHeaders:\n{json.dumps(headers, indent=2, ensure_ascii=False)}\n\nParams:\n{json.dumps(qparams, indent=2, ensure_ascii=False)}\n\nBody:\n{json.dumps(body_obj, indent=2, ensure_ascii=False) if body_obj is not None else '(sin body)'}\n\n--- RESPONSE HEADERS ---\n{hdr_lines}\n\n--- BODY ---\n{body}\n"
            self.resp_text.insert("1.0", out)

        except requests.exceptions.ConnectionError:
            msg = (
                "No se pudo conectar al servidor.\n\n"
                f"URL: {url}\n\n"
                "Causas típicas:\n"
                "• La API no está levantada.\n"
                "• Base URL/puerto incorrectos.\n"
                "• Estás usando http vs https.\n\n"
                "Acciones:\n"
                "• Verificá el puerto real (docker ps / compose)\n"
                "• Probá con 127.0.0.1 en lugar de localhost\n"
                "• Si es remoto, confirmá VPN / firewall / whitelisting"
            )
            messagebox.showerror("Conexión rechazada", msg)
            self.resp_meta_var.set("Conexión rechazada")
        except requests.exceptions.SSLError as e:
            messagebox.showerror("TLS/SSL error", f"{e}\n\nTip: desmarcá 'Verificar TLS' en homologación con certs no confiables.")
            self.resp_meta_var.set("Error TLS/SSL")
        except Exception as e:
            messagebox.showerror("Error enviando request", f"{e}\n\n{traceback.format_exc()}")
            self.resp_meta_var.set("Error")


def main() -> None:
    root = tk.Tk()
    try:
        root.tk.call("source", "azure.tcl")
        root.tk.call("set_theme", "light")
    except Exception:
        pass
    ApiTesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
