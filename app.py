# app.py — Coletor para Lovable (Executar HOJE)
# Foco: Coletar dados no formato exato que o Lovable precisa para matching perfeito
import requests
from bs4 import BeautifulSoup
import time
import json
import logging
import os
import re
from datetime import datetime, timedelta
import urllib.parse
from supabase import create_client

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 🔑 Carregar variáveis de ambiente
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Verificar variáveis obrigatórias
if not all([SERPAPI_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY]):
    logging.error("❌ Variáveis de ambiente não configuradas!")
    exit(1)

# Conexão com Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ⚙️ Configurações (AJUSTÁVEL)
MAX_VAGAS_TOTAIS = 50  # Limite seguro para MVP
DELAY_ENTRE_REQUISICOES = 3  # segundos

# Funções de normalização (essenciais para o Lovable)
def normalize_title(title: str) -> str:
    title_lower = title.lower()
    replacements = {
        "sr.": "sênior", "jr.": "júnior", "supervisor": "coordenador",
        "tech lead": "líder técnico", "head of": "diretor de"
    }
    for old, new in replacements.items():
        title_lower = title_lower.replace(old, new)
    return re.sub(r'[0-9\(\)\[\]\{\}\<\>\:\;\,\.\!\?\@\#\$\%\^\&\*\_\+\=\\\/]', '', title_lower).strip()

def detect_seniority(text: str, title: str) -> str:
    combined = (title + " " + text).lower()
    if any(kw in combined for kw in ["estágio", "estagiário", "trainee", "aprendiz"]):
        return "estagio"
    if any(kw in combined for kw in ["júnior", "jr", "junior", "assistente"]):
        return "junior"
    if any(kw in combined for kw in ["pleno", "analista", "consultor", "especialista"]):
        return "pleno"
    if any(kw in combined for kw in ["sênior", "sr", "senior", "líder"]):
        return "senior"
    if any(kw in combined for kw in ["gerente", "manager", "coordinator", "supervisor", "head"]):
        return "gerente"
    if any(kw in combined for kw in ["diretor", "director", "vp", "vice-presidente"]):
        return "diretor"
    if any(kw in combined for kw in ["ceo", "cto", "cfo", "chief", "presidente"]):
        return "c_level"
    return "pleno"  # Default seguro

def detect_area(text: str, title: str) -> str:
    combined = (title + " " + text).lower()
    if any(kw in combined for kw in ["venda", "comercial", "comércio", "representante"]):
        return "vendas"
    if any(kw in combined for kw in ["tecnologia", "tech", "software", "desenvolvedor", "dev", "dados"]):
        return "tecnologia"
    if any(kw in combined for kw in ["rh", "recursos humanos", "talentos"]):
        return "recursos_humanos"
    if any(kw in combined for kw in ["financeiro", "contábil", "controladoria"]):
        return "financeiro"
    if any(kw in combined for kw in ["marketing", "comunicação", "mídia"]):
        return "marketing"
    if any(kw in combined for kw in ["produto", "product"]):
        return "produto"
    if any(kw in combined for kw in ["jurídico", "advogado", "direito"]):
        return "juridico"
    return "operacoes"  # Default

def extract_skills(text: str) -> list:
    text_lower = text.lower()
    skills = []
    
    # Dicionário de skills para matching perfeito
    tech_skills = ["python", "javascript", "react", "sql", "aws", "docker", "cloud"]
    management_skills = ["liderança", "gestão", "equipe", "pessoas", "planejamento", "estratégia"]
    
    for skill in tech_skills + management_skills:
        if skill in text_lower:
            skills.append({
                "name": skill.title(),
                "normalized": skill,
                "category": "hard_skills" if skill in tech_skills else "soft_skills",
                "proficiency_level": 3,  # Nível médio
                "is_mandatory": "obrigatório" in text_lower or "requisito" in text_lower,
                "importance_weight": 80
            })
    
    return skills

def is_vaga_brasil(text: str) -> bool:
    text_lower = text.lower()
    palavras_brasil = ["são paulo", "rio de janeiro", "brasília", "brasil", "brazil"]
    palavras_internacionais = ["united states", "london", "germany", "canada"]
    return any(palavra in text_lower for palavra in palavras_brasil) and not any(palavra in text_lower for palavra in palavras_internacionais)

def scrape_job_details(url: str) -> dict:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        time.sleep(DELAY_ENTRE_REQUISICOES)
        res = requests.get(url, headers=headers, timeout=15)
        
        if res.status_code != 200:
            return {"descricao": "Erro ao coletar detalhes", "salario": None, "modalidade": "Não informado"}
        
        soup = BeautifulSoup(res.text, "html.parser")
        descricao = ""
        
        # Buscar descrição completa
        candidates = ["div.description", "div.job-description", "div.content", "article"]
        for selector in candidates:
            elements = soup.select(selector)
            if elements:
                descricao = "\n".join([elem.get_text(strip=True) for elem in elements])
                if len(descricao) > 100:
                    break
        
        if not descricao:
            main = soup.select_one("main, #main, .main")
            descricao = main.get_text(strip=True) if main else "Descrição não disponível"
        
        # Detectar modalidade
        modalidade = "Não informado"
        if "remoto" in descricao.lower():
            modalidade = "remote"
        elif "hibrido" in descricao.lower() or "híbrido" in descricao.lower():
            modalidade = "hybrid"
        elif "presencial" in descricao.lower():
            modalidade = "onsite"
        
        # Detectar salário
        salario = None
        if "r$" in descricao.lower() or "salário" in descricao.lower():
            salario = True
        
        return {
            "descricao": descricao[:1500] + "..." if len(descricao) > 1500 else descricao,
            "salario": salario,
            "modalidade": modalidade
        }
    except Exception as e:
        logging.error(f"Erro ao coletar detalhes de {url}: {e}")
        return {"descricao": f"Erro: {str(e)}", "salario": None, "modalidade": "Não informado"}

def scrape_google_jobs() -> list:
    all_jobs = []
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Fontes estratégicas (foco Brasil)
    sources = [
        "site:vagas.com.br",
        "site:linkedin.com/jobs brasil OR brazil",
        "site:gupy.com.br",
        "site:trampos.co",
        "site:talenses.com/pt/vagas brasil OR brazil"
    ]
    
    for source in sources:
        if len(all_jobs) >= MAX_VAGAS_TOTAIS:
            break
        
        search_query = f'diretor OR gerente OR head OR líder OR executivo OR supervisor OR coordenador {source} after:{yesterday}'
        logging.info(f"🔍 Buscando: {search_query}")
        
        try:
            url = f"https://serpapi.com/search.json?q={urllib.parse.quote(search_query)}&hl=pt-BR&num=20&api_key={SERPAPI_KEY}"
            res = requests.get(url, timeout=15)
            data = res.json()
            
            if "organic_results" not in 
                continue
            
            for result in data["organic_results"][:10]:
                if len(all_jobs) >= MAX_VAGAS_TOTAIS:
                    break
                
                link = result.get("link", "")
                title = result.get("title", "Vaga sem título")
                snippet = result.get("snippet", "")
                
                if not link or "google.com" in link or len(link) < 10:
                    continue
                
                # Filtro geográfico rigoroso
                if not is_vaga_brasil(title + " " + snippet):
                    continue
                
                # Coletar detalhes
                details = scrape_job_details(link)
                
                # Processar para formato Lovable
                job_record = {
                    "external_id": f"{hash(link)}",
                    "source": source.split("site:")[1].split(" ")[0],
                    "source_url": link,
                    "posted_at": f"{yesterday}T00:00:00Z",
                    "posted_days_ago": 1,
                    "title": title[:100],
                    "title_normalized": normalize_title(title),
                    "seniority_level": detect_seniority(details["descricao"], title),
                    "area": detect_area(details["descricao"], title),
                    "company_name": "Empresa não informada",
                    "company_name_normalized": "empresa_nao_informada",
                    "is_headhunter": "talenses" in source or "linkedin" in source,
                    "city": "São Paulo",  # Ajustar depois
                    "state": "SP",       # Ajustar depois
                    "work_model": details["modalidade"],
                    "is_remote_eligible": "remoto" in details["modalidade"].lower(),
                    "salary_min": None,
                    "salary_max": None,
                    "salary_disclosed": details["salario"],
                    "benefits": {},
                    "skills_required": extract_skills(details["descricao"]),
                    "experience_years_min": 3 if "3+ anos" in details["descricao"].lower() else 5 if "5+ anos" in details["descricao"].lower() else 2,
                    "education_required": [],
                    "languages_required": [],
                    "description": details["descricao"],
                    "culture_keywords": ["resultados", "colaboração", "inovação"],
                    "quality_score": 0.8
                }
                
                all_jobs.append(job_record)
                logging.info(f"✅ Coletada: {title[:50]}... ({job_record['seniority_level']})")
                time.sleep(2)
        
        except Exception as e:
            logging.error(f"Erro na busca: {e}")
            time.sleep(5)
    
    return all_jobs

def save_to_supabase(jobs: list):
    logging.info(f"💾 Salvando {len(jobs)} vagas no Supabase...")
    for job in jobs:
        try:
            supabase.table("vagas_lovable").insert(job).execute()
        except Exception as e:
            logging.error(f"Erro ao salvar vaga: {e}")

def run_scrapper():
    logging.info("🚀 INICIANDO COLETA PARA LOVABLE")
    jobs = scrape_google_jobs()
    if jobs:
        save_to_supabase(jobs)
    logging.info(f"✅ COLETA FINALIZADA: {len(jobs)} vagas salvas para o Lovable")

if __name__ == "__main__":
    run_scrapper()
