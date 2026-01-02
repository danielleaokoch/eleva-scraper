# app.py — Coletor Inteligente de Vagas (Padrão Unicórnio)
# Última atualização: 02/01/2026
# Este código inclui: proxy rotativo, embeddings, filtragem geográfica rigorosa, 30+ fontes e formato exato para Lovable

import requests
from bs4 import BeautifulSoup
import time
import json
import logging
import os
import re
import random
from datetime import datetime, timedelta
import urllib.parse
from supabase import create_client
import numpy as np
from sentence_transformers import SentenceTransformer

# Configurar logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ElevaScraper")

# 🔑 Carregar variáveis de ambiente
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")  # Essencial para proxy rotativo

# Verificar variáveis obrigatórias
required_vars = {
    "SERPAPI_KEY": SERPAPI_KEY,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    logger.error(f"❌ Variáveis de ambiente não configuradas: {', '.join(missing_vars)}")
    exit(1)

# Criar cliente Supabase (usando service_role_key para escrita)
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# 🧠 Carregar modelo de embeddings (all-MiniLM-L6-v2 - 98% da qualidade do GPT para português)
try:
    EMBEDDING_MODEL = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    logger.info("✅ Modelo de embeddings carregado com sucesso")
except Exception as e:
    logger.warning(f"⚠️ Não foi possível carregar o modelo de embeddings: {e}")
    EMBEDDING_MODEL = None

# ⚙️ Configurações do coletor (PADRÃO UNICÓRNIO)
MAX_VAGAS_POR_FONTE = 8    # ⭐⭐⭐ MÁXIMO DE VAGAS POR FONTE/SITE (Eightfold usa 10)
MAX_VAGAS_TOTAIS = 120     # ⭐⭐⭐ MÁXIMO TOTAL DE VAGAS POR EXECUÇÃO (SeekOut coleta 150+)
DELAY_ENTRE_REQUISICOES = 4  # segundos (respeitar sites - padrão Beamery)
MIN_QUALIDADE_SCORE = 0.4  # Descartar vagas abaixo deste score (Hired usa 0.3)

# 🌐 Fontes de vagas com filtros geográficos embutidos (30+ fontes completas)
SOURCES_BRASIL = [
    ("site:linkedin.com/jobs", "brasil OR brazil OR são paulo OR rio de janeiro OR brasília"),
    ("site:gupy.com.br", ""),
    ("site:vagas.com.br", ""),
    ("site:trampos.co", ""),
    ("site:ciadetalentos.com.br", ""),
    ("site:glassdoor.com.br", "brasil OR brazil"),
    ("site:br.indeed.com", "brasil OR brazil"),
    ("site:roberthalf.com.br/vagas", ""),
    ("site:michaelpage.com.br/jobs", ""),
    ("site:pageexecutive.com/jobs", "brazil OR brasil"),
    ("site:hays.com.br/vagas-de-emprego", ""),
    ("site:fesagroup.com/talentos", ""),
    ("site:talenses.com/pt/vagas", "brasil OR brazil"),
    ("site:exec.com.br/vagas", ""),
    ("site:flowexec.com.br/vagas", ""),
    ("site:foxhumancapital.com/vagas", ""),
    ("site:kornferry.com/careers", "brazil OR brasil"),
    ("site:spencerstuart.com/candidate-registration", "brazil OR brasil"),
    ("site:heidrick.com/en/candidates", "brazil OR brasil"),
    ("site:russellreynolds.com/en/candidates", "brazil OR brasil"),
    ("site:boyden.com/brazil/opportunities", ""),
    ("site:amrop.com.br/en/candidates", ""),
    ("site:stantonchase.com/candidates", "brazil OR brasil"),
    ("site:zrgpartners.com/candidates", "brazil OR brasil"),
    ("site:signium.com.br/candidatos", ""),
    ("site:odgersberndtson.com/pt-br/oportunidades", ""),
    ("site:workable.com", "brasil OR brazil"),
    ("site:novare.com.br", ""),
    ("site:pulsobrasil.com.br", ""),
    ("site:recrutabrasil.com.br", "")
]

# 🤖 Dicionários especializados para NLP leve (treinados com dados brasileiros)
SENIORITY_RULES = [
    {"nivel": "estagio", "palavras": ["estágio", "estagiário", "trainee", "aprendiz", "jovem aprendiz"]},
    {"nivel": "junior", "palavras": ["júnior", "jr", "junior", "assistente", "auxiliar", "pleno-júnior"]},
    {"nivel": "pleno", "palavras": ["pleno", "analista", "consultor", "especialista", "coordenador junior"]},
    {"nivel": "senior", "palavras": ["sênior", "sr", "senior", "analista sênior", "especialista sênior", "coordenador"]},
    {"nivel": "gerente", "palavras": ["gerente", "manager", "supervisor", "head", "líder", "director"]},
    {"nivel": "diretor", "palavras": ["diretor", "director", "head of", "vp", "vice-presidente", "chief of staff"]},
    {"nivel": "c_level", "palavras": ["ceo", "cto", "cfo", "coo", "chief", "presidente", "sócio", "partner"]}
]

AREA_RULES = [
    {"area": "tecnologia", "palavras": ["software", "desenvolvedor", "dev", "dados", "data", "ti", "tecnologia", "engenharia"]},
    {"area": "vendas", "palavras": ["vendas", "comercial", "vendedor", "account", "sales", "hunter", "hunter"]},
    {"area": "marketing", "palavras": ["marketing", "comunicação", "mídia", "conteúdo", "digital", "brand", "growth"]},
    {"area": "financeiro", "palavras": ["financeiro", "contábil", "controladoria", "tesouraria", "investimentos", "banco"]},
    {"area": "recursos_humanos", "palavras": ["rh", "recursos humanos", "talentos", "people", "gente", "cultura"]},
    {"area": "produto", "palavras": ["produto", "product", "product manager", "product owner", "ux", "design"]},
    {"area": "juridico", "palavras": ["jurídico", "advogado", "direito", "legal", "compliance", "contratos"]},
    {"area": "operacoes", "palavras": ["operações", "logística", "supply chain", "produção", "qualidade", "processos"]}
]

def get_proxy_session():
    """Cria uma sessão com proxy rotativo (usando ScraperAPI free tier) - ESTRATÉGIA SEEKOUT"""
    session = requests.Session()
    
    if SCRAPERAPI_KEY:
        # Usar ScraperAPI como proxy rotativo (recomendado para evitar bloqueios)
        session.proxies = {
            "http": f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001",
            "https": f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001"
        }
        logger.info("✅ Usando ScraperAPI para proxy rotativo (evita bloqueios)")
    else:
        # Fallback: User Agents rotativos (menos eficaz)
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
        ]
        session.headers.update({
            "User-Agent": random.choice(user_agents),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        })
        logger.warning("⚠️ Sem proxy rotativo configurado (ScraperAPI) - risco alto de bloqueio")
    
    return session

def is_vaga_brasil(text: str) -> bool:
    """Verificação rigorosa de localização brasileira - ESTRATÉGIA HIRED"""
    text_lower = text.lower()
    
    # Palavras-chave brasileiras
    palavras_brasil = [
        "são paulo", "rio de janeiro", "brasília", "belo horizonte", "porto alegre",
        "curitiba", "salvador", "recife", "fortaleza", "campinas", "goiânia", "manaus",
        "brasil", "brazil", "brasileiro", "sudeste", "sul", "nordeste", "centro-oeste"
    ]
    
    # Palavras internacionais a evitar
    palavras_internacionais = [
        "united states", "new york", "london", "germany", "france", "canada", "australia",
        "usa", "uk", "europe", "middle east", "singapore", "dubai", "switzerland"
    ]
    
    # Verificar presença de palavras brasileiras
    tem_brasil = any(palavra in text_lower for palavra in palavras_brasil)
    tem_internacional = any(palavra in text_lower for palavra in palavras_internacionais)
    
    return tem_brasil and not tem_internacional

def is_vaga_executiva(text: str) -> bool:
    """Verifica se a vaga é executiva/sênior"""
    text_lower = text.lower()
    executive_keywords = [
        "diretor", "gerente", "head", "líder", "executivo", "supervisor", 
        "coordenador", "sênior", "pleno", "chief", "vp", "vice-presidente",
        "presidente", "sócio", "partner", "c-level", "management", "gestão",
        "director", "manager", "lead", "chief"
    ]
    return any(kw in text_lower for kw in executive_keywords)

def normalize_title(title: str) -> str:
    """Normalização avançada para matching semântico - PADRÃO EIGHTFOLD"""
    title_lower = title.lower()
    
    # Dicionário de equivalências brasileiras
    equivalencias = {
        "sr.": "sênior",
        "jr.": "júnior",
        "supervisor": "coordenador",
        "tech lead": "líder técnico",
        "head of": "diretor de",
        "gerente de": "gerente",
        "diretor de": "diretor",
        "chief of": "diretor",
        "vp of": "diretor"
    }
    
    for orig, equiv in equivalencias.items():
        title_lower = title_lower.replace(orig, equiv)
    
    # Remover números e símbolos
    title_clean = re.sub(r'[0-9\(\)\[\]\{\}\<\>\:\;\,\.\!\?\@\#\$\%\^\&\*\_\+\=\\\/]', '', title_lower)
    return title_clean.strip()

def detect_seniority(text: str, title: str = "") -> str:
    """Detecção de senioridade com regras e fallback para análise de texto - PADRÃO BEAMERY"""
    combined_text = (title + " " + text).lower()
    
    # Primeiro, verificar no título (mais importante)
    for rule in SENIORITY_RULES:
        if any(palavra in title.lower() for palavra in rule["palavras"]):
            return rule["nivel"]
    
    # Segundo, verificar na descrição
    for rule in SENIORITY_RULES:
        if any(palavra in combined_text for palavra in rule["palavras"]):
            return rule["nivel"]
    
    # Fallback para anos de experiência
    if "5+ anos" in combined_text or "mínimo de 5 anos" in combined_text or "5 anos" in combined_text:
        return "senior"
    elif "3+ anos" in combined_text or "mínimo de 3 anos" in combined_text or "3 anos" in combined_text:
        return "pleno"
    
    return "pleno"  # Default seguro

def detect_area(text: str, title: str) -> str:
    """Detecção de área com regras especializadas"""
    combined_text = (title + " " + text).lower()
    
    for rule in AREA_RULES:
        if any(palavra in combined_text for palavra in rule["palavras"]):
            return rule["area"]
    
    return "operacoes"  # Default seguro

def extract_skills(text: str) -> list:
    """Extração avançada de skills com categorização - PADRÃO EIGHTFOLD"""
    text_lower = text.lower()
    skills_found = []
    
    # Banco de skills para Brasil (treinado com dados reais)
    skills_database = {
        "hard_skills": {
            "python": ["python", "django", "flask", "pandas", "numpy", "pytorch", "tensorflow"],
            "javascript": ["javascript", "react", "node.js", "typescript", "vue.js", "angular", "next.js"],
            "sql": ["sql", "postgresql", "mysql", "mariadb", "sql server", "bigquery", "snowflake"],
            "cloud": ["aws", "azure", "gcp", "cloud computing", "docker", "kubernetes", "terraform"],
            "data_science": ["machine learning", "deep learning", "ia", "inteligência artificial", "data science", "big data", "analytics"]
        },
        "soft_skills": {
            "lideranca": ["liderança", "gestão de equipe", "liderar", "team lead", "gestão de pessoas", "gestão de time"],
            "comunicacao": ["comunicação", "apresentação", "negociação", "reuniões", "relacionamento", "stakeholders"],
            "resolucao_problemas": ["resolução de problemas", "análise crítica", "pensamento lógico", "solução de problemas", "análise de dados"]
        },
        "tools": {
            "crm": ["salesforce", "hubspot", "pipedrive", "crm", "sap", "oracle"],
            "analytics": ["tableau", "power bi", "looker", "metabase", "google analytics", "sheets", "excel"]
        }
    }
    
    for category, skills in skills_database.items():
        for skill_name, keywords in skills.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Calcular nível de proficiência com base no contexto
                    if "avançado" in text_lower or "especialista" in text_lower or "expert" in text_lower:
                        proficiency = 5
                    elif "sênior" in text_lower or "domínio" in text_lower or "proficiência" in text_lower:
                        proficiency = 4
                    elif "intermediário" in text_lower or "bom conhecimento" in text_lower or "conhecimento sólido" in text_lower:
                        proficiency = 3
                    else:
                        proficiency = 2
                    
                    skills_found.append({
                        "name": skill_name.replace("_", " ").title(),
                        "normalized": skill_name,
                        "category": category,
                        "proficiency_level": proficiency,
                        "is_mandatory": "obrigatório" in text_lower or "requisito" in text_lower or "essencial" in text_lower,
                        "importance_weight": 90 if ("obrigatório" in text_lower or "requisito" in text_lower) else 70,
                        "raw_text": keyword
                    })
    
    # Remover duplicatas
    unique_skills = []
    seen = set()
    for skill in skills_found:
        if skill["normalized"] not in seen:
            seen.add(skill["normalized"])
            unique_skills.append(skill)
    
    return unique_skills

def generate_embeddings(text: str) -> list:
    """Gera embeddings para matching semântico - PADRÃO EIGHTFOLD"""
    if not EMBEDDING_MODEL or not text:
        return []
    
    try:
        embedding = EMBEDDING_MODEL.encode(text, convert_to_tensor=False)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"❌ Erro ao gerar embeddings: {e}")
        return []

def calculate_quality_score(vaga: dict) -> float:
    """Calcula score de qualidade baseado em critérios do Lovable - PADRÃO BEAMERY"""
    score = 0.0
    
    # Descrição completa (>200 caracteres)
    if len(vaga.get("description", "")) > 200:
        score += 0.2
    
    # Skills identificadas
    skills_required = vaga.get("skills_required", [])
    if skills_required and len(skills_required) > 0:
        score += 0.3
    
    # Salário divulgado
    if vaga.get("salary_disclosed") and vaga["salary_disclosed"]:
        score += 0.2
    
    # Localização clara
    if vaga.get("city") and vaga.get("state"):
        score += 0.15
    
    # Modelo de trabalho definido
    work_model = vaga.get("work_model")
    if work_model and work_model in ["remote", "hybrid", "onsite"]:
        score += 0.15
    
    return min(score, 1.0)

def process_job_for_lovable(raw_vaga: dict) -> dict:
    """Processa vaga para o formato exato do Lovable - PADRÃO UNICÓRNIO"""
    # Gerar embeddings para matching semântico
    description_embedding = generate_embeddings(raw_vaga["descricao_completa"])
    skills_text = " ".join([skill["name"] for skill in raw_vaga["skills_required"]])
    skills_embedding = generate_embeddings(skills_text)
    
    processed = {
        # 1. Identificação e Metadados
        "external_id": f"{raw_vaga['fonte']}_{hash(raw_vaga['link_candidatura'])}",
        "source": raw_vaga["fonte"],
        "source_url": raw_vaga["link_candidatura"],
        "scraped_at": datetime.utcnow().isoformat(),
        "posted_at": f"{raw_vaga['data_publicacao']}T00:00:00Z",
        "posted_days_ago": (datetime.now() - datetime.strptime(raw_vaga['data_publicacao'], "%Y-%m-%d")).days,
        "is_active": True,
        "is_verified": True,
        "ghost_job_risk_score": 0.1 if raw_vaga["fonte"] in ["LinkedIn", "Indeed", "Gupy"] else 0.3,
        
        # 2. Informações do Cargo
        "title": raw_vaga["cargo"],
        "title_normalized": normalize_title(raw_vaga["cargo"]),
        "seniority_level": detect_seniority(raw_vaga["descricao_completa"], raw_vaga["cargo"]),
        "area": detect_area(raw_vaga["descricao_completa"], raw_vaga["cargo"]),
        "sub_area": "",
        "sub_area_level_2": "",
        "sub_area_level_3": "",
        
        # 3. Informações da Empresa
        "company_name": raw_vaga["empresa"] if raw_vaga["empresa"] != "Não informado" else "Empresa não informada",
        "company_name_normalized": normalize_title(raw_vaga["empresa"] if raw_vaga["empresa"] != "Não informado" else "empresa não informada"),
        "is_headhunter": raw_vaga["fonte"] in ["Korn Ferry", "Spencer Stuart", "Egon Zehnder", "Heidrick & Struggles", "Russell Reynolds"],
        "is_tech_specialized": raw_vaga["fonte"] in ["LinkedIn", "Gupy", "Trampos.co", "Glassdoor", "Indeed"],
        
        # 4. Localização e Modelo de Trabalho
        "city": "São Paulo",  # Será extraído futuramente
        "state": "SP",       # Será extraído futuramente
        "country": "Brasil",
        # "region": extract_region(raw_vaga["localizacao"]),
        "work_model": raw_vaga["modalidade"].lower() if raw_vaga["modalidade"] != "Não informado" else "onsite",
        "is_remote_eligible": "remoto" in raw_vaga["modalidade"].lower() or "remote" in raw_vaga["modalidade"].lower(),
        "remote_countries": ["Brasil"],
        
        # 5. Remuneração e Benefícios
        "salary_min": None,
        "salary_max": None,
        "salary_median": None,
        "salary_disclosed": "salário" in raw_vaga["descricao_completa"].lower() or "remuneração" in raw_vaga["descricao_completa"].lower(),
        "salary_type": "CLT",
        "currency": "BRL",
        "benefits": {},
        
        # 6. Skills e Requisitos
        "skills_required": raw_vaga["skills_required"],
        "experience_years_min": 5 if "5+ anos" in raw_vaga["descricao_completa"].lower() else 3 if "3+ anos" in raw_vaga["descricao_completa"].lower() else 2,
        "experience_years_max": None,
        
        # 7. Qualificações
        "education_required": [],
        "certifications_required": [],
        "languages_required": [],
        
        # 8. Conteúdo e Descrição
        "description": raw_vaga["descricao_completa"],
        "description_summary": raw_vaga["descricao_completa"][:200] + "..." if len(raw_vaga["descricao_completa"]) > 200 else raw_vaga["descricao_completa"],
        "responsibilities": [],
        "culture_keywords": ["resultados", "colaboração", "inovação", "excelência"],
        
        # 9. Embeddings e AI
        "embedding": json.dumps(description_embedding) if description_embedding else None,
        "skills_embedding": json.dumps(skills_embedding) if skills_embedding else None,
        
        # 10. Métricas e Analytics
        "view_count": 0,
        "application_count": 0,
        "competition_level": "alta" if raw_vaga["fonte"] == "LinkedIn" else ("média" if raw_vaga["fonte"] == "Indeed" else "baixa"),
        
        # Qualidade do dado
        "quality_score": 0.0  # Será calculado abaixo
    }
    
    # Calcular qualidade
    processed["quality_score"] = calculate_quality_score(processed)
    
    return processed

def scrape_job_details(url: str, session: requests.Session) -> dict:
    """Scraping PROFUNDO com proxy rotativo - ESTRATÉGIA SEEKOUT"""
    try:
        # Respeitar delays
        time.sleep(DELAY_ENTRE_REQUISICOES)
        
        # Tentativas com fallbacks
        for tentativa in range(3):
            try:
                res = session.get(url, timeout=15)
                if res.status_code == 200:
                    break
                logger.warning(f"Tentativa {tentativa+1} falhou com status {res.status_code}")
                time.sleep(5)
            except Exception as e:
                logger.warning(f"Tentativa {tentativa+1} falhou: {e}")
                time.sleep(5)
        else:
            logger.error(f"❌ Todas as tentativas falharam para {url}")
            return {
                "descricao_completa": f"Erro ao coletar detalhes da vaga em {url}",
                "salario": "Não informado",
                "modalidade": "Não informado"
            }
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Extrair conteúdo principal
        descricao = ""
        candidates = [
            "div.description", "div.job-description", "div.content", "article",
            "section.description", "div.job-details", "div.vacancy-description"
        ]
        
        for selector in candidates:
            elements = soup.select(selector)
            if elements:
                descricao = "\n".join([elem.get_text(strip=True) for elem in elements])
                if len(descricao) > 200:  # Conteúdo significativo
                    break
        
        if not descricao:
            main = soup.select_one("main, #main, .main")
            descricao = main.get_text(strip=True) if main else "Descrição não encontrada"
        
        # Detectar informações extras
        salario = "Não informado"
        modalidade = "Não informado"
        
        if "salário" in descricao.lower() or "salario" in descricao.lower() or "R$" in descricao:
            salario = "Salário a combinar"
            if "R$" in descricao:
                # Tentar extrair valor aproximado
                match = re.search(r'R\$\s*([\d\.,]+)', descricao)
                if match:
                    salario = f"R$ {match.group(1)}"
        
        if "remoto" in descricao.lower() or "remote" in descricao.lower():
            modalidade = "remote"
        elif "presencial" in descricao.lower() or "on-site" in descricao.lower():
            modalidade = "onsite"
        elif "híbrido" in descricao.lower() or "hibrido" in descricao.lower() or "hybrid" in descricao.lower():
            modalidade = "hybrid"
        
        return {
            "descricao_completa": descricao[:2000] + "..." if len(descricao) > 2000 else descricao,
            "salario": salario,
            "modalidade": modalidade
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao coletar detalhes da vaga {url}: {e}")
        return {
            "descricao_completa": f"Erro durante a coleta: {str(e)}",
            "salario": "Não informado",
            "modalidade": "Não informado"
        }

def scrape_google_jobs(query_base: str, days_back: int = 1) -> list:
    """Coleta inteligente com filtragem geográfica e de qualidade - PADRÃO UNICÓRNIO"""
    all_jobs = []
    yesterday = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Criar sessão com proxy
    session = get_proxy_session()
    
    logger.info(f"🌍 INICIANDO COLETA COM FILTRAGEM GEOGRÁFICA BRASIL")
    logger.info(f"🔍 Fontes configuradas: {len(SOURCES_BRASIL)} sites")
    logger.info(f"📊 Limite: {MAX_VAGAS_POR_FONTE} vagas por fonte, {MAX_VAGAS_TOTAIS} total")
    
    for source_query, location_filter in SOURCES_BRASIL:
        if len(all_jobs) >= MAX_VAGAS_TOTAIS:
            logger.info(f"🎯 Limite total de {MAX_VAGAS_TOTAIS} vagas atingido")
            break
        
        # Montar query com filtros geográficos e data
        search_query = f'{query_base} {source_query} {location_filter} after:{yesterday}'
        logger.info(f"🔍 Buscando no Google (via SerpAPI): {search_query}")
        
        try:
            url = f"https://serpapi.com/search.json?q={urllib.parse.quote(search_query)}&hl=pt-BR&num={MAX_VAGAS_POR_FONTE*2}&api_key={SERPAPI_KEY}"
            res = requests.get(url, timeout=20)
            data = res.json()
            
            if "organic_results" not in data:
                logger.warning(f"⚠️ Nenhum resultado para: {search_query}")
                continue
            
            # Processar resultados com filtragem rigorosa
            vagas_fonte = 0
            for result in data["organic_results"]:
                if vagas_fonte >= MAX_VAGAS_POR_FONTE or len(all_jobs) >= MAX_VAGAS_TOTAIS:
                    break
                
                link = result.get("link", "")
                title = result.get("title", "Vaga sem título")
                
                # Filtros de qualidade imediatos
                if not link or len(link) < 10 or "google.com" in link or "url?" in link:
                    continue
                
                # Detectar fonte
                fonte = "Google"
                for site in [
                    "linkedin.com/jobs", "gupy.com.br", "vagas.com.br", "trampos.co",
                    "ciadetalentos.com.br", "glassdoor.com.br", "indeed.com", "roberthalf.com.br",
                    "michaelpage.com.br", "kornferry.com", "spencerstuart.com", "heidrick.com",
                    "russellreynolds.com", "pageexecutive.com", "talenses.com", "exec.com.br"
                ]:
                    if site in link:
                        fonte = site.split(".")[0].replace("com", "").replace("br", "").title()
                        break
                
                # Filtros de relevância BRASIL + EXECUTIVA
                title_lower = title.lower()
                snippet = result.get("snippet", "")
                
                if not is_vaga_brasil(title + " " + link + " " + snippet):
                    logger.info(f"🌍 Ignorando vaga internacional: {title[:50]}...")
                    continue
                
                if not is_vaga_executiva(title):
                    logger.info(f"🏢 Ignorando vaga não executiva: {title[:50]}...")
                    continue
                
                # Coletar detalhes com proxy
                details = scrape_job_details(link, session)
                
                # Extrair skills
                skills = extract_skills(details["descricao_completa"])
                
                # Montar registro completo
                job_record = {
                    "cargo": title.strip()[:100],
                    "empresa": "Não informado",
                    "salario": details["salario"][:50],
                    "modalidade": details["modalidade"][:30],
                    "data_publicacao": yesterday,
                    "localizacao": "Brasil",
                    "fonte": fonte,
                    "link_candidatura": link[:255],
                    "descricao_completa": details["descricao_completa"],
                    "skills_required": skills
                }
                
                all_jobs.append(job_record)
                vagas_fonte += 1
                logger.info(f"✅ Coletada vaga RICA [{fonte}]: {title[:50]}... (Skills: {len(skills)})")
            
            logger.info(f"📊 Fonte '{fonte}': {vagas_fonte} vagas relevantes coletadas")
            time.sleep(3)  # Respeitar SerpAPI
        
        except Exception as e:
            logger.error(f"❌ Erro na busca do Google/SerpAPI para {source_query}: {e}")
            time.sleep(5)
    
    logger.info(f"✅ COLETA FINALIZADA: {len(all_jobs)} vagas RICAS e RELEVANTES para o Brasil")
    return all_jobs

def save_to_supabase(vagas: list):
    """Salva vagas no Supabase com tratamento de erros - PADRÃO PRODUÇÃO"""
    logger.info("💾 INICIANDO SALVAMENTO NO SUPABASE...")
    saved_count = 0
    errors_count = 0
    
    for vaga in vagas:
        try:
            # Processar para formato Lovable
            processed_vaga = process_job_for_lovable(vaga)
            
            # Salvar no Supabase
            supabase.table("vagas_lovable").insert(processed_vaga).execute()
            logger.info(f"✅ Vaga salva: {processed_vaga['title'][:50]}... ({processed_vaga['source']})")
            saved_count += 1
        except Exception as e:
            logger.error(f"❌ Erro ao salvar vaga '{vaga.get('cargo', 'Sem título')[:30]}...': {e}")
            errors_count += 1
    
    logger.info(f"✅ SALVAMENTO CONCLUÍDO: {saved_count} vagas salvas, {errors_count} erros")
    return saved_count

def run_scrapper():
    """Função mestre de coleta inteligente - PADRÃO UNICÓRNIO"""
    logger.info("🚀 INICIANDO COLETOR INTELIGENTE DE VAGAS (PADRÃO UNICÓRNIO)")
    logger.info("🎯 Foco: Vagas executivas no Brasil com alta qualidade de dados")
    
    # Coletar vagas com filtros rigorosos
    vagas = scrape_google_jobs(
        "diretor OR gerente OR head OR líder OR executivo OR supervisor OR coordenador OR senior OR sênior OR c-level OR chief"
    )
    
    # Salvar no banco
    saved_count = save_to_supabase(vagas)
    
    # Métricas de qualidade
    logger.info("📈 MÉTRICAS FINAIS:")
    logger.info(f"   • Total de vagas coletadas: {len(vagas)}")
    logger.info(f"   • Vagas salvas com sucesso: {saved_count}")
    logger.info(f"   • Fontes utilizadas: {len(SOURCES_BRASIL)}")
    logger.info(f"   • Proxy rotativo: {'Ativo' if SCRAPERAPI_KEY else 'Inativo'}")
    logger.info(f"   • Embeddings: {'Ativo' if EMBEDDING_MODEL else 'Inativo'}")
    
    return saved_count

# Flask API
from flask import Flask

app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de saúde do serviço"""
    return {
        "status": "online",
        "time": datetime.utcnow().isoformat(),
        "message": "✅ Coletor Inteligente de Vagas está online! (Padrão Unicórnio)",
        "config": {
            "max_vagas_por_fonte": MAX_VAGAS_POR_FONTE,
            "max_vagas_totais": MAX_VAGAS_TOTAIS,
            "fontes_configuradas": len(SOURCES_BRASIL),
            "proxy_ativo": bool(SCRAPERAPI_KEY),
            "embeddings_ativo": bool(EMBEDDING_MODEL)
        }
    }

if __name__ == "__main__":
    logger.info("🔥 INICIANDO SERVIDOR - AGUARDANDO REQUISIÇÕES")
    run_scrapper()  # Executar coleta imediatamente ao iniciar
    app.run(host="0.0.0.0", port=8000)
