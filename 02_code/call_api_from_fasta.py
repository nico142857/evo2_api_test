# Contenido para: call_api_from_fasta.py

import requests
import os
import json
import argparse             ## NUEVO ##
from pathlib import Path
from Bio import SeqIO       ## NUEVO ##

## NUEVO: Función para leer el archivo FASTA ##
def leer_fasta(ruta_archivo):
    """Lee un archivo FASTA y devuelve la primera secuencia que encuentra."""
    try:
        with open(ruta_archivo, "r") as handle:
            for record in SeqIO.parse(handle, "fasta"):
                print(f"Secuencia leída desde el archivo: {record.id} (longitud: {len(record.seq)})")
                return str(record.seq)
    except FileNotFoundError:
        return None

# --- CONFIGURACIÓN ---
## NUEVO: Usamos argparse para recibir el archivo FASTA como un argumento ##
parser = argparse.ArgumentParser(description="Enviar una secuencia desde un archivo FASTA a la API de Evo2.")
parser.add_argument("--fasta", required=True, help="Ruta al archivo .fasta de entrada.")
args = parser.parse_args()

# La clave de API se sigue obteniendo de la misma forma
key = os.getenv("NVCF_RUN_KEY") or input("Pega tu clave de API (Run Key) y presiona Enter: ")

# El modelo que quieres usar
url_del_modelo = "https://health.api.nvidia.com/v1/biology/arc/evo2-40b/generate"

## NUEVO: 'mi_secuencia' ahora se lee del archivo en lugar de estar codificada ##
mi_secuencia = leer_fasta(args.fasta)

# Si no se pudo leer la secuencia, el script se detiene.
if not mi_secuencia:
    print(f"Error: No se pudo leer la secuencia del archivo: {args.fasta}")
    exit()

# Parámetros de la generación
parametros = {
    "sequence": mi_secuencia,
    "num_tokens": 100, # Número de nucleótidos a generar
    "top_k": 4,
}
# --- FIN DE LA CONFIGURACIÓN ---

print(f"\nEnviando los primeros 60 caracteres del prompt a la API de Nvidia: '{mi_secuencia[:60]}...'")

# El resto del script es igual
headers = {
    "Authorization": f"Bearer {key}"
}

try:
    response = requests.post(url=url_del_modelo, headers=headers, json=parametros)
    response.raise_for_status() # Lanza un error si la petición falla

    # Ruta de salida organizada
    ruta_salida = Path("../03_out/output.json")
    
    print(f"Respuesta recibida. Guardando en '{ruta_salida}'...")
    
    # Crea el directorio de salida si no existe
    ruta_salida.parent.mkdir(exist_ok=True)
    
    # Guardamos la respuesta en un archivo para analizarla
    ruta_salida.write_text(json.dumps(response.json(), indent=2))
    
    print("\n--- Resultado de la API ---")
    respuesta_json = response.json()
    print(json.dumps(respuesta_json, indent=2))
    print("\n¡Éxito! El resultado completo está en el archivo.")

    secuencia_generada = respuesta_json.get("sequence", "")
    secuencia_completa = mi_secuencia + secuencia_generada

    print("\n--- Secuencia Completa (Prompt + Generación) ---")
    print(secuencia_completa[:500] + "...") # Mostramos los primeros 500 caracteres

except requests.exceptions.HTTPError as err:
    print(f"\n--- ERROR ---")
    print(f"Error en la petición HTTP: {err}")
    print(f"Cuerpo de la respuesta: {err.response.text}")
except Exception as e:
    print(f"\n--- ERROR ---")
    print(f"Ha ocurrido un error inesperado: {e}")
