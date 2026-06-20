use std::sync::Arc;
use std::sync::Mutex;
use std::time::Duration;

use anyhow::Context;
use anyhow::Result;
use async_trait::async_trait;
use bytes::Bytes;
use codex_api::AuthProvider;
use codex_api::DeepSeekChatClient;
use codex_api::Provider;
use codex_api::ResponseEvent;
use codex_api::ResponsesApiRequest;
use codex_api::ResponsesOptions;
use codex_client::HttpTransport;
use codex_client::Request;
use codex_client::Response;
use codex_client::StreamResponse;
use codex_client::TransportError;
use codex_protocol::models::ContentItem;
use codex_protocol::models::ResponseItem;
use futures::StreamExt;
use http::HeaderMap;
use http::StatusCode;
use pretty_assertions::assert_eq;

#[derive(Clone)]
enum FixtureChunk {
    Bytes(Bytes),
    NetworkError(&'static str),
}

impl FixtureChunk {
    fn into_result(self) -> Result<Bytes, TransportError> {
        match self {
            Self::Bytes(bytes) => Ok(bytes),
            Self::NetworkError(message) => Err(TransportError::Network(message.to_string())),
        }
    }
}

#[derive(Clone)]
struct FixtureTransport {
    request: Arc<Mutex<Option<Request>>>,
    chunks: Vec<FixtureChunk>,
}

#[derive(Clone)]
struct ErrorTransport {
    error: FixtureHttpError,
}

#[derive(Clone)]
struct HangingTransport;

#[derive(Clone)]
struct FixtureHttpError {
    status: StatusCode,
    body: &'static str,
}

#[async_trait]
impl HttpTransport for ErrorTransport {
    async fn execute(&self, _req: Request) -> Result<Response, TransportError> {
        Err(TransportError::Build("execute should not run".to_string()))
    }

    async fn stream(&self, _req: Request) -> Result<StreamResponse, TransportError> {
        Err(TransportError::Http {
            status: self.error.status,
            url: Some("https://api.deepseek.com/v1/chat/completions".to_string()),
            headers: None,
            body: Some(self.error.body.to_string()),
        })
    }
}

#[async_trait]
impl HttpTransport for HangingTransport {
    async fn execute(&self, _req: Request) -> Result<Response, TransportError> {
        Err(TransportError::Build("execute should not run".to_string()))
    }

    async fn stream(&self, _req: Request) -> Result<StreamResponse, TransportError> {
        Ok(StreamResponse {
            status: StatusCode::OK,
            headers: HeaderMap::new(),
            bytes: Box::pin(futures::stream::pending()),
        })
    }
}

#[async_trait]
impl HttpTransport for FixtureTransport {
    async fn execute(&self, _req: Request) -> Result<Response, TransportError> {
        Err(TransportError::Build("execute should not run".to_string()))
    }

    async fn stream(&self, req: Request) -> Result<StreamResponse, TransportError> {
        *self
            .request
            .lock()
            .map_err(|_| TransportError::Build("request mutex poisoned".to_string()))? = Some(req);
        Ok(StreamResponse {
            status: StatusCode::OK,
            headers: HeaderMap::new(),
            bytes: Box::pin(futures::stream::iter(
                self.chunks
                    .clone()
                    .into_iter()
                    .map(FixtureChunk::into_result),
            )),
        })
    }
}

#[derive(Clone, Default)]
struct NoAuth;

impl AuthProvider for NoAuth {
    fn add_auth_headers(&self, _headers: &mut HeaderMap) {}
}

fn provider() -> Provider {
    Provider {
        name: "DeepSeek".to_string(),
        base_url: "https://api.deepseek.com/v1".to_string(),
        query_params: None,
        headers: HeaderMap::new(),
        retry: codex_api::RetryConfig {
            max_attempts: 1,
            base_delay: Duration::from_millis(1),
            retry_429: false,
            retry_5xx: false,
            retry_transport: false,
        },
        stream_idle_timeout: Duration::from_secs(1),
    }
}

fn request() -> ResponsesApiRequest {
    ResponsesApiRequest {
        model: "deepseek-chat".to_string(),
        instructions: "Be precise".to_string(),
        input: vec![ResponseItem::Message {
            id: None,
            role: "user".to_string(),
            content: vec![ContentItem::InputText {
                text: "hello".to_string(),
            }],
            phase: None,
        }],
        tools: vec![serde_json::json!({
            "type": "function",
            "name": "read_file",
            "description": "Read a file",
            "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}
        })],
        tool_choice: "auto".to_string(),
        parallel_tool_calls: true,
        reasoning: None,
        store: false,
        stream: true,
        include: Vec::new(),
        service_tier: None,
        prompt_cache_key: None,
        text: None,
        client_metadata: None,
    }
}

fn sse(lines: &[&str]) -> Bytes {
    Bytes::from(
        lines
            .iter()
            .map(|line| format!("data: {line}\n\n"))
            .collect::<String>(),
    )
}

#[tokio::test]
async fn translates_responses_request_and_streams_text() -> Result<()> {
    let captured = Arc::new(Mutex::new(None));
    let transport = FixtureTransport {
        request: captured.clone(),
        chunks: vec![FixtureChunk::Bytes(sse(&[
            r#"{"id":"chat_1","choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}"#,
            r#"{"id":"chat_1","choices":[{"delta":{"content":" world"},"finish_reason":"stop"}],"usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5}}"#,
            "[DONE]",
        ]))],
    };
    let client = DeepSeekChatClient::new(transport, provider(), Arc::new(NoAuth));

    let mut options = ResponsesOptions::default();
    options
        .extra_headers
        .insert("x-test-trace", "trace-value".parse()?);
    let mut stream = client.stream_request(request(), options).await?;
    let mut events = Vec::new();
    while let Some(event) = stream.next().await {
        events.push(event?);
    }

    let sent = captured
        .lock()
        .map_err(|_| anyhow::anyhow!("request mutex poisoned"))?
        .clone()
        .context("request should be captured")?;
    assert_eq!(sent.url, "https://api.deepseek.com/v1/chat/completions");
    let body = sent
        .body
        .as_ref()
        .context("request should have a body")?
        .json()
        .context("request body should be JSON")?;
    assert_eq!(
        body["messages"][0],
        serde_json::json!({"role":"system","content":"Be precise"})
    );
    assert_eq!(
        body["messages"][1],
        serde_json::json!({"role":"user","content":"hello"})
    );
    assert_eq!(body["tools"][0]["function"]["name"], "read_file");
    assert_eq!(body["stream_options"]["include_usage"], true);
    assert_eq!(
        sent.headers
            .get("x-test-trace")
            .and_then(|value| value.to_str().ok()),
        Some("trace-value")
    );
    assert!(
        events
            .iter()
            .any(|event| matches!(event, ResponseEvent::OutputTextDelta(text) if text == "Hello"))
    );
    assert!(events.iter().any(|event| matches!(event, ResponseEvent::OutputItemDone(ResponseItem::Message { content, .. }) if content == &vec![ContentItem::OutputText { text: "Hello world".to_string() }])));
    assert!(events.iter().any(|event| matches!(event, ResponseEvent::Completed { response_id, .. } if response_id == "chat_1")));
    Ok(())
}

#[tokio::test]
async fn streams_fragmented_tool_call_as_response_item() -> Result<()> {
    let transport = FixtureTransport {
        request: Arc::new(Mutex::new(None)),
        chunks: vec![FixtureChunk::Bytes(sse(&[
            r#"{"id":"chat_2","choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_1","function":{"name":"read_","arguments":"{\"pa"}}]},"finish_reason":null}]}"#,
            r#"{"id":"chat_2","choices":[{"delta":{"tool_calls":[{"index":0,"function":{"name":"file","arguments":"th\":\"a.txt\"}"}}]},"finish_reason":"tool_calls"}]}"#,
            "[DONE]",
        ]))],
    };
    let client = DeepSeekChatClient::new(transport, provider(), Arc::new(NoAuth));
    let mut stream = client
        .stream_request(request(), ResponsesOptions::default())
        .await?;

    let mut call = None;
    while let Some(event) = stream.next().await {
        if let ResponseEvent::OutputItemDone(item @ ResponseItem::FunctionCall { .. }) = event? {
            call = Some(item);
        }
    }
    assert_eq!(
        call,
        Some(ResponseItem::FunctionCall {
            id: None,
            name: "read_file".to_string(),
            namespace: None,
            arguments: r#"{"path":"a.txt"}"#.to_string(),
            call_id: "call_1".to_string(),
        })
    );
    Ok(())
}

#[tokio::test]
async fn translates_freeform_tools_and_restores_custom_tool_calls() -> Result<()> {
    let captured = Arc::new(Mutex::new(None));
    let transport = FixtureTransport {
        request: captured.clone(),
        chunks: vec![FixtureChunk::Bytes(sse(&[
            r#"{"id":"chat_custom","choices":[{"delta":{"tool_calls":[{"index":0,"id":"call_custom","function":{"name":"shell","arguments":"{\"input\":\"echo ok\"}"}}]},"finish_reason":"tool_calls"}]}"#,
            "[DONE]",
        ]))],
    };
    let client = DeepSeekChatClient::new(transport, provider(), Arc::new(NoAuth));
    let mut req = request();
    req.tools = vec![serde_json::json!({
        "type": "custom",
        "name": "shell",
        "description": "Run shell input",
        "format": {"type":"grammar","syntax":"lark","definition":"start: /.+/"}
    })];
    let mut stream = client
        .stream_request(req, ResponsesOptions::default())
        .await?;

    let mut call = None;
    while let Some(event) = stream.next().await {
        if let ResponseEvent::OutputItemDone(item @ ResponseItem::CustomToolCall { .. }) = event? {
            call = Some(item);
        }
    }
    let sent = captured
        .lock()
        .map_err(|_| anyhow::anyhow!("request mutex poisoned"))?
        .clone()
        .context("request should be captured")?;
    let body = sent
        .body
        .as_ref()
        .context("request should have a body")?
        .json()
        .context("request body should be JSON")?;
    assert_eq!(
        body["tools"][0]["function"]["parameters"]["required"][0],
        "input"
    );
    assert_eq!(
        call,
        Some(ResponseItem::CustomToolCall {
            id: None,
            status: None,
            call_id: "call_custom".to_string(),
            name: "shell".to_string(),
            input: "echo ok".to_string(),
        })
    );
    Ok(())
}

#[tokio::test]
async fn reports_clean_eof_without_done_or_finish_reason_as_interruption() -> Result<()> {
    let transport = FixtureTransport {
        request: Arc::new(Mutex::new(None)),
        chunks: vec![FixtureChunk::Bytes(sse(&[
            r#"{"id":"chat_eof","choices":[{"delta":{"content":"partial"},"finish_reason":null}]}"#,
        ]))],
    };
    let client = DeepSeekChatClient::new(transport, provider(), Arc::new(NoAuth));
    let mut stream = client
        .stream_request(request(), ResponsesOptions::default())
        .await?;

    let mut saw_error = false;
    while let Some(event) = stream.next().await {
        if event.is_err() {
            saw_error = true;
        }
    }
    assert!(
        saw_error,
        "premature clean EOF must not be reported as success"
    );
    Ok(())
}

#[tokio::test]
async fn propagates_stream_interruption_after_partial_text() -> Result<()> {
    let transport = FixtureTransport {
        request: Arc::new(Mutex::new(None)),
        chunks: vec![
            FixtureChunk::Bytes(sse(&[
                r#"{"id":"chat_3","choices":[{"delta":{"content":"partial"},"finish_reason":null}]}"#,
            ])),
            FixtureChunk::NetworkError("connection reset"),
        ],
    };
    let client = DeepSeekChatClient::new(transport, provider(), Arc::new(NoAuth));
    let mut stream = client
        .stream_request(request(), ResponsesOptions::default())
        .await?;

    assert!(matches!(
        stream.next().await,
        Some(Ok(ResponseEvent::Created))
    ));
    assert!(matches!(
        stream.next().await,
        Some(Ok(ResponseEvent::OutputItemAdded(
            ResponseItem::Message { .. }
        )))
    ));
    assert!(
        matches!(stream.next().await, Some(Ok(ResponseEvent::OutputTextDelta(text))) if text == "partial")
    );
    assert!(matches!(stream.next().await, Some(Err(_))));
    Ok(())
}

#[tokio::test]
async fn reports_stream_idle_timeout() -> Result<()> {
    let mut provider = provider();
    provider.stream_idle_timeout = Duration::from_millis(10);
    let client = DeepSeekChatClient::new(HangingTransport, provider, Arc::new(NoAuth));
    let mut stream = client
        .stream_request(request(), ResponsesOptions::default())
        .await?;

    assert!(matches!(
        stream.next().await,
        Some(Ok(ResponseEvent::Created))
    ));
    let error = match stream.next().await {
        Some(Err(error)) => error,
        Some(Ok(event)) => anyhow::bail!("expected idle timeout error, got {event:?}"),
        None => anyhow::bail!("expected idle timeout event"),
    };
    assert!(error.to_string().contains("idle for 10 ms"));
    Ok(())
}

#[tokio::test]
async fn propagates_deepseek_invalid_request_errors() {
    let client = DeepSeekChatClient::new(
        ErrorTransport {
            error: FixtureHttpError {
                status: StatusCode::BAD_REQUEST,
                body: r#"{"error":{"message":"Invalid tool schema"}}"#,
            },
        },
        provider(),
        Arc::new(NoAuth),
    );

    let err = match client
        .stream_request(request(), ResponsesOptions::default())
        .await
    {
        Ok(_) => panic!("invalid request should fail"),
        Err(err) => err,
    };
    assert!(err.to_string().contains("400"));
    assert!(err.to_string().contains("Invalid tool schema"));
}

#[tokio::test]
async fn propagates_deepseek_rate_limit_errors() {
    let client = DeepSeekChatClient::new(
        ErrorTransport {
            error: FixtureHttpError {
                status: StatusCode::TOO_MANY_REQUESTS,
                body: r#"{"error":{"message":"Rate limit reached"}}"#,
            },
        },
        provider(),
        Arc::new(NoAuth),
    );

    let err = match client
        .stream_request(request(), ResponsesOptions::default())
        .await
    {
        Ok(_) => panic!("rate limit should fail"),
        Err(err) => err,
    };
    assert!(err.to_string().contains("429"));
    assert!(err.to_string().contains("Rate limit reached"));
}
