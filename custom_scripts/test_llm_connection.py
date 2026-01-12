import json
import urllib.request
import sys

# Configuración de prueba (asumiendo ejecución desde el host)
OLLAMA_HOST = "http://localhost:4686"
OLLAMA_MODEL = "deepseek-r1:8b"
API_URL = f"{OLLAMA_HOST}/api/generate"

def test_ollama():
    print(f"Probando conexión a: {API_URL}")
    print(f"Modelo: {OLLAMA_MODEL}")

    prompt = """
    Actúa como un experto en gestión documental.
    Analiza el siguiente nombre de archivo ficticio: "Oficio 123 - Solicitud de Recursos.pdf"
    
    Responde estrictamente con el formato: 
    Tipo: [Tipo] | Resumen: [Resumen]
    """

    data = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        json_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(API_URL, data=json_data, headers={'Content-Type': 'application/json'})

        print("Enviando solicitud...")
        with urllib.request.urlopen(req) as response:
            status = response.status
            print(f"Estado HTTP: {status}")
            
            result = json.loads(response.read().decode("utf-8"))
            response_text = result.get("response", "")
            
            print("\n--- Respuesta del Modelo ---")
            print(response_text)
            print("----------------------------")
            
            if response_text:
                print("\n✅ ÉXITO: El modelo recibió los parámetros y respondió.")
            else:
                print("\n⚠️ ADVERTENCIA: La respuesta está vacía.")

    except urllib.error.URLError as e:
        print(f"\n❌ ERROR DE CONEXIÓN: No se pudo conectar a {OLLAMA_HOST}")
        print(f"Detalle: {e}")
        print("Verifica que Ollama esté corriendo y escuchando en el puerto 4686.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    test_ollama()
