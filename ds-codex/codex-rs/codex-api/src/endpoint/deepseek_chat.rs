use crate::auth::SharedAuthProvider;
use crate::common::ResponseEvent;
use crate::common::ResponseStream;
use crate::common::ResponsesApiRequest;
use crate::endpoint::session::EndpointSession;
use crate::error::ApiError;
use crate::provider::Provider;
use codex_client::HttpTransport;
use codex_client::RequestTelemetry;
use codex_client::StreamResponse;
use codex_protocol::models::ContentItem;
use codex_protocol::models::FunctionCallOutputBody;
use codex_protocol::models::ResponseItem;
use codex_protocol::protocol::TokenUsage;
use futures::StreamExt;
use http::HeaderValue;
use http::Method;
use serde::Deserialize;
use serde_json::Value;
use serde_json::json;
use std::collections::BTreeMap;
use std::collections::HashMap;
use std::collections::HashSet;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::mpsc;
use tokio::time::timeout;

pub struct DeepSeekChatClient<T: HttpTransport> {
    session: EndpointSession<T>,
}

impl<T: HttpTransport> DeepSeekChatClient<T> {
    pub fn new(transport: T, provider: Provider, auth: SharedAuthProvider) -> Self {
        Self {
            session: EndpointSession::new(transport, provider, auth),
        }
    }

    pub fn with_request_telemetry(mut self, telemetry: Option<Arc<dyn RequestTelemetry>>) -> Self {
        self.session = self.session.with_request_telemetry(telemetry);
        self
    }

    pub async fn stream_request(
        &self,
        request: ResponsesApiRequest,
        options: crate::endpoint::responses::ResponsesOptions,
    ) -> Result<ResponseStream, ApiError> {
        let (tools, tool_mappings) = translate_tools(&request.tools);
        let body = responses_to_chat_body(&request, tools);
        let stream_idle_timeout = self.session.provider().stream_idle_timeout;
        let stream_response = self
            .session
            .stream_with(
                Method::POST,
                "chat/completions",
                options.extra_headers,
                Some(body),
                |req| {
                    req.headers.insert(
                        http::header::ACCEPT,
                        HeaderValue::from_static("text/event-stream"),
                    );
                },
            )
            .await?;

        Ok(spawn_deepseek_chat_stream(
            stream_response,
            tool_mappings,
            stream_idle_timeout,
        ))
    }
}

fn responses_to_chat_body(request: &ResponsesApiRequest, tools: Vec<Value>) -> Value {
    let mut messages = Vec::new();
    if !request.instructions.trim().is_empty() {
        messages.push(json!({"role": "system", "content": request.instructions}));
    }
    let mut pending_calls: Vec<Value> = Vec::new();
    for item in &request.input {
        match item {
            ResponseItem::Message { role, content, .. } => {
                flush_pending_calls(&mut messages, &mut pending_calls);
                let role = if role == "developer" {
                    "system"
                } else {
                    role.as_str()
                };
                messages.push(json!({"role": role, "content": content_items_to_text(content)}));
            }
            ResponseItem::FunctionCall {
                call_id,
                name,
                arguments,
                ..
            } => pending_calls.push(json!({
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": arguments}
            })),
            ResponseItem::CustomToolCall {
                call_id,
                name,
                input,
                ..
            } => pending_calls.push(json!({
                "id": call_id,
                "type": "function",
                "function": {"name": name, "arguments": json!({"input": input}).to_string()}
            })),
            ResponseItem::FunctionCallOutput { call_id, output } => {
                flush_pending_calls(&mut messages, &mut pending_calls);
                messages.push(json!({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": function_output_to_text(&output.body)
                }));
            }
            ResponseItem::CustomToolCallOutput {
                call_id, output, ..
            } => {
                flush_pending_calls(&mut messages, &mut pending_calls);
                messages.push(json!({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": function_output_to_text(&output.body)
                }));
            }
            _ => {}
        }
    }
    flush_pending_calls(&mut messages, &mut pending_calls);

    let mut body = json!({
        "model": request.model,
        "messages": messages,
        "stream": true,
        "stream_options": {"include_usage": true},
    });
    if !tools.is_empty() {
        body["tools"] = Value::Array(tools);
        body["tool_choice"] = Value::String(request.tool_choice.clone());
    }
    body
}

fn flush_pending_calls(messages: &mut Vec<Value>, pending_calls: &mut Vec<Value>) {
    if !pending_calls.is_empty() {
        messages.push(json!({
            "role": "assistant",
            "content": null,
            "tool_calls": std::mem::take(pending_calls),
        }));
    }
}

fn content_items_to_text(content: &[ContentItem]) -> String {
    content
        .iter()
        .filter_map(|item| match item {
            ContentItem::InputText { text } | ContentItem::OutputText { text } => {
                Some(text.as_str())
            }
            ContentItem::InputImage { .. } => None,
        })
        .collect::<Vec<_>>()
        .join("\n")
}

fn function_output_to_text(body: &FunctionCallOutputBody) -> String {
    body.to_text().unwrap_or_default()
}

#[derive(Default)]
struct ToolMappings {
    custom_names: HashSet<String>,
    namespaces: HashMap<String, (String, String)>,
}

fn translate_tools(tools: &[Value]) -> (Vec<Value>, ToolMappings) {
    let mut translated = Vec::new();
    let mut mappings = ToolMappings::default();
    for tool in tools {
        match tool.get("type").and_then(Value::as_str) {
            Some("function") => translated.push(responses_tool_to_chat(tool)),
            Some("custom") => {
                let name = tool.get("name").and_then(Value::as_str).unwrap_or("tool");
                mappings.custom_names.insert(name.to_string());
                translated.push(json!({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": tool.get("description").cloned().unwrap_or(Value::String(String::new())),
                        "parameters": {
                            "type": "object",
                            "properties": {"input": {"type": "string"}},
                            "required": ["input"],
                            "additionalProperties": false
                        }
                    }
                }));
            }
            Some("namespace") => {
                let namespace = tool
                    .get("name")
                    .and_then(Value::as_str)
                    .unwrap_or("namespace");
                for nested in tool
                    .get("tools")
                    .and_then(Value::as_array)
                    .into_iter()
                    .flatten()
                {
                    let name = nested.get("name").and_then(Value::as_str).unwrap_or("tool");
                    let wire_name = format!("{namespace}__{name}");
                    mappings
                        .namespaces
                        .insert(wire_name.clone(), (namespace.to_string(), name.to_string()));
                    let mut nested = nested.clone();
                    nested["name"] = Value::String(wire_name);
                    translated.push(responses_tool_to_chat(&nested));
                }
            }
            // DeepSeek has no equivalents for OpenAI-hosted tools.
            _ => {}
        }
    }
    (translated, mappings)
}

fn responses_tool_to_chat(tool: &Value) -> Value {
    if tool.get("function").is_some() {
        return tool.clone();
    }
    json!({
        "type": "function",
        "function": {
            "name": tool.get("name").cloned().unwrap_or(Value::String("tool".to_string())),
            "description": tool.get("description").cloned().unwrap_or(Value::String(String::new())),
            "parameters": tool.get("parameters").cloned().unwrap_or_else(|| json!({"type":"object","additionalProperties": true})),
        }
    })
}

fn spawn_deepseek_chat_stream(
    stream_response: StreamResponse,
    tool_mappings: ToolMappings,
    stream_idle_timeout: Duration,
) -> ResponseStream {
    let (tx_event, rx_event) = mpsc::channel::<Result<ResponseEvent, ApiError>>(1600);
    tokio::spawn(async move {
        process_deepseek_chat_stream(
            stream_response,
            tx_event,
            tool_mappings,
            stream_idle_timeout,
        )
        .await;
    });
    ResponseStream {
        rx_event,
        upstream_request_id: None,
    }
}

#[derive(Default)]
struct ToolCallAccum {
    id: String,
    name: String,
    arguments: String,
}

#[derive(Deserialize)]
struct ChatChunk {
    id: Option<String>,
    choices: Option<Vec<ChatChoice>>,
    usage: Option<ChatUsage>,
}

#[derive(Deserialize)]
struct ChatChoice {
    delta: ChatDelta,
    finish_reason: Option<String>,
}

#[derive(Deserialize)]
struct ChatDelta {
    content: Option<String>,
    tool_calls: Option<Vec<ChatToolCallDelta>>,
}

#[derive(Deserialize)]
struct ChatToolCallDelta {
    index: Option<i64>,
    id: Option<String>,
    function: Option<ChatFunctionDelta>,
}

#[derive(Deserialize)]
struct ChatFunctionDelta {
    name: Option<String>,
    arguments: Option<String>,
}

#[derive(Deserialize)]
struct ChatUsage {
    prompt_tokens: Option<i64>,
    completion_tokens: Option<i64>,
    total_tokens: Option<i64>,
}

async fn process_deepseek_chat_stream(
    mut stream_response: StreamResponse,
    tx_event: mpsc::Sender<Result<ResponseEvent, ApiError>>,
    tool_mappings: ToolMappings,
    stream_idle_timeout: Duration,
) {
    let _ = tx_event.send(Ok(ResponseEvent::Created)).await;
    let mut buffer = String::new();
    let mut response_id = String::new();
    let mut output_text = String::new();
    let mut output_text_item_added = false;
    let mut usage: Option<ChatUsage> = None;
    let mut calls: BTreeMap<i64, ToolCallAccum> = BTreeMap::new();
    let mut saw_done = false;
    let mut saw_finish_reason = false;

    loop {
        let chunk = match timeout(stream_idle_timeout, stream_response.bytes.next()).await {
            Ok(Some(chunk)) => chunk,
            Ok(None) => break,
            Err(_) => {
                let _ = tx_event
                    .send(Err(ApiError::Stream(format!(
                        "DeepSeek chat stream idle for {} ms",
                        stream_idle_timeout.as_millis()
                    ))))
                    .await;
                return;
            }
        };
        let chunk = match chunk {
            Ok(chunk) => chunk,
            Err(err) => {
                let _ = tx_event.send(Err(ApiError::Transport(err))).await;
                return;
            }
        };
        buffer.push_str(&String::from_utf8_lossy(&chunk));
        while let Some(pos) = buffer.find('\n') {
            let line = buffer[..pos].trim().to_string();
            buffer.drain(..=pos);
            if let Some(data) = line.strip_prefix("data:").map(str::trim) {
                if data == "[DONE]" {
                    saw_done = true;
                    break;
                }
                match serde_json::from_str::<ChatChunk>(data) {
                    Ok(chat_chunk) => {
                        if response_id.is_empty()
                            && let Some(id) = chat_chunk.id
                        {
                            response_id = id;
                        }
                        if chat_chunk.usage.is_some() {
                            usage = chat_chunk.usage;
                        }
                        for choice in chat_chunk.choices.unwrap_or_default() {
                            if choice.finish_reason.is_some() {
                                saw_finish_reason = true;
                            }
                            if let Some(content) = choice.delta.content
                                && !content.is_empty()
                            {
                                if !output_text_item_added {
                                    output_text_item_added = true;
                                    let _ = tx_event
                                        .send(Ok(ResponseEvent::OutputItemAdded(
                                            ResponseItem::Message {
                                                id: None,
                                                role: "assistant".to_string(),
                                                content: vec![ContentItem::OutputText {
                                                    text: String::new(),
                                                }],
                                                phase: None,
                                            },
                                        )))
                                        .await;
                                }
                                output_text.push_str(&content);
                                let _ = tx_event
                                    .send(Ok(ResponseEvent::OutputTextDelta(content)))
                                    .await;
                            }
                            for tool_call in choice.delta.tool_calls.unwrap_or_default() {
                                let index = tool_call.index.unwrap_or(0);
                                let entry = calls.entry(index).or_default();
                                if let Some(id) = tool_call.id {
                                    entry.id = id;
                                }
                                if let Some(function) = tool_call.function {
                                    if let Some(name) = function.name {
                                        entry.name.push_str(&name);
                                    }
                                    if let Some(arguments) = function.arguments {
                                        entry.arguments.push_str(&arguments);
                                    }
                                }
                            }
                        }
                    }
                    Err(err) => {
                        let _ = tx_event
                            .send(Err(ApiError::Stream(format!(
                                "failed to parse DeepSeek chat chunk: {err}"
                            ))))
                            .await;
                        return;
                    }
                }
            }
        }
    }

    if !saw_done && !saw_finish_reason {
        let _ = tx_event
            .send(Err(ApiError::Stream(
                "DeepSeek chat stream ended before completion".to_string(),
            )))
            .await;
        return;
    }

    if !output_text.is_empty() {
        let _ = tx_event
            .send(Ok(ResponseEvent::OutputItemDone(ResponseItem::Message {
                id: None,
                role: "assistant".to_string(),
                content: vec![ContentItem::OutputText { text: output_text }],
                phase: None,
            })))
            .await;
    }
    for call in calls.into_values() {
        let call_id = if call.id.is_empty() {
            format!("call_{}", uuid_like_suffix(&call.name, &call.arguments))
        } else {
            call.id
        };
        let item = if tool_mappings.custom_names.contains(&call.name) {
            let input = serde_json::from_str::<Value>(&call.arguments)
                .ok()
                .and_then(|value| {
                    value
                        .get("input")
                        .and_then(Value::as_str)
                        .map(str::to_string)
                })
                .unwrap_or(call.arguments);
            ResponseItem::CustomToolCall {
                id: None,
                status: None,
                name: call.name,
                input,
                call_id,
            }
        } else {
            let (namespace, name) = tool_mappings
                .namespaces
                .get(&call.name)
                .map(|(namespace, name)| (Some(namespace.clone()), name.clone()))
                .unwrap_or((None, call.name));
            ResponseItem::FunctionCall {
                id: None,
                name,
                namespace,
                arguments: if call.arguments.is_empty() {
                    "{}".to_string()
                } else {
                    call.arguments
                },
                call_id,
            }
        };
        let _ = tx_event.send(Ok(ResponseEvent::OutputItemDone(item))).await;
    }
    let token_usage = usage.map(|usage| TokenUsage {
        input_tokens: usage.prompt_tokens.unwrap_or(0),
        cached_input_tokens: 0,
        output_tokens: usage.completion_tokens.unwrap_or(0),
        reasoning_output_tokens: 0,
        total_tokens: usage
            .total_tokens
            .unwrap_or(usage.prompt_tokens.unwrap_or(0) + usage.completion_tokens.unwrap_or(0)),
    });
    let _ = tx_event
        .send(Ok(ResponseEvent::Completed {
            response_id: if response_id.is_empty() {
                "deepseek_chat_completion".to_string()
            } else {
                response_id
            },
            token_usage,
            end_turn: None,
        }))
        .await;
}

fn uuid_like_suffix(name: &str, arguments: &str) -> String {
    format!("{:x}", seahash_like(name, arguments))
}

fn seahash_like(name: &str, arguments: &str) -> u64 {
    let mut hash = 1469598103934665603_u64;
    for byte in name.bytes().chain(arguments.bytes()) {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(1099511628211);
    }
    hash
}
