# app.py — Coletor Ético de Vagas Executivas (CTO da Eleva) — COM SUPABASE

import requests
import time
import json
import logging
import os
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import urllib.parse
from supabase import create_client, Client

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 🔑 Carregar variáveis de ambiente
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SERPAPI_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("❌ Variáveis de ambiente não configuradas!")
    exit(1)

# Inicializar cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
            res = requests.get(url, timeout=10)
            
            if res.status_code != 200:
                logging.warning(f"⚠️ SerpAPI erro {res.status_code}: {res.text}")
                continue
                
            data = res.json()
            
            if "organic_results" in data:
                for result in data["organic_results"][:10]:
                    link = result.get("link", "")
                    title = result.get("title", "Vaga executiva")
                    
                    # Evitar links do próprio Google ou vazios
                    if not link or "google.com" in link:
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
                    if any(kw in title.lower() for kw in ["diretor", "head", "c-level", "chief"]):
                        senioridade = "Diretor/Head"
                    elif "gerente" in title.lower():
                        senioridade = "Gerente"
                    elif "coordenador" in title.lower():
                        senioridade = "Coordenador"
                    elif any(kw in title.lower() for kw in ["sênior", "senior", "seniore"]):
                        senioridade = "Sênior"
                    
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
    """Executa a coleta diária e salva no Supabase"""
    logging.info("🚀 Iniciando coleta de vagas executivas...")
    
    # Coletar novas vagas
    new_jobs = scrape_google_jobs("gestão OR negócios OR executivo")
    logging.info(f"📥 Coletadas {len(new_jobs)} vagas novas")

    # Salvar no Supabase
    for job in new_jobs:
        try:
            response = supabase.table("vagas").insert(job).execute()
            logging.info(f"✅ Vaga salva: {job['cargo']}")
        except Exception as e:
            logging.error(f"❌ Erro ao salvar vaga: {e}")

    logging.info(f"✅ Total: {len(new_jobs)} vagas salvas no Supabase!")

# Flask API
app = Flask(__name__)

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    try:
        # Consultar Supabase
        q = request.args.get("q", "").lower()
        location = request.args.get("location", "").lower()
        senioridade = request.args.get("senioridade", "").lower()
        
        query = supabase.table("vagas").select("*")
        
        if q:
            query = query.ilike("cargo", f"%{q}%")
        if location:
            query = query.ilike("localizacao", f"%{location}%")
        if senioridade:
            query = query.ilike("senioridade", f"%{senioridade}%")
        
        response = query.execute()
        jobs = response.data
        
    except Exception as e:
        logging.error(f"Erro ao buscar vagas: {e}")
        jobs = []
    
    return jsonify(jobs[:100])

@app.route("/", methods=["GET"])
def health_check():
    return "✅ Eleva Scraper está online! Acesse /api/jobs para ver as vagas."

if __name__ == "__main__":
    run_scrapper()
    app.run(host="0.0.0.0", port=8000)
