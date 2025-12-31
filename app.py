# app.py — Coletor Ético de Vagas Executivas (CTO da Eleva) — CORRIGIDO E TESTADO

import requests
import time
import json
import logging
import os
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import urllib.parse

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 🔑 Carregar API Key do SerpAPI das variáveis de ambiente
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
if not SERPAPI_KEY:
    logging.error("❌ SERPAPI_KEY não configurada! Adicione nas variáveis de ambiente do Railway.")
    SERPAPI_KEY = "sua_chave_aqui"  # fallback (mas não funcionará)

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
                        "fonte": fonte
                    })
            else:
                logging.warning(f"⚠️ Nenhum resultado em 'organic_results' para: {search_query}")
            
            time.sleep(2)  # respeitar rate limit do SerpAPI (0.5 requisições/segundo)
            
        except Exception as e:
            logging.error(f"❌ Erro SerpAPI: {e}")
    
    return all_jobs

def run_scrapper():
    """Executa a coleta diária de vagas executivas"""
    logging.info("🚀 Iniciando coleta de vagas executivas...")
    all_jobs = []
    
    # Google Jobs (vagas publicadas ontem)
    google_jobs = scrape_google_jobs("gestão OR negócios OR executivo")
    logging.info(f"✅ Google: {len(google_jobs)} vagas coletadas")
    all_jobs.extend(google_jobs)
    
    # Remover duplicatas (por link)
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        link = job["link_candidatura"]
        if link not in seen:
            seen.add(link)
            unique_jobs.append(job)
    
    # Salvar em arquivo
    with open("vagas_executivas.json", "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, ensure_ascii=False, indent=2)
    
    logging.info(f"✅ Total: {len(unique_jobs)} vagas únicas salvas em vagas_executivas.json!")

# Flask API
app = Flask(__name__)

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    try:
        with open("vagas_executivas.json", "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except Exception as e:
        logging.error(f"Erro ao carregar vagas: {e}")
        jobs = []
    
    # Filtros via query params
    q = request.args.get("q", "").lower()
    location = request.args.get("location", "").lower()
    senioridade = request.args.get("senioridade", "").lower()
    
    filtered = []
    for job in jobs:
        if q and q not in job["cargo"].lower():
            continue
        if location and location not in job["localizacao"].lower():
            continue
        if senioridade and senioridade not in job["senioridade"].lower():
            continue
        filtered.append(job)
    
    return jsonify(filtered[:100])

@app.route("/", methods=["GET"])
def health_check():
    return "✅ Eleva Scraper está online! Acesse /api/jobs para ver as vagas."

if __name__ == "__main__":
    run_scrapper()
    app.run(host="0.0.0.0", port=8000)
