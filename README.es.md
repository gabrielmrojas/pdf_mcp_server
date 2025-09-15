# Servidor de Procesamiento de PDF con FastMCP

Servidor MCP construido con FastMCP (transporte STDIO) que ofrece utilidades para PDF: extracción de texto, metadatos, unir/dividir/rotar y conversión PDF↔imágenes.

## Inicio Rápido (Windows PowerShell)
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m fastmcp_pdf_server
```

Si se instala como paquete, también puede ejecutar:
```
fastmcp-pdf-server
```

## Integración MCP
- Transporte: STDIO. No imprimir en stdout/stderr; los logs van a archivo.
- Nombre/versión del servidor: desde la config (`server_name`, `server_version`).
- Las herramientas se registran con `@app.tool()` y devuelven salidas estructuradas con un bloque `meta` que incluye `operation_id` y `execution_ms`.

Nota: Si actualiza dependencias (por ejemplo añadimos `requests` para subidas por URL), reinstale:
```
pip install -r requirements.txt
```

### Ejemplo para Claude Desktop
Añada a `claude_desktop_config.json`:
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

### Uso programático (Python)
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

## Herramientas Expuestas (API)
Todas las herramientas devuelven datos estructurados; muchas respuestas incluyen `meta.operation_id` y `meta.execution_ms`.
Algunas devuelven listas directamente (FastMCP añade `x-fastmcp-wrap-result=true`), por lo que el cliente recibe `{ "result": [ ... ] }`.

# Referencia de Herramientas MCP

Cada herramienta lista: propósito, entradas, salidas, comportamiento, ejemplos y notas.

---

**Utilidades / Servidor**

- `server_info()`
  - Propósito: Información básica del servidor y configuración no sensible.
  - Entradas: Ninguna
  - Devuelve: `name`, `version`, `max_file_size_mb`, `temp_dir`, `log_file`, `meta{operation_id, execution_ms}`
  - Ejemplo: `{ "name": "server_info" }`

- `list_temp_resources(content_type?: str, max_items?: int=100) -> list`
  - Propósito: Listar archivos temporales con filtro opcional de MIME.
  - Entradas: `content_type` (`application/pdf`, `image/png`, etc.), `max_items` límite.
  - Devuelve lista de dicts: `path`, `size`, `created`, `content_type`, `filename`, `extension`, `directory`.
  - Limpia primero recursos caducados.

- `get_pdf_info(file_path: str) -> dict`
  - Propósito: Info básica de PDF sin extraer texto.
  - Salida: `pages`, `size`, `version`, `encrypted`, `meta`.

- `get_resource_base64(file_path: str) -> dict`
  - Propósito: Obtener contenido base64 de un archivo dentro del directorio temporal.
  - Salida: `path`, `base64`, `meta`.

---

**Subidas**

- `upload_file(file: Any, filename?: str) -> dict`
  - Acepta ruta local, nombre corto existente en temp, bytes/file-like o dict `{ base64, filename }`.
  - Devuelve `path`, `filename`, `directory`, `meta`.

- `upload_file_base64(base64: str, filename: str) -> dict`
  - Sube contenido Base64 explícito. Devuelve además `size`.

- `upload_file_url(url: str, filename?: str) -> dict`
  - Descarga por HTTP/HTTPS. Requiere `requests`.

---

**Extracción de Texto**

- `extract_text(file: Any, encoding?: str="utf-8") -> dict`
  - Texto completo + métricas: `text`, `page_count`, `char_count`, `meta.resolved_path`.

- `extract_text_by_page(file: Any, pages?: int[], page_range?: str, encoding?: str="utf-8") -> list`
  - Extrae solo páginas indicadas. Cada elemento: `page_number`, `text`, `char_count`.
  - Prioridad: si hay `pages` y `page_range`, gana `pages`.

- `extract_metadata(file: Any) -> dict`
  - Metadatos detallados (autor, título, fechas, etc.) + `meta`.

---

**Conversión**

- `pdf_to_images(file_path: str, output_dir: str, format: str="png", dpi: int=150, pages?: int[]) -> list`
  - Convierte páginas a imágenes. Devuelve lista con `path`, `page_number`, `size`, `format`.
  - Requiere Poppler instalado.

- `images_to_pdf(image_paths: str[], output_path: str, page_size: str="A4", orientation: str="portrait") -> dict`
  - Combina imágenes en un PDF. Devuelve info + `meta`.

---

**Manipulación de PDF**

- `merge_pdfs(input_files: str[], output_path: str) -> dict`
- `split_pdf(file_path: str, split_ranges: {start:int,end:int,filename?:str}[]) -> list`
- `rotate_pages(file_path: str, rotations: {page:int,degrees:int}[], output_path: str) -> dict`

Notas:
- Sintaxis `page_range`: `"1-3,5,7-9"` (usa `parse_page_range`).
- Si se pasan `pages` y `page_range`, `pages` manda.
- Conversión de imágenes necesita Poppler.
- Los errores de usuario se devuelven como `ValueError` con mensaje claro.

### Ejemplo JSON: extract_text (simple)
- Petición:
```json
{ "file": "C:/ruta/entrada.pdf", "encoding": "utf-8" }
```
- Respuesta:
```json
{ "text": "...", "page_count": 3, "char_count": 1234, "meta": { "operation_id": "<hex>", "execution_ms": 42 } }
```

### Subir archivos (Claude Desktop y clientes)
1) Base64 genérico (`upload_file`):
```json
{ "name": "upload_file", "arguments": { "file": { "base64": "<BASE64>", "filename": "doc.pdf" } } }
```
2) Base64 explícito (`upload_file_base64`):
```json
{ "name": "upload_file_base64", "arguments": { "base64": "<BASE64>", "filename": "doc.pdf" } }
```
3) Desde URL (`upload_file_url`):
```json
{ "name": "upload_file_url", "arguments": { "url": "https://example.com/doc.pdf", "filename": "doc.pdf" } }
```
4) Extraer texto usando nombre corto:
```json
{ "name": "extract_text", "arguments": { "file": "doc.pdf" } }
```

### Ejemplo JSON: merge_pdfs
Petición:
```json
{ "input_files": [ "C:/path/a.pdf", "C:/path/b.pdf" ], "output_path": "C:/path/merged.pdf" }
```
Respuesta:
```json
{ "output_path": "C:/path/merged.pdf", "page_count": 10, "size": 456789, "meta": { "operation_id": "<hex>", "execution_ms": 87 } }
```

## Configuración
Cargada con `pydantic-settings` desde `.env` y variables de entorno.

Variables (no sensibles a mayúsculas/minúsculas):
- `MAX_FILE_SIZE_MB` (int, predeterminado 50)
- `LOG_LEVEL` (str, predeterminado `INFO`)
- `LOG_FILE_PATH` (str, predeterminado `logs/fastmcp_pdf_server.log`)
- `TEMP_DIR` (str, predeterminado `temp_files`)
- `SERVER_NAME` (str, predeterminado `pdf-processor-fastmcp`)
- `SERVER_VERSION` (str, predeterminado `1.0.0`)

Rutas derivadas:
- `TEMP_DIR` → `settings.temp_path` absoluto
- `LOG_FILE_PATH` → `settings.log_path` absoluto

## Almacenamiento y Seguridad
- Archivos temporales bajo `TEMP_DIR` con limpieza automática tras 24h de inactividad.
- `ensure_within_temp(path)` evita accesos fuera de `TEMP_DIR`.
- Validadores aplican extensiones y límites de tamaño permitidos.

## Logs y Telemetría
- Logs rotativos en `LOG_FILE_PATH` (10MB x 5). No se usa stdout/stderr.
- Cada herramienta devuelve `meta.operation_id` y `meta.execution_ms`.
- Sin trazas sensibles; para depurar ampliar `LOG_LEVEL=DEBUG`.

## Windows: Poppler para pdf2image
`pdf2image` requiere los binarios de Poppler.
- Descargar: https://github.com/oschwartz10612/poppler-windows/releases/
- Extraer y añadir `poppler-*/Library/bin` al `PATH`.
- Verificar: `pdftoppm -v` debe mostrar versión.

## Guía de Desarrollo

### Estructura del Proyecto
- `src/fastmcp_pdf_server/`
  - `main.py`: construye la app FastMCP, registra herramientas y corre por STDIO.
  - `config.py`: settings Pydantic para entorno y rutas.
  - `utils/`: logger, validadores, parsers.
  - `services/`: operaciones PDF/imagen y gestor de archivos.
  - `tools/`: envoltorios asíncronos finos que exponen servicios como herramientas MCP.

### Instalar y Ejecutar
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m fastmcp_pdf_server
```

### Pruebas
```
pytest -q
```
Las pruebas de conversión se omiten si no se encuentra Poppler (`pdftoppm`).

### Solución de Problemas
- Arranque y espera tras el banner: normal en modo STDIO (esperando cliente MCP).
- Errores de `pdf2image`: asegure Poppler en PATH y reinicie la consola.
- `ValueError: File not found` / extensiones inválidas: revise entradas y validadores.
- Archivos grandes lentos: baje `dpi`, use rangos de páginas o aumente recursos.
- Si faltan dependencias (por ejemplo `requests`), reinstale requirements.

## Rendimiento
- Limite tamaño (`MAX_FILE_SIZE_MB`).
- Use extracción por páginas para PDFs grandes.
- Reduzca `dpi` en conversiones si busca velocidad.

## Modo HTTP Opcional (avanzado)
FastMCP soporta transporte HTTP experimental. Este servidor usa STDIO por defecto. Ejemplo de script:

```python
# run_http.py
import asyncio
from fastmcp_pdf_server.main import build_app

async def main():
  app = build_app()
  await app.run_http_async(host="127.0.0.1", port=8000, path="mcp")

asyncio.run(main())
```

¡Feliz Codificación!
