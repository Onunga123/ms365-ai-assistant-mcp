import os
import re
import json
from datetime import datetime

VERBOSE = os.getenv("VERBOSE_LOGGING", "false").lower() == "true"
SILENT = os.getenv("SILENT", "false").lower() == "true"

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit.log")
REDACT_PII = os.getenv("REDACT_PII", "true").lower() == "true"

def redact(text: str) -> str:
    if not REDACT_PII:
        return text
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL]', text)
    text = re.sub(r'eyJ[a-zA-Z0-9_-]{10,}', '[TOKEN]', text)
    text = re.sub(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', '[UUID]', text)
    return text

def log_action(tool_name: str, parameters: dict):
    sanitized = json.loads(redact(json.dumps(parameters)))
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