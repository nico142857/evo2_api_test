# Contenido para: 02_code/validar_generacion.py

import requests
import os
import json
import argparse
from pathlib import Path
from Bio import SeqIO

## NUEVO: Función para comparar dos secuencias ##
def comparar_secuencias(seq1, seq2):
    """Compara dos secuencias y devuelve el porcentaje de identidad."""
    coincidencias = 0
    longitud_minima = min(len(seq1), len(seq2))
    for i in range(longitud_minima):
        if seq1[i] == seq2[i]:
            coincidencias += 1
    
    if longitud_minima == 0:
        return 0.0
        
    identidad = (coincidencias / longitud_minima) * 100
    return identidad

def leer_fasta(ruta_archivo):
    """Lee un archivo FASTA y devuelve la primera secuencia que encuentra."""
    try:
        with open(ruta_archivo, "r") as handle:
            for record in SeqIO.parse(handle, "fasta"):
                print(f"Secuencia leída desde el archivo: {record.id} (longitud total: {len(record.seq)})")
                return str(record.seq)
    except FileNotFoundError:
        return None

# --- CONFIGURACIÓN ---
parser = argparse.ArgumentParser(description="Valida la capacidad de completado de Evo2 en un archivo FASTA.")
parser.add_argument("--fasta", required=True, help="Ruta al archivo .fasta de entrada.")
## NUEVO: Argumento para definir cuántos nucleótidos ocultar y predecir ##
parser.add_argument("--holdout", type=int, default=100, help="Número de nucleótidos finales a ocultar y usar para validación.")
args = parser.parse_args()

key = os.getenv("NVCF_RUN_KEY") or input("Pega tu clave de API (Run Key) y presiona Enter: ")
url_del_modelo = "https://health.api.nvidia.com/v1/biology/arc/evo2-40b/generate"

secuencia_completa = leer_fasta(args.fasta)
if not secuencia_completa:
    print(f"Error: No se pudo leer la secuencia del archivo: {args.fasta}")
    exit()

## MODIFICADO: Dividimos la secuencia en 'prompt' y 'ground truth' ##
holdout_size = args.holdout
prompt_seq = secuencia_completa[:-holdout_size]       # Todo excepto los últimos N nucleótidos
ground_truth_seq = secuencia_completa[-holdout_size:] # Solo los últimos N nucleótidos

print(f"Longitud del prompt: {len(prompt_seq)}")
print(f"Longitud de la secuencia a validar/generar: {len(ground_truth_seq)}")

## MODIFICADO: Los parámetros ahora usan el prompt y la longitud a generar ##
parametros = {
    "sequence": prompt_seq,
    "num_tokens": len(ground_truth_seq), # Generar exactamente la longitud que ocultamos
    "top_k": 4,
}
# --- FIN DE LA CONFIGURACIÓN ---

print(f"\nEnviando prompt a la API de Nvidia (últimos 60 caracteres: '...{prompt_seq[-60:]}')")

headers = {
    "Authorization": f"Bearer {key}"
}

try:
    response = requests.post(url=url_del_modelo, headers=headers, json=parametros)
    response.raise_for_status()

    respuesta_json = response.json()
    secuencia_generada = respuesta_json.get("sequence", "")

    ## NUEVO: Lógica de comparación y resultados ##
    identidad = comparar_secuencias(ground_truth_seq, secuencia_generada)

    print("\n--- ¡COMPARACIÓN DE RESULTADOS! ---")
    print(f"Secuencia Real (Oculta):      {ground_truth_seq}")
    print(f"Secuencia Generada por Evo2:    {secuencia_generada}")
    print("---------------------------------")
    print(f"Identidad de la secuencia: {identidad:.2f}%")

    # Guardar el resultado completo para un análisis más detallado
    resultado_completo = {
        "prompt_info": {
            "fasta_file": args.fasta,
            "prompt_length": len(prompt_seq),
            "holdout_size": len(ground_truth_seq),
        },
        "ground_truth_sequence": ground_truth_seq,
        "generated_sequence": secuencia_generada,
        "comparison": {
            "identity_percentage": identidad
        }
    }
    ruta_salida = Path(f"../03_out/validation_result_{holdout_size}bp.json")
    ruta_salida.parent.mkdir(exist_ok=True)
    ruta_salida.write_text(json.dumps(resultado_completo, indent=2))
    print(f"\n✅ Resultado completo de la validación guardado en: {ruta_salida}")

except requests.exceptions.HTTPError as err:
    print(f"\n--- ERROR ---")
    print(f"Error en la petición HTTP: {err}")
    print(f"Cuerpo de la respuesta: {err.response.text}")
except Exception as e:
    print(f"\n--- ERROR ---")
    print(f"Ha ocurrido un error inesperado: {e}")
