import os
import sys
import subprocess
import shutil
import random
import string
import platform

class Coordinator:
    def __init__(self):
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.docker_compose_file = os.path.join(self.root_dir, "docker-compose.yml")
        self.env_file = os.path.join(self.root_dir, "docker-compose.env")
        self.dot_env_file = os.path.join(self.root_dir, ".env")
        self.is_windows = platform.system().lower() == "windows"

    def run_command(self, command, cwd=None, shell=True):
        """Ejecuta un comando de sistema y maneja errores."""
        try:
            print(f"Ejecutando: {command}")
            # En Windows con shell=True, necesitamos pasar el comando como string
            if self.is_windows and isinstance(command, list):
                command = subprocess.list2cmdline(command)

            subprocess.check_call(command, cwd=cwd, shell=shell)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error al ejecutar el comando: {e}")
            return False

    def check_prerequisites(self):
        """Verifica si Docker y Docker Compose están instalados y el demonio corre."""
        print("Verificando prerequisitos...")
        if not shutil.which("docker"):
            print("Error: Docker no encontrado. Por favor instala Docker Desktop.")
            return False

        # Verificar si docker compose funciona
        try:
            subprocess.check_output(["docker", "compose", "version"], stderr=subprocess.STDOUT)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: 'docker compose' no funciona. Asegúrate de tener una versión reciente de Docker.")
            return False

        # Verificar conexión al demonio de Docker
        try:
            subprocess.check_output(["docker", "info"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            print("\n" + "="*50)
            print("ERROR CRÍTICO: No se puede conectar al motor de Docker.")
            print("="*50)
            print("Posibles causas:")
            print("1. Docker Desktop NO está corriendo.")
            print("2. No tienes permisos (ejecuta la terminal como Administrador).")
            print("3. El servicio de Docker está detenido.")
            print("\nSolución: Abre Docker Desktop y espera a que el ícono deje de animarse.")
            print("="*50 + "\n")
            return False

        print("Prerequisitos verificados correctamente.")
        return True

    def generate_secret_key(self):
        """Genera una clave secreta aleatoria."""
        chars = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
        return ''.join(random.choice(chars) for i in range(50))

    def setup(self):
        """Configura la instalación inicial."""
        print("\n--- Configuración Inicial ---")

        if os.path.exists(self.docker_compose_file):
            print(f"¡Atención! Ya existe un archivo 'docker-compose.yml'.")
            print("Si respondes 'n', se mantendrá la configuración actual (recomendado si ya lo configuraste).")
            overwrite = input("¿Sobrescribir y reconfigurar desde cero? (s/n): ").lower()
            if overwrite != 's':
                print("Manteniendo configuración existente.")
                return

        print("Selecciona la base de datos:")
        print("1. PostgreSQL (Recomendado)")
        print("2. PostgreSQL + Tika/Gotenberg (Soporte Office)")
        print("3. MariaDB")
        print("4. MariaDB + Tika/Gotenberg")
        print("5. SQLite")
        print("6. SQLite + Tika/Gotenberg")

        choice = input("Opción [1]: ") or "1"

        source_compose = ""
        if choice == "1":
            source_compose = "docker-compose.postgres.yml"
        elif choice == "2":
            source_compose = "docker-compose.postgres-tika.yml"
        elif choice == "3":
            source_compose = "docker-compose.mariadb.yml"
        elif choice == "4":
            source_compose = "docker-compose.mariadb-tika.yml"
        elif choice == "5":
            source_compose = "docker-compose.sqlite.yml"
        elif choice == "6":
            source_compose = "docker-compose.sqlite-tika.yml"
        else:
            print("Opción inválida, usando PostgreSQL por defecto.")
            source_compose = "docker-compose.postgres.yml"

        # Copiar archivos
        src_compose_path = os.path.join(self.root_dir, "docker", "compose", source_compose)
        src_env_path = os.path.join(self.root_dir, "docker", "compose", "docker-compose.env")
        src_dotenv_path = os.path.join(self.root_dir, "docker", "compose", ".env")

        try:
            shutil.copy(src_compose_path, self.docker_compose_file)
            if not os.path.exists(self.env_file):
                shutil.copy(src_env_path, self.env_file)
            if not os.path.exists(self.dot_env_file):
                shutil.copy(src_dotenv_path, self.dot_env_file)
            print("Archivos de configuración copiados.")
        except FileNotFoundError as e:
            print(f"Error: No se encontraron los archivos plantilla en {os.path.join(self.root_dir, 'docker', 'compose')}")
            print(e)
            return

        # Modificar docker-compose.yml para build local si se desea
        build_local = input("¿Deseas construir la imagen desde el código fuente local? (s/n) [s]: ").lower() or "s"
        if build_local == "s":
            self.configure_local_build()

        # Configurar variables de entorno
        self.configure_env_vars()

        print("\nConfiguración completada. Ahora puedes ejecutar 'Construir e Iniciar'.")

    def configure_local_build(self):
        """Modifica docker-compose.yml para usar build local."""
        with open(self.docker_compose_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Reemplazar la imagen con build context
        # Buscamos la definición del servicio webserver
        if "image: ghcr.io/paperless-ngx/paperless-ngx:latest" in content:
            content = content.replace(
                "image: ghcr.io/paperless-ngx/paperless-ngx:latest",
                "build:\n      context: ."
            )
            with open(self.docker_compose_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print("Configurado para construir desde código local.")
        else:
            print("No se pudo detectar la línea de imagen para reemplazar. Verifica docker-compose.yml manualmente.")

    def configure_env_vars(self):
        """Configura variables en docker-compose.env."""
        with open(self.env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []

        # Preguntar configuraciones
        url = input("URL de acceso (ej. https://paperless.local) [dejar vacío si es local]: ")
        secret_key = self.generate_secret_key()
        timezone = input("Zona horaria (ej. America/Santiago) [America/Santiago]: ") or "America/Santiago"
        lang = input("Idioma OCR (ej. spa, eng) [spa]: ") or "spa"

        configured_keys = set()

        for line in lines:
            if line.startswith("#PAPERLESS_SECRET_KEY=") or line.startswith("PAPERLESS_SECRET_KEY="):
                new_lines.append(f"PAPERLESS_SECRET_KEY={secret_key}\n")
                configured_keys.add("PAPERLESS_SECRET_KEY")
            elif line.startswith("#PAPERLESS_TIME_ZONE=") or line.startswith("PAPERLESS_TIME_ZONE="):
                new_lines.append(f"PAPERLESS_TIME_ZONE={timezone}\n")
                configured_keys.add("PAPERLESS_TIME_ZONE")
            elif line.startswith("#PAPERLESS_OCR_LANGUAGE=") or line.startswith("PAPERLESS_OCR_LANGUAGE="):
                new_lines.append(f"PAPERLESS_OCR_LANGUAGE={lang}\n")
                configured_keys.add("PAPERLESS_OCR_LANGUAGE")
            elif url and (line.startswith("#PAPERLESS_URL=") or line.startswith("PAPERLESS_URL=")):
                new_lines.append(f"PAPERLESS_URL={url}\n")
                configured_keys.add("PAPERLESS_URL")
            else:
                new_lines.append(line)

        with open(self.env_file, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)

        print("Variables de entorno actualizadas.")

    def fix_windows_compatibility(self):
        """Convierte finales de línea CRLF a LF en scripts de docker/rootfs y custom_scripts."""
        print("Corrigiendo finales de línea para compatibilidad con Linux...")

        paths_to_fix = [
            os.path.join(self.root_dir, "docker", "rootfs"),
            os.path.join(self.root_dir, "custom_scripts")
        ]

        count = 0
        for base_path in paths_to_fix:
            if not os.path.exists(base_path):
                continue

            for root, dirs, files in os.walk(base_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Detectar si es texto/script
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()

                        if b'\r\n' in content:
                            content = content.replace(b'\r\n', b'\n')
                            with open(file_path, 'wb') as f:
                                f.write(content)
                            count += 1
                    except Exception as e:
                        pass
        print(f"Se corregieron finales de línea en {count} archivos.")

    def setup_llm(self):
        """Configura la integración con LLM (Ollama)."""
        print("\n--- Configuración LLM ---")
        scripts_dir = os.path.join(self.root_dir, "custom_scripts")
        script_path = os.path.join(scripts_dir, "llm_processor.py")

        if not os.path.exists(scripts_dir):
            os.makedirs(scripts_dir)
            print(f"Directorio creado: {scripts_dir}")

        # Contenido del script llm_processor.py
        script_content = '''#!/usr/bin/env python3
import os
import sys
import json
import urllib.request

# Configuración desde variables de entorno
OLLAMA_HOST = os.environ.get("PAPERLESS_LLM_HOST", "http://host.docker.internal:4686")
OLLAMA_MODEL = os.environ.get("PAPERLESS_LLM_MODEL", "deepseek-r1:8b")
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

def main():
    """
    Script de post-consumo para Paperless-ngx.
    """
    try:
        document_id = os.environ.get("DOCUMENT_ID")
        file_name = os.environ.get("DOCUMENT_FILE_NAME")

        log(f"Iniciando procesamiento para Doc ID: {document_id}, Archivo: {file_name}")
        log(f"Usando LLM: {OLLAMA_MODEL} en {OLLAMA_HOST}")

        prompt = f"""
        Actúa como un experto en gestión documental del sistema de salud público de Chile (GES/AUGE, Oncología).
        Analiza el siguiente nombre de archivo: "{file_name}"

        Tipos de documentos comunes:
        - Administrativos: Oficio, Ordinario, Circular, Memo, Correo Electrónico.
        - Normativos: Ley, Decreto, Resolución, Reglamento.
        - Gestión: Modelo de Gestión, Protocolo, Convenio, Programación.
        - Clínicos: Interconsulta, Informe Paciente, Comité Oncológico.

        Tu tarea:
        1. Identificar el Tipo de documento más adecuado basándote en el nombre.
        2. Generar un resumen ejecutivo de 1 línea.

        Responde estrictamente con el formato: Tipo: [Tipo] | Resumen: [Resumen]
        """

        response = call_ollama(prompt)

        if response:
            log(f"Análisis LLM: {response}")
            # Aquí podríamos usar la API de Paperless para guardar este resumen en una nota.
        else:
            log("No se recibió respuesta del LLM.")

    except Exception as e:
        log(f"Error crítico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
        # Siempre sobrescribimos para asegurar que esté actualizado
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)

        print(f"Script creado/actualizado: {script_path}")
        print("El script está configurado para conectar a tu Ollama local.")
        print("\nRecuerda ejecutar 'Construir (Build)' para aplicar correcciones de formato.")

    def build(self):
        """Construye los contenedores."""
        if self.is_windows:
            self.fix_windows_compatibility()

        print("\n--- Construyendo Contenedores ---")
        self.run_command(["docker", "compose", "build"])

    def start(self):
        """Inicia los contenedores."""
        print("\n--- Iniciando Servicios ---")
        self.run_command(["docker", "compose", "up", "-d"])
        print("Servicios iniciados. Ejecuta 'Logs' para ver el estado.")

    def stop(self):
        """Detiene los contenedores."""
        print("\n--- Deteniendo Servicios ---")
        self.run_command(["docker", "compose", "down"])

    def update(self):
        """Actualiza el código y reconstruye."""
        print("\n--- Actualizando Proyecto ---")
        if self.run_command(["git", "pull"]):
            self.build()
            self.start()
            print("Actualización completada.")
        else:
            print("Error al actualizar git.")

    def create_superuser(self):
        """Crea un superusuario de Django."""
        print("\n--- Crear Superusuario ---")
        print("Asegúrate de que los servicios estén corriendo.")
        self.run_command(["docker", "compose", "exec", "webserver", "python", "manage.py", "createsuperuser"])

    def show_logs(self):
        """Muestra los logs."""
        try:
            subprocess.run(["docker", "compose", "logs", "-f"])
        except KeyboardInterrupt:
            print("\nLogs detenidos.")

    def menu(self):
        while True:
            print("\n=== Coordinador Paperless-ngx ===")
            print("1. Instalar / Configurar")
            print("2. Construir (Build)")
            print("3. Iniciar (Up)")
            print("4. Detener (Down)")
            print("5. Actualizar (Git Pull + Build + Up)")
            print("6. Crear Superusuario")
            print("7. Ver Logs")
            print("8. Configurar LLM (Crear scripts)")
            print("9. Salir")

            opcion = input("Selecciona una opción: ")

            if opcion == "1":
                self.setup()
            elif opcion == "2":
                self.build()
            elif opcion == "3":
                self.start()
            elif opcion == "4":
                self.stop()
            elif opcion == "5":
                self.update()
            elif opcion == "6":
                self.create_superuser()
            elif opcion == "7":
                self.show_logs()
            elif opcion == "8":
                self.setup_llm()
            elif opcion == "9":
                print("¡Hasta luego!")
                sys.exit(0)
            else:
                print("Opción no válida.")

if __name__ == "__main__":
    coordinator = Coordinator()
    if coordinator.check_prerequisites():
        coordinator.menu()
