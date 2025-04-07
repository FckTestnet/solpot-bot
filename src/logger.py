from datetime import datetime
from .utils import pth, htm, hju, mrh, bru, kng

last_log_message = None

LOG_WIDTH = 8

def _get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _print(log_type, color, message, flush=False, end='\n'):
    global last_log_message
    timestamp = _get_timestamp()
    padded_type = f"[{log_type.upper():<{LOG_WIDTH}}]"
    formatted_msg = f"{color}[{timestamp}] {padded_type} {message}"

    if message != last_log_message:
        print(formatted_msg, flush=flush, end=end)
        last_log_message = message

def info(message, **kwargs):
    _print("INFO", htm, message, **kwargs)

def success(message, **kwargs):
    _print("SUCCESS", hju, message, **kwargs)

def warning(message, **kwargs):
    _print("WARNING", kng, message, **kwargs)

def error(message, **kwargs):
    _print("ERROR", mrh, message, **kwargs)
    _log_to_file("ERROR", message)

def step(message, **kwargs):
    _print("STEP", bru, message, **kwargs)

def line():
    print(pth + "~" * 60)

def _log_to_file(level, message):
    with open("report.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"{_get_timestamp()} - {level.upper()} - {message}\n")
