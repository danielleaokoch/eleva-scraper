# app.py — Versão RICA para coleta de vagas (CTO da Eleva)

import requests
from bs4 import BeautifulSoup
import time
import json
import logging
import os
from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import urllib.parse
from supabase import create_client
import re
from collections import Counter
import spacy  # Para NLP (instale com: pip install spacy && python -m spacy download pt_core_news_sm)

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar modelo NLP (português)
try:
    NLP_MODEL = spacy.load("pt_core_news_sm")
except Exception as e:
    logging.warning(f"⚠️ Modelo NLP não carregado: {e}. Fallback para extração simples.")
    NLP_MODEL = None

# 🔑 Carregar variáveis de ambiente
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Verificar variáveis obrigatórias
required_vars = [SERPAPI_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY]
if not all(required_vars):
    logging.error("❌ Variáveis de ambiente não configuradas!")
    exit(1)

# Criar clientes Supabase
supabase_read = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_write = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def extract_keywords(text):
    """Extrai palavras-chave usando NLP ou fallback simples"""
    if not text or not isinstance(text, str):
        return []
    
    if NLP_MODEL:
        # Usar spaCy para extrair entidades e substantivos
        doc = NLP_MODEL(text.lower())
        keywords = [
            token.text for token in doc
            if token.pos_ in ["NOUN", "PROPN", "VERB"] 
            and len(token.text) > 2
            and not token.is_stop
        ]
        return list(set(keywords))[:20]  # Máximo 20 palavras-chave
    else:
        # Fallback simples: palavras comuns em vagas
        common_skills = [
            "python", "javascript", "react", "sql", "aws", "docker", "kubernetes",
            "gestão", "liderança", "comunicação", "inglês", "excel", "powerpoint",
            "planejamento", "análise", "resolução", "problemas", "criatividade"
        ]
        return [skill for skill in common_skills if skill in text.lower()]

def scrape_job_details(url, fonte):
    """Scrape profundo da página individual da vaga"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        # Diferentes estratégias por fonte
        if "linkedin.com/jobs" in url:
            return scrape_linkedin_job(url, headers)
        elif "gupy.com.br" in url:
            return scrape_gupy_job(url, headers)
        elif "talenses.com" in url:
            return scrape_talenses_job(url, headers)
        else:
            return scrape_generic_job(url, headers)
            
    except Exception as e:
        logging.error(f"❌ Erro ao coletar detalhes da vaga {url}: {e}")
        return {
            "descricao_completa": "Não foi possível coletar detalhes",
            "requisitos": [],
            "beneficios": [],
            "habilidades_extraidas": [],
            "salario": "Não informado",
            "modalidade": "Não informado"
        }

def scrape_linkedin_job(url, headers):
    """Estratégia específica para LinkedIn Jobs"""
    res = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Seletores específicos do LinkedIn
    descricao_div = soup.select_one("div.description__text")
    descricao = descricao_div.get_text(strip=True) if descricao_div else "Descrição não disponível"
    
    # Extrair requisitos (seções comuns no LinkedIn)
    requisitos = []
    sections = soup.select("section")
    for section in sections:
        if "Requisitos" in section.get_text() or "Requirements" in section.get_text():
            requisitos = [li.get_text(strip=True) for li in section.select("li")]
    
    # Salário (se disponível)
    salario_elem = soup.select_one("span.salary")
    salario = salario_elem.get_text(strip=True) if salario_elem else "Não informado"
    
    return {
        "descricao_completa": descricao,
        "requisitos": requisitos,
        "beneficios": [],
        "habilidades_extraidas": extract_keywords(descricao),
        "salario": salario,
        "modalidade": "Não informado"
    }

def scrape_talenses_job(url, headers):
    """Estratégia para o site Talenses"""
    # Primeiro, obter a lista de vagas
    res = requests.get("https://talenses.com/jobs", headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Encontrar todas as vagas
    jobs = []
    job_cards = soup.select("div.job-posting")  # Ajuste conforme estrutura real do site
    
    for card in job_cards:
        title_elem = card.select_one("h3")
        link_elem = card.select_one("a")
        
        if title_elem and link_elem:
            jobs.append({
                "cargo": title_elem.get_text(strip=True),
                "link_candidatura": urllib.parse.urljoin("https://talenses.com", link_elem.get("href", "")),
                "empresa": "Talenses",
                "fonte": "Talenses",
                "localizacao": "Brasil",  # Ajustar conforme necessário
                "data_publicacao": datetime.now().strftime("%Y-%m-%d"),
                "senioridade": "Não informado"  # Pode inferir do título
            })
    
    return jobs

def scrape_generic_job(url, headers):
    """Fallback para sites genéricos"""
    res = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    
    # Buscar por divs comuns que contêm descrição
    content_divs = soup.select("div.description, div.job-description, div.content, article")
    descricao = "Descrição não disponível"
    
    for div in content_divs:
        text = div.get_text(strip=True)
        if len(text) > 100:  # Assumir que é a descrição principal
            descricao = text
            break
    
    # Tentar extrair requisitos
    requisitos = []
    if "requisitos" in descricao.lower():
        parts = descricao.lower().split("requisitos")
        if len(parts) > 1:
            requisitos_text = parts[1].split("benefícios")[0] if "benefícios" in parts[1] else parts[1]
            requisitos = [r.strip() for r in requisitos_text.split("\n") if len(r.strip()) > 5][:5]
    
    return {
        "descricao_completa": descricao,
        "requisitos": requisitos,
        "beneficios": [],
        "habilidades_extraidas": extract_keywords(descricao),
        "salario": "Não informado",
        "modalidade": "Não informado"
    }

def scrape_google_jobs(query, days_back=1, max_results=50):
    """Busca vagas no Google usando SerpAPI com scraping profundo"""
    all_jobs = []
    yesterday = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    sources = [
        "site:linkedin.com/jobs",
        "site:gupy.com.br",
        "site:vagas.com.br",
        "site:trampos.co",
        "site:ciadetalentos.com.br",
        "site:glassdoor.com.br",
        "site:br.indeed.com",
        "site:talenses.com/jobs"  # Adicionado Talenses
    ]
    
    for source in sources:
        search_query = f'{query} {source} after:{yesterday}'
        logging.info(f"🔍 Buscando no Google (via SerpAPI): {search_query}")
        
        try:
            url = f"https://serpapi.com/search.json?q={urllib.parse.quote(search_query)}&hl=pt-BR&api_key={SERPAPI_KEY}"
            res = requests.get(url, timeout=10)
            data = res.json()
            
            if "organic_results" in 
                for result in data["organic_results"][:10]:
                    link = result.get("link", "")
                    title = result.get("title", "Vaga executiva")
                    
                    if not link or "google.com" in link:
                        continue
                    
                    # Detectar fonte
                    fonte = "Google"
                    if "linkedin.com/jobs" in link:
                        fonte = "LinkedIn"
                    elif "gupy.com.br" in link:
                        fonte = "Gupy"
                    elif "talenses.com" in link:
                        fonte = "Talenses"
                    
                    # Fazer scraping profundo da página da vaga
                    details = scrape_job_details(link, fonte)
                    
                    # Detectar senioridade (melhorado)
                    senioridade = "Sênior+"
                    title_lower = title.lower()
                    if any(kw in title_lower for kw in ["diretor", "head", "c-level", "chief"]):
                        senioridade = "Diretor/Head"
                    elif "gerente" in title_lower:
                        senioridade = "Gerente"
                    elif "coordenador" in title_lower:
                        senioridade = "Coordenador"
                    elif any(kw in title_lower for kw in ["sênior", "senior"]):
                        senioridade = "Sênior"
                    elif any(kw in title_lower for kw in ["júnior", "junior", "jr"]):
                        senioridade = "Júnior"
                    elif "pleno" in title_lower:
                        senioridade = "Pleno"
                    
                    all_jobs.append({
                        "cargo": title.strip(),
                        "empresa": "Não informado",
                        "salario": details["salario"],
                        "modalidade": details["modalidade"],
                        "data_publicacao": yesterday,
                        "localizacao": "Brasil",
                        "senioridade": senioridade,
                        "requisitos": json.dumps(details["requisitos"]),  # Armazenar como JSON
                        "experiencias": json.dumps(details["habilidades_extraidas"]),  # Palavras-chave
                        "descricao_completa": details["descricao_completa"],  # Dado RICO
                        "beneficios": json.dumps(details["beneficios"]),
                        "habilidades_extraidas": json.dumps(details["habilidades_extraidas"]),
                        "link_candidatura": link,
                        "fonte": fonte,
                        "created_at": datetime.now().isoformat()
                    })
                    
                    # Respeitar o site
                    time.sleep(3)
                    
                    if len(all_jobs) >= max_results:
                        break
            
            time.sleep(2)
            
        except Exception as e:
            logging.error(f"❌ Erro SerpAPI ou scraping: {e}")
    
    return all_jobs

def scrape_talenses_direct():
    """Coleta direta do site Talenses (exemplo prático)"""
    logging.info("🔍 Coletando vagas diretamente do Talenses")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    try:
        # Acessar a página de vagas
        url = "https://talenses.com/jobs"
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code != 200:
            logging.warning(f"⚠️ Talenses retornou status {res.status_code}")
            return []
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Estratégia para o Talenses (ajustar conforme estrutura real)
        jobs = []
        job_elements = soup.select(".job-listing, .vacancy, .job-post")  # Ajustar seletores
        
        for elem in job_elements[:20]:  # Limite de segurança
            title_elem = elem.select_one("h2, h3, .title")
            link_elem = elem.select_one("a")
            
            if title_elem and link_elem:
                title = title_elem.get_text(strip=True)
                link = urllib.parse.urljoin("https://talenses.com", link_elem.get("href", ""))
                
                # Coletar detalhes da vaga individual
                details = scrape_job_details(link, "Talenses")
                
                jobs.append({
                    "cargo": title,
                    "empresa": "Talenses",
                    "fonte": "Talenses (coleta direta)",
                    "localizacao": "Brasil",
                    "link_candidatura": link,
                    "data_publicacao": datetime.now().strftime("%Y-%m-%d"),
                    "descricao_completa": details["descricao_completa"],
                    "requisitos": json.dumps(details["requisitos"]),
                    "habilidades_extraidas": json.dumps(details["habilidades_extraidas"]),
                    "created_at": datetime.now().isoformat()
                })
                time.sleep(2)  # Respeitar o site
        
        logging.info(f"✅ Coletadas {len(jobs)} vagas do Talenses")
        return jobs
    
    except Exception as e:
        logging.error(f"❌ Erro ao coletar do Talenses: {e}")
        return []

def run_scrapper():
    """Executa coleta RICA de vagas"""
    logging.info("🚀 Iniciando coleta RICA de vagas executivas...")
    
    all_jobs = []
    
    # 1. Google Jobs (agora com scraping profundo)
    google_jobs = scrape_google_jobs("gestão OR negócios OR executivo OR diretor OR gerente", days_back=2, max_results=30)
    logging.info(f"✅ Google: {len(google_jobs)} vagas RICAS coletadas")
    all_jobs.extend(google_jobs)
    
    # 2. Coleta direta do Talenses (exemplo solicitado)
    talenses_jobs = scrape_talenses_direct()
    all_jobs.extend(talenses_jobs)
    
    # 3. Outras fontes (exemplo: Vagas.com.br direto)
    # ... (pode adicionar mais fontes específicas)
    
    # Salvar no Supabase
    saved_count = 0
    for job in all_jobs:
        try:
            supabase_write.table("vagas").insert(job).execute()
            logging.info(f"✅ Vaga RICA salva: {job['cargo'][:50]}...")
            saved_count += 1
        except Exception as e:
            logging.error(f"❌ Erro ao salvar vaga RICA '{job['cargo']}': {e}")
    
    logging.info(f"✅ Total: {saved_count} vagas RICAS salvas no Supabase!")
    return saved_count

# Flask API (mantida, mas agora com dados RICOS)
app = Flask(__name__)

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    try:
        q = request.args.get("q", "").lower()
        location = request.args.get("location", "").lower()
        senioridade = request.args.get("senioridade", "").lower()
        
        query = supabase_read.table("vagas").select("*")
        
        if q:
            query = query.or_("cargo.ilike.%{0}%,descricao_completa.ilike.%{0}%".format(q))
        if location:
            query = query.ilike("localizacao", f"%{location}%")
        if senioridade:
            query = query.ilike("senioridade", f"%{senioridade}%")
        
        response = query.order("created_at", desc=True).limit(100).execute()
        jobs = response.data or []
        return jsonify(jobs)
    
    except Exception as e:
        logging.error(f"❌ Erro na API /api/jobs: {e}")
        return jsonify({"error": "Erro ao buscar vagas"}), 500

@app.route("/api/enrich-job", methods=["POST"])
def enrich_job():
    """Endpoint para enriquecer uma vaga com IA (Gemini)"""
    try:
        data = request.json
        descricao = data.get("descricao", "")
        
        if not descricao:
            return jsonify({"error": "Descrição vazia"}), 400
        
        # Aqui integraria com o Gemini para extrair skills, senioridade, etc.
        # Exemplo simulado:
        habilidades = extract_keywords(descricao)
        senioridade = "Sênior" if "sênior" in descricao.lower() or "5+ anos" in descricao.lower() else "Pleno"
        
        return jsonify({
            "habilidades_extraidas": habilidades,
            "senioridade_sugerida": senioridade,
            "match_score": 0.85  # Simulado
        })
    
    except Exception as e:
        logging.error(f"❌ Erro no enriquecimento: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    run_scrapper()
    app.run(host="0.0.0.0", port=8000)
