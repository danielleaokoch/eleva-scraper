# backup_supabase.py - Backup automático do Supabase para Google Drive
import os
import json
import requests
from datetime import datetime
from supabase import create_client
import logging

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 🔑 Carregar variáveis de ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")  # Pasta no seu Google Drive
GOOGLE_OAUTH_TOKEN = os.getenv("GOOGLE_OAUTH_TOKEN")  # Token OAuth2 do Google

# Verificar variáveis obrigatórias
if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GOOGLE_DRIVE_FOLDER_ID, GOOGLE_OAUTH_TOKEN]):
    logging.error("❌ Variáveis de ambiente do backup não configuradas!")
    exit(1)

# Conexão com Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def backup_vagas_to_google_drive():
    """Faz backup da tabela vagas para Google Drive"""
    try:
        # 1. Buscar todos os dados da tabela
        logging.info("📥 Iniciando backup da tabela 'vagas'...")
        response = supabase.table("vagas").select("*").execute()
        data = response.data
        
        if not data:
            logging.warning("⚠️ Tabela 'vagas' está vazia - backup não realizado")
            return False
        
        logging.info(f"✅ Coletados {len(data)} registros para backup")
        
        # 2. Preparar arquivo JSON
        backup_data = {
            "metadata": {
                "tabela": "vagas",
                "data_backup": datetime.now().isoformat(),
                "total_registros": len(data),
                "projeto": os.getenv("SUPABASE_PROJECT_REF", "desconhecido")
            },
            "dados": data
        }
        
        filename = f"backup_vagas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # 3. Fazer upload para Google Drive
        headers = {
            "Authorization": f"Bearer {GOOGLE_OAUTH_TOKEN}",
            "Content-Type": "application/json"
        }
        
        upload_url = f"https://www.googleapis.com/upload/drive/v3/files?uploadType=media&name={filename}&parents={GOOGLE_DRIVE_FOLDER_ID}"
        
        response = requests.post(
            upload_url,
            headers=headers,
            data=json.dumps(backup_data, ensure_ascii=False, indent=2),
            timeout=30
        )
        
        if response.status_code == 200:
            file_id = response.json().get("id")
            logging.info(f"✅ Backup salvo no Google Drive! Arquivo ID: {file_id}")
            logging.info(f"🔗 Link do backup: https://drive.google.com/file/d/{file_id}/view")
            return True
        else:
            error_msg = response.json().get("error", {}).get("message", "Erro desconhecido")
            logging.error(f"❌ Falha no upload para Google Drive: {error_msg} (Status: {response.status_code})")
            return False
    
    except Exception as e:
        logging.error(f"❌ Erro no backup: {str(e)}")
        return False

if __name__ == "__main__":
    backup_vagas_to_google_drive()
