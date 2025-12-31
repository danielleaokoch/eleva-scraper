# app.py — Coletor Ético de Vagas Executivas (CTO da Eleva)

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
    
    # Fontes seguras para buscar via Google
    sources = [
        "site:br.indeed.com",
        "site:glassdoor.com.br",
        "site:vagas.com.br",
        "site:trampos.co",
        "site:ciadetalentos.com.br"
    ]
    
    for source in sources:
        search_query = f'{query} {source} after:{yesterday}'
        logging.info(f"Buscando no Google: {search_query}")
        
        try:
            url = f"https://www.google.com/search?q={urllib.parse.quote(search_query)}&hl=pt-BR"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            
            for g in soup.select("div.g"):
                link_elem = g.select_one("a")
                if link_elem:
                    href = link_elem.get("href")
                    if href and "url?" not in href:
                        # Extrair só o título (simulando preview)
                        title_elem = g.select_one("h3")
                        title = title_elem.text if title_elem else "Vaga executiva"
                        all_jobs.append({
                            "cargo": title,
                            "empresa": "Não informado",
                            "salario": "Não informado",
                            "modalidade": "Não informado",
                            "data_publicacao": yesterday,
                            "localizacao": "Brasil",
                            "senioridade": "Sênior+",
                            "requisitos": [],
                            "experiencias": [],
                            "link_candidatura": href,
                            "fonte": source.replace("site:", "").replace(".com.br", "").replace(".com", "")
                        })
                        if len(all_jobs) >= 100:  # limite seguro
                            break
            time.sleep(10)  # respeitar Google
        except Exception as e:
            logging.error(f"Erro Google: {e}")
    return all_jobs

def scrape_indeed_executivo():
    """Coleta vagas executivas do Indeed Brasil"""
    jobs = []
    query = "gerente OR diretor OR head OR líder OR executivo"
    url = f"https://br.indeed.com/jobs?q={urllib.parse.quote(query)}&l=Brasil"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        for div in soup.select("div.job_seen_beacon")[:30]:
            title_elem = div.select_one("h2 a")
            title = title_elem.get("title") if title_elem else "Não informado"
            
            company_elem = div.select_one("span.companyName")
            company = company_elem.text.strip() if company_elem else "Não informado"
            
            loc_elem = div.select_one("div.companyLocation")
            loc = loc_elem.text.strip() if loc_elem else "Brasil"
            
            link = "https://br.indeed.com" + (title_elem.get("href") if title_elem else "")
            
            # Detectar senioridade
            senioridade = "Sênior"
            if "diretor" in title.lower() or "head" in title.lower():
                senioridade = "Diretor/Head"
            elif "gerente" in title.lower():
                senioridade = "Gerente"
            
            jobs.append({
                "cargo": title,
                "empresa": company,
                "salario": "Não informado",
                "modalidade": "Não informado",
                "data_publicacao": datetime.now().strftime("%Y-%m-%d"),
                "localizacao": loc,
                "senioridade": senioridade,
                "requisitos": [],
                "experiencias": [],
                "link_candidatura": link,
                "fonte": "Indeed"
            })
            time.sleep(3)
    except Exception as e:
        logging.error(f"Erro Indeed executivo: {e}")
    return jobs

def run_scrapper():
    """Executa a coleta diária de vagas executivas"""
    logging.info("🚀 Iniciando coleta de vagas executivas...")
    all_jobs = []
    
    # Google Jobs (vagas publicadas ontem)
    google_jobs = scrape_google_jobs("gestão OR negócios OR executivo")
    logging.info(f"✅ Google: {len(google_jobs)} vagas")
    all_jobs.extend(google_jobs)
    
    # Indeed Executivo
    indeed_jobs = scrape_indeed_executivo()
    logging.info(f"✅ Indeed: {len(indeed_jobs)} vagas")
    all_jobs.extend(indeed_jobs)
    
    # Remover duplicatas (por link)
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
