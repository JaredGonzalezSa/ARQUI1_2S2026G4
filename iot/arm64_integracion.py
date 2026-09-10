import platform
import subprocess

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

BINARIO_ARM64 = BASE_DIR / "arm64_stats"
ARCHIVO_RESULTADO = BASE_DIR / "resultado.txt"

def ejecutar_arm64():

    # Borrar resultado anterior para evitar
    # leer información vieja.
    if ARCHIVO_RESULTADO.exists():
        ARCHIVO_RESULTADO.unlink()

    arquitectura = platform.machine().lower()

    # En Raspberry Pi ARM64 se ejecuta directo.
    if arquitectura in ("aarch64", "arm64"):

        comando = [str(BINARIO_ARM64)]

    # En nuestra PC x86_64 usamos QEMU.
    else:

        comando = ["qemu-aarch64",str(BINARIO_ARM64)]

    subprocess.run(comando, cwd=BASE_DIR, check=True)

    if not ARCHIVO_RESULTADO.exists():

        raise FileNotFoundError("ARM64 no generó resultado.txt")

def leer_resultado():

    resultados = {}

    with open(ARCHIVO_RESULTADO, "r", encoding="utf-8") as archivo:

        for linea in archivo:

            linea = linea.strip()

            if not linea:
                continue

            clave, valor = linea.split(
                "=",
                1
            )

            clave = (
                clave
                .strip()
                .upper()
                .replace("Á", "A")
            )

            resultados[clave] = int(
                valor.strip()
            )

    return {
        "max": resultados["MAX"],
        "min": resultados["MIN"],
        "avg": resultados["AVG"],
        "count": resultados["COUNT"]
    }

def procesar_arm64():

    ejecutar_arm64()

    return leer_resultado()