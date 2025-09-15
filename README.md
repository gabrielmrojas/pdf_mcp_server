# FastMCP PDF Processing Server

An MCP server built with FastMCP (STDIO transport) offering PDF utilities: text extraction, metadata, merge/split/rotate, and PDF↔image conversion.

## Quick Start (Windows PowerShell)
```
python -m venv .venv
\.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m fastmcp_pdf_server
```

If installed as a package, you may also run:
```
fastmcp-pdf-server
```

## MCP Integration
- Transport: STDIO. Do not print to stdout/stderr; logs go to file.
- Server name/version: from config (`server_name`, `server_version`).
- Tools are registered using `@app.tool()` and return structured outputs with a `meta` block containing `operation_id` and `execution_ms`.

### Claude Desktop config example
Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
     "pdf-processor-server": {
      "command": "D:\\Github Projects\\mcp_pdf_server\\.venv\\Scripts\\python.exe",
      "args": [
        "-m",
        "fastmcp_pdf_server"
      ],
      "env": {
        "MAX_FILE_SIZE_MB": "50",
        "TEMP_DIR": "D:\\Github Projects\\mcp_pdf_server\\temp_files",
        "LOG_LEVEL": "DEBUG",
        "LOG_FILE_PATH": "D:\\Github Projects\\mcp_pdf_server\\logs\\fastmcp_pdf_server.log",
        "SERVER_NAME": "pdf-processor-server",
        "SERVER_VERSION": "1.0.0",
        "PATH": "%PATH%;C:\\poppler-25.07.0\\Library\\bin"
      }
    }
}
```

Note: If you update dependencies (e.g., we added `requests` for URL uploads), reinstall with:
```
pip install -r requirements.txt
```

### Programmatic usage (Python)
```python
import asyncio
from fastmcp import Client

async def main():
    client = Client(command="python", args=["-m", "fastmcp_pdf_server"])
    await client.start()
    try:
        info = await client.call_tool("server_info")
        print(info)
    finally:
        await client.close()

asyncio.run(main())
```

## Exposed Tools (API)
All tools return structured data; many responses include `meta.operation_id` and `meta.execution_ms`.
Some tools return lists (arrays). These are marked with FastMCP's `x-fastmcp-wrap-result`, so clients receive `{ "result": [...] }` at the RPC layer.

# MCP Tools Reference

Each tool lists: purpose, inputs, outputs, behavior, examples, and notes about errors and usage.

---

**Utilities / Server**

- `server_info()`
  - Purpose: Return basic server info and configuration snapshot (non-secret).
  - Inputs: None
  - Returns: dict with keys:
    - `name` (str): server name from settings
    - `version` (str): server version from settings
    - `max_file_size_mb` (int): maximum configured file size in megabytes
    - `temp_dir` (str): absolute path to temporary files directory
    - `log_file` (str): absolute path to the log file
    - `meta` (dict): operation metadata: `operation_id` (hex), `execution_ms` (int)
  - Errors: none expected; if configuration missing, underlying access may raise exceptions.
  - Example:
    - Call: `{ "name": "server_info" }`
    - Response: `{ "name": "mcp-pdf", "version": "1.0.0", "meta": { ... } }`

- `list_temp_resources(content_type: Optional[str] = None, max_items: Optional[int] = 100) -> list[dict]`
  - Purpose: List files currently in the server temp directory with optional filtering by content type.
  - Inputs:
    - `content_type` (optional str): MIME filter; supported examples: `application/pdf`, `image/png`, `image/jpeg`.
    - `max_items` (optional int): maximum number of entries to return (default 100). If set to null or 0, defaults to 100.
  - Returns: list of resource dicts (each):
    - `path` (str): absolute path to the temp file
    - `size` (int): size in bytes
    - `created` (str): creation timestamp (ISO or file-manager-specific format)
    - `content_type` (str): MIME type of resource
    - `filename` (str): filename only
    - `extension` (str): lowercased file extension (e.g. `.pdf`)
    - `directory` (str): parent directory of the file
  - Behavior: Cleans up expired temp files before listing. Result list is sliced to `max_items`.
  - Errors: Raises `ValueError` if internal listing fails.
  - Example call:
    - `{ "name": "list_temp_resources", "arguments": { "content_type": "application/pdf" } }`

- `get_pdf_info(file_path: str) -> dict`
  - Purpose: Read a PDF headers and basic info without extracting pages/text.
  - Inputs:
    - `file_path` (str): path to an existing file on disk (absolute or relative). Must be accessible to the server.
  - Returns: dict:
    - `pages` (int): number of pages
    - `size` (int): file size in bytes
    - `version` (str|None): PDF header/version info (if available)
    - `encrypted` (bool): whether the PDF is encrypted
    - `meta` (dict): `operation_id`, `execution_ms`
  - Errors:
    - Raises `ValueError` if file not found.
    - May raise other errors if the file is not a PDF or is corrupted.

- `get_resource_base64(file_path: str) -> dict`
  - Purpose: Return base64-encoded contents of a file inside the server temp directory.
  - Inputs:
    - `file_path` (str): path; must be inside the configured temp directory. The function enforces this.
  - Returns: dict:
    - `path` (str): resolved path inside temp
    - `base64` (str): Base64-encoded content of the file
    - `meta` (dict): operation metadata
  - Errors:
    - Raises `ValueError` if the path is outside temp or file missing.
  - Notes: Use this to fetch content for download via MCP where direct file transfers aren't available.

---

**Uploads**

- `upload_file(file: Any, filename: Optional[str] = None) -> dict`
  - Purpose: Persist an uploaded file into the server temp directory.
  - Inputs:
    - `file` (Any): Accepts:
      - a full path string to a local file
      - a short filename that refers to a file already stored in temp
      - bytes or file-like object
      - dicts containing `base64` and `filename` (will be saved to temp)
    - `filename` (Optional[str]): optional filename hint used when saving raw bytes.
  - Returns: dict:
    - `path` (str): absolute path to the saved file
    - `filename` (str): saved filename
    - `directory` (str): directory containing the file
    - `meta` (dict): operation metadata
  - Errors:
    - Raises `ValueError` with a descriptive message on failure (network, decoding, IO).
  - Example:
    - To upload base64: call `upload_file` with `file` = `{ "base64": "<...>", "filename": "my.pdf" }`.

- `upload_file_base64(base64: str, filename: str) -> dict`
  - Purpose: Upload raw Base64 content and persist to temp storage.
  - Inputs:
    - `base64` (str): Base64 string
    - `filename` (str): filename to use when saving
  - Returns: dict:
    - `path`, `filename`, `directory`, `size` (int), `meta`
  - Errors: Raises `ValueError` on decoding or write errors.

- `upload_file_url(url: str, filename: Optional[str] = None) -> dict`
  - Purpose: Download a remote file (HTTP/HTTPS) and save to temp storage.
  - Inputs:
    - `url` (str): direct URL to file
    - `filename` (Optional[str]): optional override filename
  - Returns: dict with `path`, `filename`, `directory`, `meta`.
  - Notes: Requires `requests` package to be available in the environment.

---

**Text Extraction**

- `extract_text(file: Any, encoding: Optional[str] = "utf-8") -> dict`
  - Purpose: Extract all text from a PDF and return summary metrics.
  - Inputs:
    - `file` (Any): same resolver rules as `upload_file` (path, temp filename, bytes, base64 dict).
    - `encoding` (str|None): encoding used when returning text (default `utf-8`).
  - Returns: dict:
    - `text` (str): full extracted text
    - `page_count` (int): number of pages processed
    - `char_count` (int): number of characters in `text`
    - `meta` (dict): includes `resolved_path` pointing to saved temp file
  - Errors:
    - Raises `ValueError` with helpful hint explaining how to provide the file if extraction fails.
  - Example usage:
    - Upload a file with `upload_file`, then call `extract_text` with the returned `path`.

- `extract_text_by_page(file: Any, pages: Optional[List[int]] = None, page_range: Optional[str] = None, encoding: Optional[str] = "utf-8") -> list[dict]`
  - Purpose: Extract text from specific pages or a page range.
  - Inputs:
    - `file` (Any): resolver rules as above
    - `pages` (Optional[List[int]]): list of 1-based page indices to extract (e.g., `[1,3,5]`).
    - `page_range` (Optional[str]): range expression like `"1-3,5"` (parser in `utils.parsers` will be used).
    - `encoding` (Optional[str]): text encoding
  - Returns: list of page result dicts; each dict typically contains:
    - `page_number` (int)
    - `text` (str)
    - `char_count` (int)
  - Behavior: If both `pages` and `page_range` are provided, `pages` takes precedence. The tool returns a list directly (framework wraps list results).
  - Errors: Raises `ValueError` on invalid pages or extraction failures.

- `extract_metadata(file: Any) -> dict`
  - Purpose: Extract detailed PDF metadata (author, title, producer, creation/mod dates, custom metadata, etc.).
  - Inputs: `file` same as above.
  - Returns: dict containing metadata keys found in the PDF plus `meta` operation info.

---

**Conversion**

- `pdf_to_images(file_path: str, output_dir: str, format: str = "png", dpi: int = 150, pages: Optional[List[int]] = None) -> list[dict]`
  - Purpose: Convert one or more PDF pages to image files.
  - Inputs:
    - `file_path` (str): path to the PDF on disk (absolute or temp path).
    - `output_dir` (str): directory where generated images will be written.
    - `format` (str): image format, e.g., `png`, `jpeg`.
    - `dpi` (int): resolution for conversion (default 150).
    - `pages` (Optional[List[int]]): list of 1-based pages to render; `None` for all pages.
  - Returns: list of dicts for each generated image:
    - `path` (str), `page_number` (int), `size` (int), `format` (str)
  - Notes: Implementation uses `pdf2image` and PIL; ensure dependencies and poppler are installed on the host.

- `images_to_pdf(image_paths: List[str], output_path: str, page_size: str = "A4", orientation: str = "portrait") -> dict`
  - Purpose: Create a PDF document from multiple images.
  - Inputs:
    - `image_paths` (List[str]): list of image file paths in order
    - `output_path` (str): path for the generated PDF
    - `page_size` (str): e.g., `A4`, `Letter` (processor maps to physical sizes)
    - `orientation` (str): `portrait` or `landscape`
  - Returns: dict with success info and `meta` including operation timing.

---

**PDF Manipulation**

- `merge_pdfs(input_files: List[str], output_path: str) -> dict`
  - Purpose: Merge multiple PDF files into a single PDF.
  - Inputs:
    - `input_files` (List[str]): file paths
    - `output_path` (str): destination path
  - Returns: dict with details (e.g., `path`) and `meta`.

- `split_pdf(file_path: str, split_ranges: List[Dict[str, Any]]) -> list[dict]`
  - Purpose: Split a PDF into multiple files by page ranges.
  - Inputs:
    - `file_path` (str): source PDF
    - `split_ranges` (List[Dict]): each dict should describe `start` and `end` pages and optional `filename`.
  - Returns: list of generated files info dicts.

- `rotate_pages(file_path: str, rotations: List[Dict[str, int]], output_path: str) -> dict`
  - Purpose: Rotate specific pages in a PDF and write to `output_path`.
  - Inputs:
    - `file_path` (str): source PDF
    - `rotations` (List[Dict]): each dict should include `page` (1-based) and `degrees` (e.g., 90, 180, 270).
    - `output_path` (str): target PDF path
  - Returns: dict with `path` and `meta`.

---

Notes:
- All tools log an `operation_id` and execution time in ms in the returned `meta` object.
- Tools that return lists set `x-fastmcp-wrap-result=true` for the framework so they are returned as bare lists.
- Tools will raise `ValueError` for user-facing errors; internal exceptions are logged.
- For file inputs, prefer uploading first via `upload_file` to ensure files are in the server temp directory.
- `page_range` syntax uses `utils.parsers.parse_page_range`: e.g., `"1-3,5,7-9"`.
- If both `pages` and `page_range` are passed, `pages` takes precedence.
- Image conversion requires Poppler (see below).

### Example JSON: extract_text (simple)
- Request arguments:
```json
{
  "file": "C:/path/to/input.pdf",
  "encoding": "utf-8"
}
```
- Response shape:
```json
{
  "text": "... full extracted text ...",
  "page_count": 3,
  "char_count": 1234,
  "meta": { "operation_id": "<hex>", "execution_ms": 42 }
}
```

### Uploading files (Claude Desktop and clients)
Claude may not automatically send binary file contents. Use one of these upload tools to persist a file to the server temp directory, then reference it by short filename in subsequent calls.

1) Upload a file (generic)
- Tool: `upload_file`
- Request:
```json
{
  "name": "upload_file",
  "arguments": {
    "file": { "base64": "<BASE64_DATA>", "filename": "document.pdf" }
  }
}
```
- Response contains `filename` and absolute `path` under the server `temp_dir`.

2) Upload a file as base64 (explicit schema)
- Tool: `upload_file_base64`
- Request:
```json
{
  "name": "upload_file_base64",
  "arguments": { "base64": "<BASE64_DATA>", "filename": "document.pdf" }
}
```

3) Upload a file from URL (explicit schema)
- Tool: `upload_file_url`
- Request:
```json
{
  "name": "upload_file_url",
  "arguments": { "url": "https://example.com/document.pdf", "filename": "document.pdf" }
}
```

4) Extract text using the saved short filename
- Request:
```json
{
  "name": "extract_text",
  "arguments": { "file": "document.pdf" }
}
```

Alternative: provide a URL to `upload_file` (requires `requests` installed):
```json
{
  "name": "upload_file",
  "arguments": {
    "file": { "url": "https://example.com/document.pdf", "filename": "document.pdf" }
  }
}
```

Manual option: run `server_info` to get `temp_dir`, copy your file into that directory, then call tools with the short filename.

### Example JSON: merge_pdfs
- Request arguments:
```json
{
  "input_files": [
    "C:/path/a.pdf",
    "C:/path/b.pdf"
  ],
  "output_path": "C:/path/merged.pdf"
}
```
- Response shape:
```json
{
  "output_path": "C:/path/merged.pdf",
  "page_count": 10,
  "size": 456789,
  "meta": { "operation_id": "<hex>", "execution_ms": 87 }
}
```

## Configuration
Configuration is loaded via `pydantic-settings` from `.env` and environment variables.

Env vars (case-insensitive):
- `MAX_FILE_SIZE_MB` (int, default 50): Max file size for inputs.
- `LOG_LEVEL` (str, default `INFO`): Logging level.
- `LOG_FILE_PATH` (str, default `logs/pdf-processor-server.log`): Log file path.
- `TEMP_DIR` (str, default `temp_files`): Working temp storage directory.
- `SERVER_NAME` (str, default `pdf-processor-server`): Server name.
- `SERVER_VERSION` (str, default `1.0.0`): Server version.

Path helpers:
- `TEMP_DIR` resolves to absolute `settings.temp_path`.
- `LOG_FILE_PATH` resolves to absolute `settings.log_path`.

## Storage & Security
- Temp files are stored under `TEMP_DIR` and cleaned up automatically after 24h of inactivity.
- `ensure_within_temp(path)` prevents reading files outside `TEMP_DIR` for base64 retrieval.
- Validators enforce allowed extensions and size limits for PDFs and images.

## Logging & Telemetry
- Rotating logs at `LOG_FILE_PATH` (10MB x 5). No stdout/stderr prints.
- Each tool returns `meta.operation_id` and `meta.execution_ms` for traceability.
- Server banner and lifecycle logs are emitted by FastMCP at startup/shutdown.

## Windows: Poppler for pdf2image
`pdf2image` requires Poppler binaries.
- Download: https://github.com/oschwartz10612/poppler-windows/releases/
- Extract, add `poppler-*/Library/bin` to your `PATH`.
- Verify: `pdftoppm -v` prints a version. If not available, `pdf_to_images` tools will raise helpful errors.

## Developer Guide

### Project layout
- `src/fastmcp_pdf_server/`
  - `main.py`: Builds FastMCP app, registers tools, runs via STDIO.
  - `config.py`: Pydantic settings for env and paths.
  - `utils/`: Logger, validators, parsers.
  - `services/`: PDF and image operations, file manager.
  - `tools/`: Thin async wrappers exposing services as MCP tools.

### Install & Run
```
python -m venv .venv
\.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m fastmcp_pdf_server
```

### Tests
```
pytest -q
```
Conversion tests are skipped if Poppler (`pdftoppm`) is not found.

### Troubleshooting
- Startup hangs after banner: normal for STDIO mode (waiting for an MCP client).
- `pdf2image` errors: ensure Poppler on PATH; retry shell after updating PATH.
- `ValueError: File not found` or `Invalid file extension`: check inputs and validators.
- Large files slow/timeout: reduce `dpi`, use page-range, or increase resources.

## Performance Notes
- Max file size is enforced; adjust `MAX_FILE_SIZE_MB` if needed.
- Prefer page-scoped ops for large PDFs.
- Lower `dpi` for faster PDF→image conversions.

## Optional HTTP Mode (advanced)
FastMCP supports a streamable HTTP transport. This server defaults to STDIO. For experimentation, you can run an HTTP endpoint:

```python
# run_http.py
import asyncio
from fastmcp_pdf_server.main import build_app

async def main():
  app = build_app()
  await app.run_http_async(host="127.0.0.1", port=8000, path="mcp")

asyncio.run(main())
```

Happy Coding!