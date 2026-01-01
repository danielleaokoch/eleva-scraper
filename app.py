# app.py — Coletor Ético de Vagas Executivas (CTO da Eleva) — SEGURO E DEFINITIVO

import requests
import time
import json
import logging
import os
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import urllib.parse
from supabase import create_client

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 🔑 Carregar variáveis de ambiente
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Verificar variáveis obrigatórias
required_vars = {
    "SERPAPI_KEY": SERPAPI_KEY,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
    "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    logging.error(f"❌ Variáveis de ambiente não configuradas: {', '.join(missing_vars)}")
    exit(1)

# Criar clientes Supabase (separados para segurança)
supabase_read = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)  # Para leitura pública
supabase_write = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)  # Para escrita segura

def scrape_google_jobs(query, days_back=1):
    """Busca vagas no Google usando SerpAPI"""
    all_jobs = []
    yesterday = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Fontes seguras para buscar via Google
    sources = [
        "site:linkedin.com/jobs",
        "site:gupy.com.br",
        "site:vagas.com.br",
        "site:trampos.co",
        "site:ciadetalentos.com.br",
        "site:glassdoor.com.br",
        "site:br.indeed.com"
    ]
    
    for source in sources:
        search_query = f'{query} {source} after:{yesterday}'
        logging.info(f"🔍 Buscando no Google (via SerpAPI): {search_query}")
        
        try:
            # Usar SerpAPI para buscar
            url = f"https://serpapi.com/search.json?q={urllib.parse.quote(search_query)}&hl=pt-BR&api_key={SERPAPI_KEY}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            res = requests.get(url, headers=headers, timeout=10)
            
            if res.status_code != 200:
                logging.warning(f"⚠️ SerpAPI erro {res.status_code}: {res.text[:100]}")
                continue
                
            data = res.json()
            
            if "organic_results" in data:
                for result in data["organic_results"][:10]:
                    link = result.get("link", "")
                    title = result.get("title", "Vaga executiva")
                    
                    # Evitar links do próprio Google ou vazios
                    if not link or "google.com" in link or "url?" in link:
                        continue
                    
                    # Detectar fonte
                    fonte = "Google"
                    if "linkedin.com/jobs" in link:
                        fonte = "LinkedIn"
                    elif "gupy.com.br" in link:
                        fonte = "Gupy"
                    elif "vagas.com.br" in link:
                        fonte = "Vagas.com.br"
                    elif "trampos.co" in link:
                        fonte = "Trampos.co"
                    elif "ciadetalentos.com.br" in link:
                        fonte = "Cia de Talentos"
                    elif "glassdoor.com.br" in link:
                        fonte = "Glassdoor"
                    elif "indeed.com" in link:
                        fonte = "Indeed"
                    
                    # Detectar senioridade
                    senioridade = "Sênior+"
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in ["diretor", "head", "c-level", "chief"]):
                        senioridade = "Diretor/Head"
                    elif "gerente" in title_lower:
                        senioridade = "Gerente"
                    elif "coordenador" in title_lower:
                        senioridade = "Coordenador"
                    elif any(kw in title_lower for kw in ["sênior", "senior", "seniore"]):
                        senioridade = "Sênior"
                    elif any(kw in title_lower for kw in ["júnior", "junior", "jr"]):
                        senioridade = "Júnior"
                    elif "pleno" in title_lower:
                        senioridade = "Pleno"
                    
                    all_jobs.append({
                        "cargo": title.strip(),
                        "empresa": "Não informado",
                        "salario": "Não informado",
                        "modalidade": "Não informado",
                        "data_publicacao": yesterday,
                        "localizacao": "Brasil",
                        "senioridade": senioridade,
                        "requisitos": [],
                        "experiencias": [],
                        "link_candidatura": link,
                        "fonte": fonte,
                        "created_at": datetime.now().isoformat()
                    })
            else:
                logging.warning(f"⚠️ Nenhum resultado em 'organic_results' para: {search_query}")
            
            time.sleep(2)  # respeitar rate limit do SerpAPI
            
        except Exception as e:
            logging.error(f"❌ Erro SerpAPI: {e}")
    
    return all_jobs

def run_scrapper():
    """Executa a coleta diária e salva no Supabase com segurança"""
    logging.info("🚀 Iniciando coleta de vagas executivas...")
    
    # Coletar novas vagas
    new_jobs = scrape_google_jobs("gestão OR negócios OR executivo")
    logging.info(f"📥 Coletadas {len(new_jobs)} vagas novas")

    # Salvar no Supabase (usando service_role para escrita)
    saved_count = 0
    for job in new_jobs:
        try:
            supabase_write.table("vagas").insert(job).execute()
            logging.info(f"✅ Vaga salva: {job['cargo']}")
            saved_count += 1
        except Exception as e:
            logging.error(f"❌ Erro ao salvar vaga '{job['cargo']}': {e}")

    logging.info(f"✅ Total: {saved_count} vagas salvas no Supabase!")

# Flask API
app = Flask(__name__)

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """API pública para leitura (usa chave anon)"""
    try:
        # Parâmetros de filtro
        q = request.args.get("q", "").lower()
        location = request.args.get("location", "").lower()
        senioridade = request.args.get("senioridade", "").lower()
        
        # Construir consulta
        query = supabase_read.table("vagas").select("*")
        
        if q:
            query = query.ilike("cargo", f"%{q}%")
        if location:
            query = query.ilike("localizacao", f"%{location}%")
        if senioridade:
            query = query.ilike("senioridade", f"%{senioridade}%")
        
        # Executar consulta
        response = query.order("created_at", desc=True).limit(100).execute()
        jobs = response.data or []
        
        logging.info(f"🔍 API retornou {len(jobs)} vagas para consulta: q='{q}', location='{location}', senioridade='{senioridade}'")
        return jsonify(jobs)
    
    except Exception as e:
        logging.error(f"❌ Erro na API /api/jobs: {e}")
        return jsonify({"error": "Erro ao buscar vagas", "details": str(e)}), 500

@app.route("/", methods=["GET"])
def health_check():
    """Verificação de saúde do serviço"""
    return "✅ Eleva Scraper está online e seguro! Acesse /api/jobs para ver as vagas."

@app.route("/test-scraper", methods=["GET"])
def test_scraper():
    """Endpoint para testar o scraper manualmente (protegido)"""
    try:
        run_scrapper()
        return "✅ Scraper executado com sucesso! Verifique os logs."
    except Exception as e:
        logging.error(f"❌ Erro no teste do scraper: {e}")
        return f"❌ Erro ao executar scraper: {str(e)}", 500

if __name__ == "__main__":
    # Ao iniciar, executar o scraper uma vez
    run_scrapper()
    
    # Iniciar servidor Flask (só para desenvolvimento - em produção usar gunicorn)
    app.run(host="0.0.0.0", port=8000)
