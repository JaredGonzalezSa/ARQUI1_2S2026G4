"""Preparacion automatica de los entornos de ejecucion del proyecto.

Permite iniciar cada componente con ``python app.py`` o ``python main.py``.
Cada carpeta conserva su propio entorno porque backend e IoT usan versiones
distintas de algunas dependencias.
"""

import hashlib
import os
from pathlib import Path
import subprocess
import sys


def _environment_python(environment):
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"

    return environment / "bin" / "python"


def _requirements_digest(requirements):
    return hashlib.sha256(requirements.read_bytes()).hexdigest()


def ensure_runtime(entry_file):
    """Crea, sincroniza y activa el entorno asociado al archivo de entrada."""
    entry = Path(entry_file).resolve()
    component_directory = entry.parent
    requirements = component_directory / "requirements.txt"
    environment = component_directory / ".venv"
    environment_python = _environment_python(environment)
    state_file = environment / ".requirements.sha256"

    if not requirements.exists():
        raise SystemExit(f"No se encontro el archivo de dependencias: {requirements}")

    try:
        if not environment_python.exists():
            print(f"[INICIO] Creando entorno virtual en {environment}...")
            subprocess.check_call([
                sys.executable,
                "-m",
                "venv",
                str(environment),
            ])

        expected_digest = _requirements_digest(requirements)
        installed_digest = (
            state_file.read_text(encoding="utf-8").strip()
            if state_file.exists()
            else ""
        )

        if installed_digest != expected_digest:
            print("[INICIO] Instalando dependencias del componente...")
            subprocess.check_call([
                str(environment_python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(requirements),
            ])
            state_file.write_text(expected_digest, encoding="utf-8")

    except (OSError, subprocess.CalledProcessError) as error:
        print(f"[INICIO] No se pudo preparar el entorno: {error}")
        print(
            "[INICIO] Verifique la conexion a Internet y que python3-venv "
            "este instalado."
        )
        raise SystemExit(1) from error

    if Path(sys.prefix).resolve() != environment.resolve():
        print(f"[INICIO] Ejecutando con {environment_python}...")
        try:
            exit_code = subprocess.call([
                str(environment_python),
                str(entry),
                *sys.argv[1:],
            ])
        except OSError as error:
            print(f"[INICIO] No se pudo iniciar el componente: {error}")
            raise SystemExit(1) from error

        raise SystemExit(exit_code)
