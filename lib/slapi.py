# MicroPython imports
from machine import UART
import socket
import ssl
import sys
import json

from transport import Transport
from config import load_config

DEBUG=False

CRLF= "\r\n"
BIN_CRLF= b"\r\n"
DOUBLE_CRLF = "\r\n\r\n"
BIN_DOUBLE_CRLF = b"\r\n\r\n"
SOH = b'\x01'
STX = b'\x02'
EOT = b'\x04'
XON  = b'\x11'
XOFF = b'\x13'

paused = False
transport = load_config()


# ------------------------
# Configuration State
# ------------------------

state = {
    "domain": None,
    "send_headers": True,
    "flow": "OFF",
    "default_headers": {},
    "jsonpath": None,
    "use_ssl": None,  # None=auto-detect, True=force HTTPS, False=force HTTP
}

# ------------------------
# Utility
# ------------------------

lastchar = None
def debug_write(data):
    global lastchar
    # For debugging purposes, write to stderr
    # Convert \r to \n for proper display
    # if data == b'\r':
    #     data = b'\n'
    if (lastchar == b'\r' and data != b'\n'):
        sys.stderr.write('\n')
    sys.stderr.buffer.write(data)
    lastchar = data

def transport_write(data):
    global paused
    if state["flow"] == "X":
        while paused:
            pass
    written = 0
    length = len(data)
    while written < length:
        if DEBUG:
            debug_write(data[written:])  # Log chunks of data being written to transport
        written += transport.write(data[written:]) or 0

def readline():
    hide = False
    buf = b""
    while True:
        b = transport.read(1)
        if not b:
            continue
        if buf == b"HEADERS Authorization Bearer ":
            hide = True

        if hide and not (b in (b"\r", b"\n")):
            debug_write(b"*")  # Log hidden characters as asterisks
        else:
            debug_write(b)  # Log characters being read from transport
        
        if state["flow"] == "X":
            global paused
            if b == XOFF:
                paused = True
                continue
            if b == XON:
                paused = False
                continue
        buf += b
        if buf.endswith(b"\r\n"):
            return buf.decode().rstrip(CRLF)


def error(status, msg):
    """HTTP error response"""
    transport_write(f"HTTP/1.1 {status}{DOUBLE_CRLF}{msg}{CRLF}".encode())

def slapi_error(code, msg):
    """SLAPI protocol error response"""
    transport_write(f"SLAPI/1.0 {code} {msg}{CRLF}".encode())

def ok():
    transport_write(f"OK{CRLF}".encode())

def apply_jsonpath(data, path):
    """
    Apply a JSONPath-like expression to filter JSON data.
    Supports: $.key, $.key.subkey, $.array[0], $.array[*], $.key[*].subkey
    """
    if not path or not path.startswith("$"):
        return None

    parts = []
    current = ""
    i = 1  # Skip the leading $

    while i < len(path):
        ch = path[i]
        if ch == ".":
            if current:
                parts.append(current)
                current = ""
        elif ch == "[":
            if current:
                parts.append(current)
                current = ""
            # Find closing bracket
            j = i + 1
            while j < len(path) and path[j] != "]":
                j += 1
            bracket_content = path[i+1:j]
            parts.append(f"[{bracket_content}]")
            i = j
        else:
            current += ch
        i += 1

    if current:
        parts.append(current)

    result = data
    for part in parts:
        if part.startswith("[") and part.endswith("]"):
            index = part[1:-1]
            if index == "*":
                # Wildcard - keep as list for further processing
                if isinstance(result, list):
                    # Already a list, continue
                    pass
                elif isinstance(result, dict):
                    result = list(result.values())
                else:
                    return None
            else:
                # Numeric index
                try:
                    if isinstance(result, list):
                        result = result[int(index)]
                    else:
                        return None
                except (IndexError, ValueError):
                    return None
        else:
            if isinstance(result, list):
                # Apply to each element in list
                new_result = []
                for item in result:
                    if isinstance(item, dict) and part in item:
                        new_result.append(item[part])
                result = new_result if new_result else None
            elif isinstance(result, dict):
                result = result.get(part)
            else:
                return None

        if result is None:
            return None

    return result
# ------------------------
# Command Handling
# ------------------------

def handle_command(line):
    parts = line.split(" ", 1)
    cmd = parts[0]

    if cmd == "DOMAIN":
        if len(parts) < 2:
            slapi_error("400", "DOMAIN requires an argument")
            return
        state["domain"] = parts[1].strip()
        ok()

    elif cmd == "RESPONSE":
        if len(parts) < 2:
            slapi_error("400", "RESPONSE requires an argument")
            return
        args = parts[1].split(" ", 1)
        subcmd = args[0].strip()
        if subcmd == "HDRS_ON":
            state["send_headers"] = True
            ok()
        elif subcmd == "HDRS_OFF":
            state["send_headers"] = False
            ok()
        elif subcmd == "JSONPATH":
            if len(args) == 1:
                # Clear the jsonpath
                state["jsonpath"] = None
            else:
                state["jsonpath"] = args[1].strip()
            ok()
        else:
            slapi_error("400", "Unknown RESPONSE subcommand")

    elif cmd == "FLOW":
        state["flow"] = parts[1].strip()
        ok()

    elif cmd == "SERIAL":
        cfg = parts[1].split(",")
        baud = int(cfg[0])
        bits = int(cfg[1])
        parity = cfg[2]
        stop = int(cfg[3])

        p = None
        if parity == "E":
            p = 0
        elif parity == "O":
            p = 1

        transport.init(baudrate=baud, bits=bits, parity=p, stop=stop)
        ok()

    elif cmd == "HEADERS":
        if len(parts) == 1:
            # List all headers
            if state["default_headers"]:
                for k, v in state["default_headers"].items():
                    transport_write(f"{k}: {v}{CRLF}".encode())
            else:
                transport_write(f"(no default headers){CRLF}".encode())
        else:
            args = parts[1].split(" ", 1)
            if args[0] == "CLEAR":
                state["default_headers"].clear()
                ok()
            elif len(args) >= 2:
                header_name = args[0].strip()
                header_value = args[1].strip()
                state["default_headers"][header_name.lower()] = header_value
                ok()
            else:
                slapi_error("400", "HEADERS requires header name and value")

    elif cmd == "HTTPS":
        state["use_ssl"] = True
        ok()

    elif cmd == "HTTP":
        state["use_ssl"] = False
        ok()

    else:
        slapi_error("400", "Unknown command")


# ------------------------
# HTTP Handling
# ------------------------

def read_http_request(first_line, method):
    headers = {}
    body = b""

    debug_write(b"\n--- Reading HTTP Request ---\n")

    # Read headers until blank line
    while True:
        line = readline()
        if line == "":
            # Blank line separates headers from body
            break
        
        # Parse header
        if ":" not in line:
            raise ValueError(f"Invalid header line (missing colon): {line}")
        
        k, v = line.split(":", 1)
        header_name = k.strip()
        
        # Validate header name (should not start with special chars like {, [, etc.)
        if not header_name or header_name[0] in '{[<"':
            raise ValueError(f"Invalid header name: {header_name}")
        
        headers[header_name.lower()] = v.strip()

    debug_write(b"--- Headers Read ---\r\n")

    body_lines = []
    if method in ("POST", "PUT", "PATCH"):
        # Read body until blank line
        while True:
            line = readline()
            if line == "":
                # Blank line ends body
                break
            body_lines.append(line)
        
        if body_lines:
            body = (CRLF.join(body_lines) + DOUBLE_CRLF)
    else:
        debug_write(b"--- No Body Expected for Method " + method.encode() + b" ---\r\n")

    debug_write(b"--- HTTP Request Read ---\r\n")
    return headers, body

def recv_until(sock, marker):
    data = b""
    while marker not in data:
        data += sock.recv(4096)
    return data

def send_http(method, path, headers, body, redirected_host=None, _redirects=0, _max_redirects=5):
    # Merge default headers (request headers override defaults)
    merged_headers = state["default_headers"].copy()
    merged_headers.update(headers)
    req_headers = merged_headers
    
    host = redirected_host or headers.get("host")

    if not host:
        if not state["domain"]:
            slapi_error("400", "DOMAIN not set and no Host header provided")
            return
        host = state["domain"]
        req_headers["host"] = host

    # Detect protocol and port
    use_ssl = False
    port = 80
    
    if host.startswith("https://"):
        use_ssl = True
        port = 443
        host = host[8:]  # Remove https://
    elif host.startswith("http://"):
        host = host[7:]  # Remove http://
    
    # Override with state setting if specified
    if state["use_ssl"] is not None:
        use_ssl = state["use_ssl"]
        port = 443 if use_ssl else 80
    
    # Remove trailing slash if present
    if host.endswith("/"):
        host = host[:-1]
    
    # Update the host header with port for non-default ports or when HTTPS
    if use_ssl:
        req_headers["host"] = f"{host}:443"
    elif port != 80:
        req_headers["host"] = f"{host}:{port}"
    else:
        req_headers["host"] = host

    try:
        addr = socket.getaddrinfo(host, port)[0][-1]
    except OSError as e:
        slapi_error("500", f"DNS resolution failed for {host}: {e}")
        return
    
    s = socket.socket()
    
    try:
        s.connect(addr)
    except OSError as e:
        slapi_error("500", f"Connection failed to {host}:{port}: {e}")
        s.close()
        return
    
    # Wrap with SSL if HTTPS
    if use_ssl:
        s = ssl.wrap_socket(s, server_hostname=host)

    # Add Content-Length header if body is present
    if body:
        req_headers["content-length"] = str(len(body))

    req = f"{method} {path} HTTP/1.1{CRLF}"
    for k, v in req_headers.items():
        req += f"{k}: {v}{CRLF}"
    req += CRLF

    debug_write(b"--- Sending Request ---\r\n")
    # debug_write(req.encode())             don't show potentially sensitive headers in debug log
    s.send(req.encode())
    if body:
        debug_write(b"--- Sending Body ---\r\n")
        debug_write(body)
        s.send(body)

    # Read headers
    first_headers = recv_until(s, BIN_CRLF)
    status_line, raw_headers = first_headers.split(BIN_CRLF, 1)
    debug_write(b"--- Status Received ---\r\n")
    debug_write(status_line + b"\r\n")
    transport_write(status_line + BIN_CRLF)

    debug_write(b"--- Receiving Headers ---\r\n")
    if BIN_DOUBLE_CRLF not in raw_headers:
        raw_headers += recv_until(s, BIN_DOUBLE_CRLF)

    resp_headers, body = raw_headers.split(BIN_DOUBLE_CRLF, 1)
    bodyLen = len(body)

    debug_write(resp_headers + b"\r\n")
    
    debug_write(b"--- Headers Received ---\r\n")
    remainingLength = 0
    content_type = None
    location = None
    status_code = None

    # Parse Headers for Content-Length and Content-Type, Location, and Status Code
    try:
        status_code = int(status_line.split(b" ")[1])
    except Exception:
        status_code = None

    debug_write(b"--- Status Code: " + (str(status_code).encode() if status_code else b"Unknown") + b" ---\r\n")

    for line in resp_headers.split(BIN_CRLF):
        line_lower = line.lower()
        if line_lower.startswith(b"content-length"):
            remainingLength = int(line.split(b":")[1].strip()) - bodyLen
        elif line_lower.startswith(b"content-type"):
            content_type = line.split(b":")[1].strip().decode()
        elif line_lower.startswith(b"location"):
            location = line.split(b":", 1)[1].strip().decode()

    # Follow redirects (3xx + Location)
    if status_code in (301, 302, 303, 307, 308) and location:
        if _redirects >= _max_redirects:
            slapi_error("500", "Too many redirects")
            return
        
        # Per RFC, switch to GET on 303
        new_method = "GET" if status_code == 303 else method
        debug_write(f"\r\n--- Redirecting to {location} (status {status_code}) ---\r\n".encode())
        return send_http(new_method, path, req_headers, body if new_method != "GET" else b"", location, _redirects + 1, _max_redirects)

    if state["send_headers"]:
        debug_write(b"--- Sending Headers ---\r\n")
        transport_write(SOH)
        transport_write(resp_headers + BIN_CRLF)
        debug_write(b"--- Headers Sent ---\r\n")
    else:
        debug_write(b"--- Skipping Headers ---\r\n")

    # Collect remaining body
    while remainingLength > 0:
        recvLength = min(4096, remainingLength)
        chunk = s.recv(recvLength)
        remainingLength -= len(chunk)
        body += chunk
    s.close()


    # Apply JSONPath filter if set and response is JSON
    if state["jsonpath"] and content_type and "application/json" in content_type:
        try:
            json_data = json.loads(body.decode())
            filtered = apply_jsonpath(json_data, state["jsonpath"])
            body = json.dumps(filtered).encode('ascii',)
            debug_write(b"--- JSONPath Applied ---\r\n")
            debug_write(body + b"\n")
        except Exception as e:
            debug_write(f"\r\n--- JSONPath Error: {e} ---\r\n".encode())
            body = b""  # Clear body on JSON parsing error

    # send body
    debug_write(b"--- Sending Body ---\r\n")
    transport_write(STX)
    debug_write(b"--- STX Sent ---\r\n")
    transport_write(body)
    transport_write(BIN_DOUBLE_CRLF)
    debug_write(b"--- Body Sent ---\r\n")
    transport_write(EOT)
    debug_write(b"--- EOT Sent ---\r\n")


# ------------------------
# Main Loop
# ------------------------

def start_slapi():

    global transport

    print("SLAPI started", file=sys.stderr)
    print(transport)

    # Send start header to show we are here:
    transport_write(b"SLAPI/1.0 READY\r\n")

    while True:
        transport.set_read_mode()
        line = readline()
        if not line:
            continue

        method = line.split(" ", 1)[0]

        if method in (
            "GET","POST","PUT","DELETE","HEAD",
            "OPTIONS","TRACE","CONNECT","PATCH"
        ):
            try:
                method, path, _ = line.split(" ", 2)
                headers, body = read_http_request(line, method)
                transport.set_write_mode()                  # prevent spurious gpio valid lines
                send_http(method, path, headers, body)
            except ValueError as e:
                # Bad request format
                slapi_error("400", str(e))
            except Exception as e:
                sys.print_exception(e)
                slapi_error("500", str(e))
        else:
            handle_command(line)
