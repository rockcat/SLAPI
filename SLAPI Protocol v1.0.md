# Serial Line API / SLAPI v1.0
## An HTTP Proxy Protocol for calling APIs from slow and retro clients

A lightweight, line-oriented protocol for proxying HTTP/1.1 requests over a serial interface to a Wi-Fi (or Ethernet) network.

Designed for:
- Microcontrollers
- Retro computers
- Embedded systems
- Slow or unreliable serial links

This protocol is intended to be implemented by a **serial-to-network proxy** (e.g. MicroPython on a Raspberry Pi) and a **low speed or serial client**.

---

## 1. Design Goals

- Minimal parsing requirements
- Human-readable and debuggable
- HTTP-compatible where possible
- Deterministic behavior over serial
- Easy to implement on constrained systems

---

## 2. Transport Assumptions

The default transport is a serial port but implmentations may also support GPIO based connections.

- Serial connection (UART or USB CDC)
- Default serial configuration:

```
9600 baud
8 data bits
No parity
1 stop bit
```

- ASCII / UTF-8 text
- Lines terminated by `\n` (CRLF tolerated)

---

## 3. Protocol Overview

The protocol consists of two types of input:

1. **Control Commands** – single-line, uppercase commands
2. **HTTP Requests** – standard HTTP/1.1 request syntax

The proxy distinguishes commands from HTTP requests by inspecting the first token of each line.

---

## 4. Supported HTTP Methods

The proxy passes through all standard HTTP/1.1 methods:

```
GET
HEAD
POST
PUT
DELETE
OPTIONS
TRACE
CONNECT
PATCH
```

The proxy does not interpret method semantics; all methods are forwarded verbatim.

---

## 5. HTTP Request Handling

### 5.1 Request Format

Standard HTTP/1.1 request format is used:

```
METHOD path HTTP/1.1
Header: value
Header: value

[optional body]
```

### 5.2 Request Body

- Request bodies are supported **only** when `Content-Length` is present
- Chunked transfer encoding is **not supported** in v1

---

## 6. Relative URLs and DOMAIN

If the request line contains a relative path:

```
GET /api/status HTTP/1.1
```

The proxy determines the destination host using:

1. `Host:` header (if present)
2. `DOMAIN` command (fallback)

If neither is available, the request fails.

---

## 7. Control Commands

Control commands are single-line, uppercase commands sent over the serial interface.

### 7.1 DOMAIN

```
DOMAIN example.com
```

Sets the default domain used for relative URLs.

- Overrides nothing
- Overridden by explicit `Host:` header
- Supports both HTTP and HTTPS protocols

#### Examples:
```
DOMAIN example.com           # defaults to HTTP (port 80)
DOMAIN http://example.com    # explicit HTTP (port 80)
DOMAIN https://google.com    # HTTPS with SSL/TLS (port 443)
```

When HTTPS is specified, the proxy automatically:
- Uses port 443
- Wraps the connection with SSL/TLS
- Sets the server hostname for certificate validation

---

### 7.2 RESPONSE

```
RESPONSE HDRS_ON
RESPONSE HDRS_OFF
RESPONSE JSONPATH [expression]
```

Controls response processing behavior.

**Important rule:**
> The HTTP status line is always returned.

#### HDRS_ON (default)

Returns full headers with the response:

```
HTTP/1.1 200 OK
Content-Type: text/plain
Content-Length: 5

Hello
```

#### HDRS_OFF

Suppresses headers, returning only status line and body:

```
HTTP/1.1 200 OK

Hello
```

#### JSONPATH

Filters JSON responses using a JSONPath-like expression. Only applies to responses with `Content-Type: application/json`.

**Set a JSONPath filter:**
```
RESPONSE JSONPATH $.data[0].name
OK
```

**Clear the JSONPath filter:**
```
RESPONSE JSONPATH
OK
```

**Supported JSONPath syntax:**

| Pattern | Description |
|---------|-------------|
| `$` | Root object |
| `$.key` | Access object property |
| `$.key.subkey` | Nested property access |
| `$.array[0]` | Array index (zero-based) |
| `$.array[*]` | All array elements (wildcard) |
| `$.array[*].field` | Extract field from each array element |

**Example session:**

Given an API that returns:
```json
{
  "status": "ok",
  "data": [
    {"id": 1, "name": "Alice"},
    {"id": 2, "name": "Bob"}
  ]
}
```

Extract just the names:
```
RESPONSE JSONPATH $.data[*].name
OK
GET /api/users HTTP/1.1

HTTP/1.1 200 OK
Content-Type: application/json

["Alice", "Bob"]
```

Extract the first user:
```
RESPONSE JSONPATH $.data[0]
OK
GET /api/users HTTP/1.1

HTTP/1.1 200 OK
Content-Type: application/json

{"id": 1, "name": "Alice"}
```

Extract just the status:
```
RESPONSE JSONPATH $.status
OK
GET /api/users HTTP/1.1

HTTP/1.1 200 OK
Content-Type: application/json

"ok"
```

---

### 7.3 HEADERS

```
HEADERS
HEADERS name value
HEADERS CLEAR
```

Manages default headers that are automatically included with every HTTP request.

#### List default headers
```
HEADERS
content-type: application/json
authorization: Bearer token123
```

If no headers are set:
```
HEADERS
(no default headers)
```

#### Set a default header
```
HEADERS Content-Type application/json
OK
HEADERS Authorization Bearer mytoken
OK
```

Header names are normalized to lowercase. Request-specific headers override defaults.

#### Clear all default headers
```
HEADERS CLEAR
OK
```

---

### 7.5 SERIAL

```
SERIAL baud,bits,parity,stop
```

Example:
```
SERIAL 115200,8,N,1
```

Valid values:
- baud: common UART rates (e.g. 9600, 115200)
- bits: 7 or 8
- parity: N (none), E (even), O (odd)
- stop: 1 or 2

The serial interface is reinitialized immediately.

---

### 7.6 FLOW

```
FLOW OFF
FLOW X
```

Controls flow control behavior.

- `OFF` – no flow control
- `X` – XON/XOFF software flow control

XON/XOFF bytes:
- XON: `0x11`
- XOFF: `0x13`

---

## 8. Responses

### 8.1 Successful HTTP Response

The proxy returns:

1. **HTTP status line** (always)
2. Headers (optional, controlled by RESPONSE)
3. Body (if present)

---

### 8.2 SLAPI Errors

SLAPI proxy errors use the SLAPI protocol format:

```
SLAPI/1.0 400 Unknown command
```

Common error codes:

| Status | Meaning | Examples |
|--------|---------|----------|
| 400 | Bad Request | Unknown command, missing arguments, invalid syntax, DOMAIN not set |
| 500 | Internal Server Error | DNS resolution failed, connection failed, network errors |

---

## 9. Example Session

```
DOMAIN example.com
OK
RESPONSE HDRS_OFF
OK
GET / HTTP/1.1

HTTP/1.1 200 OK

<!doctype html>...
```

---

## 10. v1 Limitations

The following are **explicitly not supported** in v1:

- Chunked transfer encoding
- Persistent connections
- Streaming bodies
- CONNECT tunneling

---

## 11. Example Run

```http
SLAPI/1.0 READY
```

Set the domain to https://potterapi-fedeperin.vercel.app/
```http
DOMAIN https://potterapi-fedeperin.vercel.app/
OK
```

Get the root
```http
GET / HTTP/1.1
HTTP/1.1 200 OK
Access-Control-Allow-Credentials: true
Access-Control-Allow-Headers: X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version
Access-Control-Allow-Methods: GET,OPTIONS,PATCH,DELETE,POST,PUT
Access-Control-Allow-Origin: *
Age: 0
Cache-Control: public, max-age=0, must-revalidate
Content-Length: 291
Content-Type: application/json; charset=utf-8
Date: Wed, 14 Jan 2026 14:37:20 GMT
Etag: W/"123-wtmsXU5oGrk/Z+GFXdaUnqGfAJ8"
Server: Vercel
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Powered-By: Express
X-Vercel-Cache: MISS
X-Vercel-Id: lhr1::iad1::qnklp-1768401440806-c0eb91543eab
{"message":"This is PotterAPI, a REST API that stores images and information about Harry Potter characters, books and spells. For more info about the routes and query params, visit the github repo.","repo":"https://github.com/fedeperin/potterapi","languages":["en","es","fr","it","pt","uk"]}
```

Turn off headers and get all the books
```http
RESPONSE HDRS_OFF
OK
GET /en/books HTTP/1.1
HTTP/1.1 200 OK
[{"number":1,"title":"Harry Potter and the Sorcerer's Stone","originalTitle":"Harry Potter and the Sorcerer's Stone","releaseDate":"Jun 26, 1997","description":"On his birthday, Harry Potter discovers that he is the son of two well-known wizards, from whom he has inherited magical powers. He must attend a famous school of magic and sorcery, where he establishes a friendship with two young men who will become his companions on his adventure. During his first year at Hogwarts, he discovers that a malevolent and powerful wizard named Voldemort is in search of a philosopher's stone that prolongs the life of its owner.","pages":223,"cover":"https://raw.githubusercontent.com/fedeperin/potterapi/main/public/images/covers/1.png","index":0},{"number":2,"title":"Harry Potter and the Chamber of Secrets","originalTitle":"Harry Potter and the Chamber of Secrets","releaseDate":"Jul 2, 1998","description":"Harry Potter and the sophomores investigate a malevolent threat to their Hogwarts classmates, a menacing beast that hides within the castle.","pages":251,"cover":"https://raw.githubusercontent.com/fedeperin/potterapi/main/public/images/covers/2.png","index":1},{"number":3,"title":"Harry Potter and the Prisoner of Azkaban","originalTitle":"Harry Potter and the Prisoner of Azkaban","releaseDate":"Jul 8, 1999","description":"Harry's third year of studies at Hogwarts is threatened by Sirius Black's escape from Azkaban prison. Apparently, it is a dangerous wizard who was an accomplice of Lord Voldemort and who will try to take revenge on Harry Potter.","pages":317,"cover":"https://raw.githubusercontent.com/fedeperin/potterapi/main/public/images/covers/3.png","index":2},{"number":4,"title":"Harry Potter and the Goblet of Fire","originalTitle":"Harry Potter and the Goblet of Fire","releaseDate":"Jul 8, 2000","description":"Hogwarts prepares for the Triwizard Tournament, in which three schools of wizardry will compete. To everyone's surprise, Harry Potter is chosen to participate in the competition, in which he must fight dragons, enter the water and face his greatest fears.","pages":636,"cover":"https://raw.githubusercontent.com/fedeperin/potterapi/main/public/images/covers/4.png","index":3},{"number":5,"title":"Harry Potter and the Order of the Phoenix","originalTitle":"Harry Potter and the Order of the Phoenix","releaseDate":"Jun 21, 2003","description":"In his fifth year at Hogwarts, Harry discovers that many members of the wizarding community do not know the truth about his encounter with Lord Voldemort. Cornelius Fudge, Minister of Magic, appoints Dolores Umbridge as Defense Against the Dark Arts teacher because he believes that Professor Dumbledore plans to take over his job. But his teachings are inadequate, so Harry prepares the students to defend the school against evil.","pages":766,"cover":"https://raw.githubusercontent.com/fedeperin/potterapi/main/public/images/covers/5.png","index":4},{"number":6,"title":"Harry Potter and the Half-Blood Prince","originalTitle":"Harry Potter and the Half-Blood Prince","releaseDate":"Jul 16, 2005","description":"Harry discovers a powerful book and, while trying to discover its origins, collaborates with Dumbledore in the search for a series of magical objects that will aid in the destruction of Lord Voldemort.","pages":607,"cover":"https://raw.githubusercontent.com/fedeperin/potterapi/main/public/images/covers/6.png","index":5},{"number":7,"title":"Harry Potter and the Deathly Hallows","originalTitle":"Harry Potter and the Deathly Hallows","releaseDate":"Jul 21, 2007","description":"Harry, Ron and Hermione go on a dangerous mission to locate and destroy the secret of Voldemort's immortality and destruction - the Horcruces. Alone, without the guidance of their teachers or the protection of Professor Dumbledore, the three friends must lean on each other more than ever. But there are Dark Forces in between that threaten to tear them apart. Harry Potter is getting closer and closer to the task for which he has been preparing since the first day he set foot in Hogwarts: the last battle with Voldemort.","pages":607,"cover":"https://raw.githubusercontent.com/fedeperin/potterapi/main/public/images/covers/7.png","index":6},{"number":8,"title":"Harry Potter and the Cursed Child","originalTitle":"Harry Potter and the Cursed Child","releaseDate":"Jul 30, 2016","description":"Harry's second son entered Hogwarts, but in Slytherin. His relationship with Harry is getting worse and he became close friends with Draco's son, Scorpius Malfoy who is said to be Lord Voldemort's son.","pages":336,"cover":"https://raw.githubusercontent.com/fedeperin/potterapi/main/public/images/covers/8.png","index":7}]
```

Set a JSON filter andf get all the books again, returns justhe title fields
```http
RESPONSE JSONPATH $.[*].title
OK
GET /en/books HTTP/1.1
HTTP/1.1 200 OK
["Harry Potter and the Sorcerer's Stone", "Harry Potter and the Chamber of Secrets", "Harry Potter and the Prisoner of Azkaban", "Harry Potter and the Goblet of Fire", "Harry Potter and the Order of the Phoenix", "Harry Potter and the Half-Blood Prince", "Harry Potter and the Deathly Hallows", "Harry Potter and the Cursed Child"]
```

---

## 12. License

This protocol specification is released into the public domain.

Use it freely, modify it, and build cool things.
