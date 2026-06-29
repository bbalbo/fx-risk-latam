"""
Actualiza los datos y sube al repo. Correr una vez al mes:

    python refresh.py
"""
import subprocess
import sys
from datetime import date

def run(cmd):
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Error en: {cmd}")
        sys.exit(1)

print("Extrayendo datos frescos...")
run("python -m src.extraction")

today = date.today().strftime("%Y-%m-%d")
print(f"Commiteando y subiendo ({today})...")
run("git add data/fx_data.db")
run(f'git commit -m "data: refresh {today}"')
run("git push origin main")

print("Listo. Streamlit Cloud se actualizará en ~1 minuto.")
