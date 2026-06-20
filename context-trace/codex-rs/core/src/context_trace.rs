use chrono::Utc;
use serde::Serialize;
use serde_json::Value;
use serde_json::json;
use std::fs::OpenOptions;
use std::io::Write;
use std::panic::Location;
use std::path::PathBuf;
use std::sync::Mutex;
use std::sync::OnceLock;

const TRACE_DIR_ENV: &str = "CODEX_CONTEXT_TRACE_DIR";

static TRACE_DIR: OnceLock<Option<PathBuf>> = OnceLock::new();
static TRACE_WRITE_LOCK: Mutex<()> = Mutex::new(());

fn trace_dir() -> Option<&'static PathBuf> {
    TRACE_DIR
        .get_or_init(|| std::env::var_os(TRACE_DIR_ENV).map(PathBuf::from))
        .as_ref()
}

pub(crate) fn to_value<T: Serialize + ?Sized>(value: &T) -> Value {
    serde_json::to_value(value).unwrap_or_else(|err| {
        json!({
            "serialization_error": err.to_string(),
        })
    })
}

pub(crate) fn emit(
    thread_id: impl ToString,
    turn_id: Option<&str>,
    stage: &str,
    action: &str,
    source: Option<&'static Location<'static>>,
    payload: Value,
) {
    let Some(dir) = trace_dir() else {
        return;
    };

    let thread_id = thread_id.to_string();
    let safe_thread_id: String = thread_id
        .chars()
        .map(|character| {
            if character.is_ascii_alphanumeric() || matches!(character, '-' | '_') {
                character
            } else {
                '_'
            }
        })
        .collect();
    let event = json!({
        "timestamp": Utc::now().to_rfc3339(),
        "thread_id": thread_id,
        "turn_id": turn_id,
        "stage": stage,
        "action": action,
        "source": source.map(|location| json!({
            "file": location.file(),
            "line": location.line(),
            "column": location.column(),
        })),
        "payload": payload,
    });

    let Ok(_guard) = TRACE_WRITE_LOCK.lock() else {
        return;
    };
    if std::fs::create_dir_all(dir).is_err() {
        return;
    }
    let path = dir.join(format!("{safe_thread_id}.jsonl"));
    let Ok(mut file) = OpenOptions::new().create(true).append(true).open(path) else {
        return;
    };
    if serde_json::to_writer(&mut file, &event).is_ok() {
        let _ = file.write_all(b"\n");
    }
}
