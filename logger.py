import os
import re
import json
from datetime import datetime

VERBOSE = os.getenv("VERBOSE_LOGGING", "false").lower() == "true"
SILENT = os.getenv("SILENT", "false").lower() == "true"

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit.log")
REDACT_PII = os.getenv("REDACT_PII", "true").lower() == "true"

def redact(text: str) -> str:
    """Remove sensitive values from text regardless of optional log settings."""
    text = str(text)
    text = re.sub(r'(?is)(response body|response text|error body|exception details?)\s*[:=]\s*.*?(?=(\n|$))', r'\1=[REDACTED]', text)
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    text = re.sub(r'eyJ[a-zA-Z0-9_-]{10,}', '[TOKEN]', text)
    text = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '[UUID]', text)
    text = re.sub(r'(?i)(authorization|client_secret|password|access_token|refresh_token)\s*[:=]\s*[^,\s}]+', r'\1=[REDACTED]', text)
    text = re.sub(r'(?i)(tenant_id|client_id)\s*[:=]\s*[^,\s}]+', r'\1=[REDACTED]', text)
    text = re.sub(r'(?i)([?&](?:access_token|client_secret|code|token|sig|signature)=)[^&\s]+', r'\1[REDACTED]', text)
    return text

def log_action(tool_name: str, parameters: dict):
    sanitized = json.loads(redact(json.dumps(parameters)))
    if "endpoint" in sanitized:
        sanitized["endpoint"] = redact(sanitized["endpoint"].split("?", 1)[0])
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "tool": tool_name,
        "parameters": sanitized
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    if VERBOSE and not SILENT:
        print(f"[{entry['timestamp']}] {tool_name} → {sanitized}")
        
def read_logs(last_n: int = 50):
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    return [json.loads(line) for line in lines[-last_n:]]