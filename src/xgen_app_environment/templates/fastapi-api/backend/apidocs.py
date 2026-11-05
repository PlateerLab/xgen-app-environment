"""API 명세 페이지 — platform glue, leave this file alone.

backend/serve.py reads the app's OpenAPI schema (the same one /api/openapi.json
answers) and this module turns it into one page a person can read: for every
endpoint its description, parameters, a request JSON example, a response JSON
example and a curl line. Plain HTML, no outside assets, so it opens anywhere
(the app tab, a new window, the deployed address, an air-gapped site).

The examples are generated from the pydantic models unless the schema carries
its own (``example`` / ``examples`` / ``default`` on a field or model).
"""

import html
import json

_METHODS = ("get", "post", "put", "patch", "delete")
_MAX_DEPTH = 6
_SKIP_RESPONSES = {"422"}  # FastAPI's validation-error boilerplate — noise for a reader


# ── schema walking ──────────────────────────────────────────────────────────

def _resolve(schema, root):
    """Follow ``$ref`` (only local ``#/components/schemas/...``)."""
    seen = 0
    while isinstance(schema, dict) and "$ref" in schema and seen < 20:
        ref = str(schema["$ref"])
        node = root
        for part in ref.lstrip("#/").split("/"):
            node = node.get(part) if isinstance(node, dict) else None
        if not isinstance(node, dict):
            return {}
        schema = node
        seen += 1
    return schema if isinstance(schema, dict) else {}


def _variants(schema):
    for key in ("anyOf", "oneOf", "allOf"):
        items = schema.get(key)
        if isinstance(items, list) and items:
            return [v for v in items if isinstance(v, dict)]
    return []


def _pick(schema, root):
    """The schema to describe: unwrap unions, skipping ``null`` when there is something else."""
    schema = _resolve(schema, root)
    variants = _variants(schema)
    if variants:
        non_null = [v for v in variants if _resolve(v, root).get("type") != "null"] or variants
        merged = dict(_resolve(non_null[0], root))
        for extra in ("title", "description", "example", "examples", "default"):
            if extra in schema and extra not in merged:
                merged[extra] = schema[extra]
        return merged
    return schema


def type_name(schema, root):
    """``string``, ``integer``, ``array<string>``, ``object``, a model title or ``any``."""
    schema = _pick(schema, root)
    kind = schema.get("type")
    if kind == "array":
        return f"array<{type_name(schema.get('items') or {}, root)}>"
    if kind == "object" or "properties" in schema:
        return str(schema.get("title") or "object")
    if isinstance(kind, str):
        fmt = schema.get("format")
        return f"{kind}({fmt})" if fmt else kind
    if "enum" in schema:
        return "enum"
    return "any"


def example(schema, root, depth=0):
    """A sample value for the schema — the declared example when there is one, otherwise built from the types."""
    schema = _pick(schema, root)
    for key in ("example", "default"):
        if key in schema:
            return schema[key]
    examples = schema.get("examples")
    if isinstance(examples, list) and examples:
        return examples[0]
    if isinstance(examples, dict) and examples:
        first = next(iter(examples.values()))
        return first.get("value", first) if isinstance(first, dict) else first
    if depth > _MAX_DEPTH:
        return "…"
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return enum[0]
    kind = schema.get("type")
    if kind == "array":
        return [example(schema.get("items") or {}, root, depth + 1)]
    if kind == "object" or "properties" in schema:
        props = schema.get("properties") or {}
        if not props:
            return {}
        return {str(name): example(prop, root, depth + 1) for name, prop in props.items()}
    if kind == "string":
        fmt = schema.get("format")
        return {"date": "2026-01-01", "date-time": "2026-01-01T09:00:00Z", "uuid": "00000000-0000-0000-0000-000000000000",
                "email": "user@example.com", "uri": "https://example.com", "binary": "<file>"}.get(fmt, "string")
    if kind == "integer":
        return 0
    if kind == "number":
        return 0.0
    if kind == "boolean":
        return True
    if kind == "null":
        return None
    return {}


def fields(schema, root):
    """``[{name, type, required, description}]`` for an object schema; empty for scalars."""
    schema = _pick(schema, root)
    props = schema.get("properties")
    if not isinstance(props, dict):
        return []
    required = set(schema.get("required") or [])
    out = []
    for name, prop in props.items():
        resolved = _pick(prop, root)
        out.append({
            "name": str(name),
            "type": type_name(prop, root),
            "required": name in required,
            "description": str(resolved.get("description") or ""),
        })
    return out


# ── the model of the page ───────────────────────────────────────────────────

def summary(schema):
    """The short list: ``[{method, path, summary}]`` — what the JSON index answers."""
    out = []
    for path, item in sorted((schema.get("paths") or {}).items()):
        if not isinstance(item, dict):
            continue
        for method in _METHODS:
            op = item.get(method)
            if isinstance(op, dict):
                out.append({"method": method.upper(), "path": str(path),
                            "summary": str(op.get("summary") or op.get("description") or "")})
    return out


def endpoints(schema):
    """Everything the page shows per endpoint, resolved and with examples built."""
    root = schema if isinstance(schema, dict) else {}
    out = []
    for path, item in sorted((root.get("paths") or {}).items()):
        if not isinstance(item, dict):
            continue
        for method in _METHODS:
            op = item.get(method)
            if not isinstance(op, dict):
                continue
            params = []
            for p in (item.get("parameters") or []) + (op.get("parameters") or []):
                if not isinstance(p, dict):
                    continue
                p = _resolve(p, root)
                params.append({
                    "name": str(p.get("name") or ""), "in": str(p.get("in") or ""),
                    "type": type_name(p.get("schema") or {}, root), "required": bool(p.get("required")),
                    "description": str(p.get("description") or ""),
                    "example": example(p.get("schema") or {}, root),
                })
            body = None
            rb = op.get("requestBody")
            if isinstance(rb, dict):
                content = _resolve(rb, root).get("content") or {}
                for ctype, media in content.items():
                    if not isinstance(media, dict):
                        continue
                    sch = media.get("schema") or {}
                    body = {"content_type": str(ctype), "fields": fields(sch, root),
                            "example": media.get("example", example(sch, root)), "required": bool(rb.get("required", True))}
                    break
            responses = []
            for code, resp in sorted((op.get("responses") or {}).items()):
                if str(code) in _SKIP_RESPONSES or not isinstance(resp, dict):
                    continue
                resp = _resolve(resp, root)
                content = resp.get("content") or {}
                sch, ctype, ex = None, "", None
                for ctype_, media in content.items():
                    if isinstance(media, dict):
                        sch, ctype = media.get("schema") or {}, str(ctype_)
                        ex = media.get("example", example(sch, root))
                        break
                responses.append({"code": str(code), "description": str(resp.get("description") or ""),
                                  "content_type": ctype, "fields": fields(sch, root) if sch is not None else [],
                                  "example": ex, "has_body": sch is not None})
            out.append({
                "method": method.upper(), "path": str(path),
                "summary": str(op.get("summary") or ""), "description": str(op.get("description") or ""),
                "params": params, "body": body, "responses": responses,
                "deprecated": bool(op.get("deprecated")),
            })
    return out


# ── HTML ────────────────────────────────────────────────────────────────────

_CSS = (
    "body{font:14px/1.55 system-ui,-apple-system,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;margin:0;color:#1f2937;background:#fff}"
    "main{max-width:960px;margin:0 auto;padding:28px 24px 64px}"
    "h1{font-size:22px;margin:0 0 4px}.lead{color:#6b7280;margin:0 0 20px}"
    ".note{background:#f3f4f6;border-radius:8px;padding:10px 14px;margin:0 0 24px;color:#374151}"
    ".note code{background:#fff}"
    "nav ul{list-style:none;padding:0;margin:0 0 28px;display:flex;flex-wrap:wrap;gap:6px}"
    "nav a{display:inline-block;border:1px solid #e5e7eb;border-radius:999px;padding:3px 10px;font:12px ui-monospace,monospace;color:#1f2937;text-decoration:none}"
    "section{border-top:1px solid #e5e7eb;padding:22px 0 8px}"
    "h2{font-size:16px;margin:0 0 4px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}"
    ".m{font:12px ui-monospace,monospace;font-weight:700;padding:2px 8px;border-radius:4px;color:#fff;background:#6b7280}"
    ".m.GET{background:#2563eb}.m.POST{background:#16a34a}.m.PUT{background:#d97706}.m.PATCH{background:#d97706}.m.DELETE{background:#dc2626}"
    ".p{font:14px ui-monospace,monospace}.dep{color:#dc2626;font-size:12px}"
    ".sum{margin:0 0 4px;font-weight:600}.desc{margin:0 0 12px;color:#4b5563;white-space:pre-line}"
    "h3{font-size:13px;margin:16px 0 6px;color:#374151}"
    "table{border-collapse:collapse;width:100%;margin:0 0 8px}"
    "th{font-size:12px;text-align:left;color:#6b7280;font-weight:600;padding:4px 8px;border-bottom:1px solid #e5e7eb}"
    "td{padding:5px 8px;border-bottom:1px solid #f3f4f6;vertical-align:top}"
    "td.n{font:13px ui-monospace,monospace;white-space:nowrap}td.t{font:12px ui-monospace,monospace;color:#6b7280;white-space:nowrap}"
    ".req{color:#dc2626;font-size:11px;margin-left:4px}"
    "pre{background:#111827;color:#e5e7eb;border-radius:8px;padding:12px 14px;overflow:auto;font:12.5px/1.5 ui-monospace,monospace;margin:0 0 10px}"
    ".muted{color:#9ca3af}"
    "@media (prefers-color-scheme:dark){body{background:#0b1220;color:#e5e7eb}.lead,.desc,th,td.t{color:#9ca3af}"
    ".note{background:#111827;color:#d1d5db}.note code{background:#1f2937}nav a{border-color:#374151;color:#e5e7eb}"
    "section,th{border-color:#1f2937}td{border-color:#111827}h3{color:#d1d5db}pre{background:#000}}"
)

_SCRIPT = (
    "<script>(function(){var b=location.href.replace(/[?#].*$/,'').replace(/\\/(api\\/docs)?\\/?$/,'');"
    "document.querySelectorAll('[data-base]').forEach(function(e){e.textContent=e.textContent.split('__BASE__').join(b)});"
    "var a=document.getElementById('addr');if(a){a.textContent=b+'/'}})();</script>"
)


def _pretty(value):
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(value)


def _table(rows, *, with_in=False):
    head = "<tr><th>이름</th>" + ("<th>위치</th>" if with_in else "") + "<th>타입</th><th>설명</th></tr>"
    body = "".join(
        "<tr><td class=n>{n}{r}</td>{i}<td class=t>{t}</td><td>{d}</td></tr>".format(
            n=html.escape(r["name"]), r="<span class=req>필수</span>" if r.get("required") else "",
            i=f"<td class=t>{html.escape(r.get('in', ''))}</td>" if with_in else "",
            t=html.escape(r["type"]), d=html.escape(r.get("description") or ""),
        )
        for r in rows
    )
    return f"<table>{head}{body}</table>"


def _curl(ep):
    query = "&".join(f"{p['name']}={html.escape(str(p['example']))}" for p in ep["params"] if p["in"] == "query")
    url = f"__BASE__{ep['path']}" + (f"?{query}" if query else "")
    parts = [f"curl -X {ep['method']} '{url}'"]
    parts.append("-H 'Authorization: Bearer <키>'")
    if ep["body"] is not None:
        parts.append(f"-H 'Content-Type: {ep['body']['content_type']}'")
        parts.append("-d '" + json.dumps(ep["body"]["example"], ensure_ascii=False) + "'")
    return " \\\n  ".join(parts)


def _section(ep):
    anchor = f"{ep['method']}-{ep['path']}".replace("/", "-")
    out = [f"<section id='{html.escape(anchor)}'>"]
    out.append(
        f"<h2><span class='m {ep['method']}'>{ep['method']}</span><span class=p>{html.escape(ep['path'])}</span>"
        + ("<span class=dep>더 이상 쓰지 않음</span>" if ep["deprecated"] else "") + "</h2>"
    )
    if ep["summary"]:
        out.append(f"<p class=sum>{html.escape(ep['summary'])}</p>")
    if ep["description"]:
        out.append(f"<p class=desc>{html.escape(ep['description'])}</p>")
    if ep["params"]:
        out.append("<h3>인자</h3>" + _table(ep["params"], with_in=True))
    body = ep["body"]
    if body is not None:
        out.append(f"<h3>요청 본문 <span class=muted>({html.escape(body['content_type'])})</span></h3>")
        if body["fields"]:
            out.append(_table(body["fields"]))
        out.append(f"<pre>{html.escape(_pretty(body['example']), quote=False)}</pre>")
    elif not ep["params"]:
        out.append("<h3>요청</h3><p class=muted>보내는 값이 없다.</p>")
    for resp in ep["responses"]:
        label = f"응답 {html.escape(resp['code'])}"
        if resp["description"]:
            label += f" <span class=muted>{html.escape(resp['description'])}</span>"
        out.append(f"<h3>{label}</h3>")
        if resp["fields"]:
            out.append(_table(resp["fields"]))
        if resp["has_body"]:
            out.append(f"<pre>{html.escape(_pretty(resp['example']), quote=False)}</pre>")
    out.append("<h3>curl</h3><pre data-base>" + html.escape(_curl(ep), quote=False) + "</pre>")
    out.append("</section>")
    return "".join(out)


def render(schema):
    """The whole page for the schema."""
    root = schema if isinstance(schema, dict) else {}
    info = root.get("info") or {}
    title = str(info.get("title") or "api")
    version = str(info.get("version") or "")
    eps = endpoints(root)
    nav = "".join(
        "<li><a href='#{a}'>{m} {p}</a></li>".format(
            a=html.escape(f"{e['method']}-{e['path']}".replace("/", "-")), m=e["method"], p=html.escape(e["path"]))
        for e in eps
    )
    sections = "".join(_section(e) for e in eps) or "<section><p class=muted>아직 끝점이 없다.</p></section>"
    return (
        "<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)} 명세</title><style>{_CSS}</style></head><body><main>"
        f"<h1>{html.escape(title)}</h1>"
        f"<p class=lead>API 명세{(' · 버전 ' + html.escape(version)) if version else ''} · 끝점 {len(eps)}개"
        + (f"<br>{html.escape(str(info.get('description')))}" if info.get("description") else "") + "</p>"
        "<p class=note>주소는 <code id=addr>이 페이지의 주소</code> 뒤에 끝점 경로를 붙인다. "
        "API로 배포된 주소(<code>/v1/</code>, <code>/v2/</code> …)를 부를 때는 <code>Authorization: Bearer &lt;키&gt;</code> 헤더가 필요하고, "
        "앱 자신의 주소를 로그인한 브라우저에서 부를 때는 필요 없다. 규격 원문은 <code>api/openapi.json</code>.</p>"
        f"<nav><ul>{nav}</ul></nav>{sections}</main>{_SCRIPT}</body></html>"
    )
