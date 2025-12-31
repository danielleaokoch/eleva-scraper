# app.py — Coletor Ético de Vagas Executivas (CTO da Eleva) — CORRIGIDO PARA GOOGLE

import requests
from bs4 import BeautifulSoup
import time
import json
import logging
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import urllib.parse

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_google_jobs(query, days_back=1):
    """Busca vagas no Google usando site: e data"""
    all_jobs = []
    yesterday = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Fontes seguras para buscar via Google (incluindo LinkedIn e Gupy)
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
        logging.info(f"🔍 Buscando no Google: {search_query}")
        
        try:
            # Usar User-Agent mais humano
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
            }
            
            # Construir URL de busca
            url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&hl=pt-BR&num=10"
            
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            
            # Procurar por resultados (Google mudou a estrutura — usar .g ou .yuRUbf)
            results = soup.select("div.g") or soup.select("div.yuRUbf")
            
            for result in results[:10]:  # limite seguro
                link_elem = result.select_one("a")
                if link_elem:
                    href = link_elem.get("href")
                    if href and "url?" not in href and "google" not in href:
                        # Extrair título
                        title_elem = result.select_one("h3")
                        title = title_elem.text if title_elem else "Vaga executiva"
                        
                        # Detectar fonte
                        fonte = "Google"
                        if "linkedin.com/jobs" in href:
                            fonte = "LinkedIn"
                        elif "gupy.com.br" in href:
                            fonte = "Gupy"
                        elif "vagas.com.br" in href:
                            fonte = "Vagas.com.br"
                        elif "trampos.co" in href:
                            fonte = "Trampos.co"
                        elif "ciadetalentos.com.br" in href:
                            fonte = "Cia de Talentos"
                        elif "glassdoor.com.br" in href:
                            fonte = "Glassdoor"
                        elif "indeed.com" in href:
                            fonte = "Indeed"
                        
                        # Detectar senioridade
                        senioridade = "Sênior+"
                        if "diretor" in title.lower() or "head" in title.lower():
                            senioridade = "Diretor/Head"
                        elif "gerente" in title.lower():
                            senioridade = "Gerente"
                        elif "coordenador" in title.lower():
                            senioridade = "Coordenador"
                        
                        all_jobs.append({
                            "cargo": title,
                            "empresa": "Não informado",
                            "salario": "Não informado",
                            "modalidade": "Não informado",
                            "data_publicacao": yesterday,
                            "localizacao": "Brasil",
                            "senioridade": senioridade,
                            "requisitos": [],
                            "experiencias": [],
                            "link_candidatura": href,
                            "fonte": fonte
                        })
            time.sleep(10)  # respeitar Google
        except Exception as e:
            logging.error(f"Erro Google: {e}")
    return all_jobs

def run_scrapper():
    """Executa a coleta diária de vagas executivas"""
    logging.info("🚀 Iniciando coleta de vagas executivas...")
    all_jobs = []
    
    # Google Jobs (vagas publicadas ontem)
    google_jobs = scrape_google_jobs("gestão OR negócios OR executivo")
    logging.info(f"✅ Google: {len(google_jobs)} vagas")
    all_jobs.extend(google_jobs)
    
    # Remover duplicatas
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        if job["link_candidatura"] not in seen:
            seen.add(job["link_candidatura"])
            unique_jobs.append(job)
    
    # Salvar
    with open("vagas_executivas.json", "w", encoding="utf-8") as f:
        json.dump(unique_jobs, f, ensure_ascii=False, indent=2)
    
    logging.info(f"✅ Total: {len(unique_jobs)} vagas únicas salvas!")

# Flask API
app = Flask(__name__)

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    try:
        with open("vagas_executivas.json", "r", encoding="utf-8") as f:
            jobs = json.load(f)
    except:
        jobs = []
    
    # Filtros
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

if __name__ == "__main__":
    run_scrapper()
    app.run(host="0.0.0.0", port=8000)
