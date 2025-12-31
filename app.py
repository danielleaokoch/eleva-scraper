# app.py
from api import app
import subprocess
import sys

def run_scrapper():
    """Executa o scrapper.py ao iniciar o serviço"""
    try:
        result = subprocess.run([sys.executable, "scrapper.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Scrapper executado com sucesso!")
        else:
            print(f"❌ Erro ao executar scrapper.py: {result.stderr}")
    except Exception as e:
        print(f"❌ Erro ao tentar executar scrapper.py: {e}")

if __name__ == "__main__":
    # Executa o scrapper antes de iniciar a API
    run_scrapper()
    
    # Inicia a API
    app.run(host="0.0.0.0", port=8000)
