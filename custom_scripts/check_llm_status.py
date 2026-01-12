import json
import urllib.request
import sys

# Configuración
OLLAMA_HOST = "http://localhost:4686"
API_PS_URL = f"{OLLAMA_HOST}/api/ps"

def check_status():
    print(f"Consultando estado de Ollama en: {API_PS_URL}")

    try:
        req = urllib.request.Request(API_PS_URL)
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                models = data.get("models", [])

                if models:
                    print("\n🔵 Modelos actualmente en ejecución (Memoria):")
                    for m in models:
                        name = m.get("name", "Desconocido")
                        size = m.get("size", 0) / (1024**3) # GB
                        vram = m.get("size_vram", 0) / (1024**3)
                        print(f" - {name} | Tamaño: {size:.2f}GB | VRAM: {vram:.2f}GB")
                else:
                    print("\n⚪ Ningún modelo está cargado en memoria actualmente (Idle).")
            else:
                print(f"Respuesta inesperada: {response.status}")

    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("\n⚠️ El endpoint /api/ps no existe. Probablemente una versión antigua de Ollama.")
            print("Intentando /api/tags para ver qué modelos están disponibles...")
            check_tags()
        else:
            print(f"Error HTTP: {e}")
    except Exception as e:
        print(f"Error de conexión: {e}")

def check_tags():
    try:
        url = f"{OLLAMA_HOST}/api/tags"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            print("\n📚 Modelos disponibles en disco:")
            for m in data.get("models", []):
                print(f" - {m.get('name')}")
    except Exception as e:
        print(f"No se pudieron listar los tags: {e}")

if __name__ == "__main__":
    check_status()
