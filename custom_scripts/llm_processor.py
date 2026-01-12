#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import subprocess
import re

# Configuración desde variables de entorno
OLLAMA_HOST = os.environ.get("PAPERLESS_LLM_HOST", "http://host.docker.internal:4686")
OLLAMA_MODEL = os.environ.get("PAPERLESS_LLM_MODEL", "deepseek-r1:8b")
PAPERLESS_URL = os.environ.get("PAPERLESS_URL", "http://localhost:8000") # URL interna o externa según configuración
PAPERLESS_TOKEN = os.environ.get("PAPERLESS_API_TOKEN") # Token para API de Paperless (opcional si se usa script interno con auth directa no disponible, pero post-consume suele requerir token)
API_URL = f"{OLLAMA_HOST}/api/generate"

def log(message):
    print(f"[LLM Processor] {message}")

def call_ollama(prompt):
    """Llama a la API de Ollama."""
    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        json_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(API_URL, data=json_data, headers={'Content-Type': 'application/json'})

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "")

    except Exception as e:
        log(f"Error conectando a Ollama ({API_URL}): {e}")
        return None

def get_document_content(file_path):
    """Intenta extraer texto de las primeras páginas del documento."""
    text = ""
    if not file_path or not os.path.exists(file_path):
        return ""

    try:
        # Intentar usar pdftotext (si es PDF)
        if file_path.lower().endswith('.pdf'):
            # Extraer primera página (-l 1) a stdout (-)
            result = subprocess.run(['pdftotext', '-l', '1', file_path, '-'], capture_output=True, text=True)
            if result.returncode == 0:
                text = result.stdout
            else:
                log(f"pdftotext falló o no encontró texto: {result.stderr}")
        else:
            # Intentar leer como texto plano
            with open(file_path, 'r', errors='ignore') as f:
                text = f.read(2000) # Primeros 2000 chars
    except Exception as e:
        log(f"No se pudo extraer texto del archivo: {e}")

    return text.strip()[:2000]

def update_document_note(doc_id, note_content):
    """Añade una nota al documento usando la API de Paperless."""
    # Nota: Los scripts de post-consumo corren en el contexto del contenedor.
    # Para acceder a la API, necesitamos un token.
    # Si no hay token configurado, no podemos escribir de vuelta a menos que usemos hacks de DB (no recomendado) o API sin auth (raro).

    # Intentar obtener token de variable de entorno
    token = os.environ.get("PAPERLESS_API_TOKEN")

    if not token:
        log("ADVERTENCIA: No se configuró PAPERLESS_API_TOKEN. No se puede guardar el resumen en Paperless.")
        log(f"Resumen generado (no guardado): {note_content}")
        return

    api_endpoint = f"{PAPERLESS_URL}/api/documents/{doc_id}/notes/"

    data = {
        "note": f"🤖 Análisis LLM:\n{note_content}",
        "document": int(doc_id)
    }

    try:
        json_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(api_endpoint, data=json_data, headers={
            'Content-Type': 'application/json',
            'Authorization': f'Token {token}'
        })

        with urllib.request.urlopen(req) as response:
            if response.status == 201:
                log("✅ Resumen guardado exitosamente como nota en el documento.")
            else:
                log(f"⚠️ Error al guardar nota. Estado: {response.status}")

    except Exception as e:
        log(f"Error llamando a API de Paperless: {e}")

def main():
    try:
        document_id = os.environ.get("DOCUMENT_ID")
        file_name = os.environ.get("DOCUMENT_FILE_NAME")
        source_path = os.environ.get("DOCUMENT_SOURCE_PATH")

        log(f"Iniciando procesamiento para Doc ID: {document_id}, Archivo: {file_name}")

        content_snippet = get_document_content(source_path)

        prompt = f"""
        Actúa como un experto en gestión documental del sistema de salud público de Chile (GES/AUGE, Oncología).

        Analiza el siguiente documento:
        Nombre del archivo: "{file_name}"

        Contenido inicial (fragmento):
        \"\"\"
        {content_snippet}
        \"\"\"

        Tarea:
        1. Clasificar el Tipo de documento.
        2. Generar un resumen ejecutivo conciso.

        Responde SOLO con el siguiente formato:
        Tipo: [Tipo Detectado]
        Resumen: [Resumen de 1-2 líneas]
        """

        response = call_ollama(prompt)

        if response:
            # Limpiar etiquetas <think>...</think> si el modelo las genera (común en deepseek-r1)
            clean_response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()

            log(f"Análisis LLM: {clean_response}")

            # Guardar en Paperless
            update_document_note(document_id, clean_response)

        else:
            log("No se recibió respuesta del LLM.")

    except Exception as e:
        log(f"Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
