"""Translate Codex Responses API requests to DeepSeek chat completions."""

import json
import os
import sys
import urllib.error
import urllib.request
import requests
import uuid
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
HOST = "127.0.0.1"
PORT = 8898
CALL_REASONING = {}
CALL_REASONING_LOCK = threading.Lock()


def text_content(content):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return json.dumps(content, ensure_ascii=False)
    parts = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict):
            parts.append(item.get("text") or item.get("input_text") or "")
    return "\n".join(filter(None, parts))


def flush_pending_calls(messages, pending_calls):
    if not pending_calls:
        return []
    message = {"role": "assistant", "content": None, "tool_calls": pending_calls}
    with CALL_REASONING_LOCK:
        reasoning = "".join(CALL_REASONING.get(call["id"], "") for call in pending_calls)
    if reasoning:
        message["reasoning_content"] = reasoning
    messages.append(message)
    return []


def to_messages(body):
    system_parts = []
    if body.get("instructions"):
        system_parts.append(str(body["instructions"]).strip())
    messages = []
    pending_calls = []
    for item in body.get("input", []):
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind == "message":
            role = item.get("role", "user")
            content = text_content(item.get("content", ""))
            if role in ("developer", "system"):
                text = content.strip()
                if text:
                    system_parts.append(text)
                continue
            pending_calls = flush_pending_calls(messages, pending_calls)
            messages.append({"role": role, "content": content})
        elif kind in ("function_call", "custom_tool_call"):
            call_id = item.get("call_id") or item.get("id") or f"call_{uuid.uuid4().hex}"
            args = item.get("arguments") or item.get("input") or "{}"
            pending_calls.append({"id": call_id, "type": "function", "function": {"name": item.get("name", "tool"), "arguments": args}})
        elif kind in ("function_call_output", "custom_tool_call_output"):
            pending_calls = flush_pending_calls(messages, pending_calls)
            messages.append({"role": "tool", "tool_call_id": item.get("call_id"), "content": text_content(item.get("output", ""))})
    flush_pending_calls(messages, pending_calls)
    if system_parts:
        return [{"role": "system", "content": "\n\n".join(system_parts)}] + messages
    return messages


def to_tools(tools):
    result = []
    for tool in tools or []:
        if tool.get("type") == "function":
            function = tool.get("function") or {k: tool[k] for k in ("name", "description", "parameters") if k in tool}
            result.append({"type": "function", "function": function})
        elif tool.get("name"):
            result.append({"type": "function", "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object", "additionalProperties": True}),
            }})
    return result


def sse(handler, event):
    handler.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode())
    handler.wfile.flush()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self):
        if self.path.rstrip("/") != "/v1/responses":
            self.send_error(404)
            return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        with open(os.path.join(os.path.dirname(__file__), "last-request.json"), "w", encoding="utf-8") as capture:
            json.dump(body, capture, ensure_ascii=False, indent=2)
        request_body = {
            "model": os.environ.get("DEEPSEEK_MODEL") or body.get("model", "deepseek-v4-pro"),
            "messages": to_messages(body),
            "stream": True,
        }
        tools = to_tools(body.get("tools"))
        if tools:
            request_body.update({"tools": tools, "tool_choice": "auto"})
        with open(os.path.join(os.path.dirname(__file__), "last-upstream-request.json"), "w", encoding="utf-8") as capture:
            json.dump(request_body, capture, ensure_ascii=False, indent=2)
        key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        req = urllib.request.Request(DEEPSEEK_URL, json.dumps(request_body).encode(), {
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"
        })
        try:
            upstream = requests.post(
                DEEPSEEK_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json=request_body,
                stream=True,
                timeout=300,
            )
            if upstream.status_code >= 400:
                payload = upstream.content
                print(f"HTTP {upstream.status_code}: {payload[:2000]!r}", file=sys.stderr, flush=True)
                self.send_response(upstream.status_code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            with open(os.path.join(os.path.dirname(__file__), "proxy-upstream-error.log"), "ab") as log:
                log.write(f"HTTP {exc.code} tools={len(tools)} messages={len(request_body['messages'])}\n".encode())
                log.write(payload + b"\n")
            self.send_response(exc.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        except Exception as exc:
            print(repr(exc), file=sys.stderr, flush=True)
            payload = json.dumps({"error": {"message": str(exc)}}).encode()
            with open(os.path.join(os.path.dirname(__file__), "proxy-upstream-error.log"), "ab") as log:
                log.write(repr(exc).encode() + b"\n")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        response_id = f"resp_{uuid.uuid4().hex}"
        sse(self, {"type": "response.created", "response": {"id": response_id}})
        content, reasoning, calls, usage, message_id = [], [], {}, {}, f"msg_{uuid.uuid4().hex}"
        for raw in upstream.iter_lines():
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[5:].strip())
            usage = chunk.get("usage") or usage
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            if delta.get("reasoning_content"):
                reasoning.append(delta["reasoning_content"])
            if delta.get("content"):
                if not content:
                    sse(self, {"type": "response.output_item.added", "item": {"type": "message", "role": "assistant", "id": message_id, "content": []}})
                content.append(delta["content"])
                sse(self, {"type": "response.output_text.delta", "delta": delta["content"]})
            for tc in delta.get("tool_calls") or []:
                index = tc.get("index", 0)
                entry = calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
                entry["id"] = tc.get("id") or entry["id"]
                fn = tc.get("function") or {}
                entry["name"] += fn.get("name", "")
                entry["arguments"] += fn.get("arguments", "")
        if content:
            text = "".join(content)
            sse(self, {"type": "response.output_item.done", "item": {"type": "message", "role": "assistant", "id": message_id, "content": [{"type": "output_text", "text": text}]}})
        for call in calls.values():
            if reasoning:
                with CALL_REASONING_LOCK:
                    CALL_REASONING[call["id"]] = "".join(reasoning)
            sse(self, {"type": "response.output_item.done", "item": {"type": "function_call", "call_id": call["id"] or f"call_{uuid.uuid4().hex}", "name": call["name"], "arguments": call["arguments"] or "{}"}})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        sse(self, {"type": "response.completed", "response": {"id": response_id, "usage": {"input_tokens": prompt_tokens, "output_tokens": completion_tokens, "total_tokens": usage.get("total_tokens", prompt_tokens + completion_tokens)}}})

    def log_message(self, fmt, *args):
        sys.stderr.write((fmt % args) + "\n")


if __name__ == "__main__":
    if not os.environ.get("DEEPSEEK_API_KEY"):
        raise SystemExit("DEEPSEEK_API_KEY is not set")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
