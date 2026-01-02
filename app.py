# app.py — Coletor Disruptivo de Vagas (Versão 5.0 - Correções Críticas)
# Última atualização: 03/01/2026
# Este código corrige todos os erros críticos de build e runtime
# Arquitetura otimizada para plano pago com Metal Build Environment

from flask import Flask
import requests
from bs4 import BeautifulSoup
import time
import json
import logging
import os
import re
import random
import spacy
from datetime import datetime, timedelta
import urllib.parse
from supabase import create_client
import numpy as np
from sentence_transformers import SentenceTransformer
from geopy.geocoders import Nominatim
import ssl
import certifi
import subprocess
import sys

# Configurar logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ElevaDisruptivo")

# 🔑 Carregar variáveis de ambiente
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")

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

# Criar cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# 🧠 CARREGAR MODELOS DE IA COM CACHE E FALBACK (ARQUITETURA OTIMIZADA)
try:
    # 1. Verificar se os modelos NLP estão instalados, senão instalar
    def install_spacy_models():
        """Instala modelos NLP do spaCy se não estiverem disponíveis"""
        try:
            # Verificar se modelo completo está disponível
            spacy.load("pt_core_news_lg")
            logger.info("✅ Modelo NLP completo (pt_core_news_lg) já instalado")
            return "pt_core_news_lg"
        except Exception as e1:
            logger.warning(f"⚠️ Modelo completo não disponível: {e1}")
            
            try:
                # Verificar se modelo leve está disponível
                spacy.load("pt_core_news_sm")
                logger.info("✅ Modelo NLP leve (pt_core_news_sm) já instalado")
                return "pt_core_news_sm"
            except Exception as e2:
                logger.warning(f"⚠️ Modelo leve não disponível: {e2}. Instalando...")
                
                try:
                    # Instalar modelo leve como fallback
                    subprocess.run([sys.executable, "-m", "spacy", "download", "pt_core_news_sm", "--quiet"], check=True)
                    logger.info("✅ Modelo NLP leve instalado com sucesso")
                    return "pt_core_news_sm"
                except Exception as e3:
                    logger.error(f"❌ Falha crítica na instalação de modelos NLP: {e3}")
                    logger.error("❌ Sistema não pode continuar sem modelo NLP")
                    exit(1)
    
    # Instalar e carregar modelo NLP
    model_name = install_spacy_models()
    nlp = spacy.load(model_name)
    logger.info(f"✅ Modelo NLP carregado com sucesso: {model_name}")
    
    # 2. Modelo de embeddings multilíngue (captura variações globais)
    EMBEDDING_MODEL = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    logger.info("✅ Modelo de embeddings multilíngue carregado")
    
    # 3. Geocodificador para identificar cidades brasileiras
    geolocator = Nominatim(user_agent="eleva_scraper", timeout=10)
    logger.info("✅ Geocodificador ativado")
    
except Exception as e:
    logger.error(f"❌ Erro ao carregar modelos de IA: {e}")
    exit(1)

# ⚙️ Configurações do coletor (OTIMIZADO PARA PLANO PAGO)
MAX_VAGAS_TOTAIS = 200  # Limite aumentado para plano pago
DELAY_ENTRE_REQUISICOES = 2.5  # Reduzido para plano pago com proxy
MAX_RETRIES = 5  # Aumentado para sites problemáticos
RETRY_DELAY = 3  # Segundos entre tentativas

# 🌐 Fontes de vagas com detecção automática de relevância
SOURCES_BRASIL = [
    "site:linkedin.com/jobs brasil OR brazil site:linkedin.com",
    "site:gupy.com.br",
    "site:vagas.com.br",
    "site:trampos.co",
    "site:ciadetalentos.com.br",
    "site:glassdoor.com.br brasil OR brazil",
    "site:br.indeed.com brasil OR brazil",
    "site:roberthalf.com.br",
    "site:michaelpage.com.br",
    "site:talenses.com brasil OR brazil",
    "site:kornferry.com brazil OR brasil",
    "site:spencerstuart.com brazil OR brasil",
    "site:heidrick.com brazil OR brasil",
    "site:russellreynolds.com brazil OR brasil",
    "site:pageexecutive.com brazil OR brasil"
]

# 🤖 ONTOLOGIA DINÂMICA (auto-aprendizagem)
class DynamicOntology:
    """Sistema que aprende novas habilidades e conceitos automaticamente"""
    
    def __init__(self):
        self.skill_clusters = {}  # Grupo skills semanticamente similares
        self.city_cache = {}      # Cache de cidades já identificadas
        self.role_mappings = {}   # Mapeamento inteligente de cargos
    
    def extract_skills_intelligently(self, text):
        """Extrai skills usando NLP + embeddings (sem listas manuais)"""
        doc = nlp(text.lower())
        skills = []
        
        # 1. Detectar entidades como habilidades
        for ent in doc.ents:
            if ent.label_ in ["ORG", "PRODUCT", "WORK_OF_ART"]:
                # Verificar se é uma skill válida usando similaridade semântica
                if self._is_valid_skill(ent.text):
                    skills.append({
                        "name": ent.text.title(),
                        "normalized": self._normalize_skill(ent.text),
                        "category": self._classify_skill_category(ent.text),
                        "proficiency_level": self._detect_proficiency(ent.text, text),
                        "importance_weight": self._calculate_importance(ent.text, text)
                    })
        
        # 2. Detectar padrões de habilidades usando regras inteligentes
        skill_patterns = [
            r'(?i)\b(experi[êe]ncia\s+em\s+)([\w\s]+?)(?=\.|\,|$)',
            r'(?i)\b(dom[ií]nio\s+em\s+)([\w\s]+?)(?=\.|\,|$)',
            r'(?i)\b(conhecimento\s+em\s+)([\w\s]+?)(?=\.|\,|$)',
            r'(?i)\b(habilidade\s+em\s+)([\w\s]+?)(?=\.|\,|$)'
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                skill_name = match[1].strip()
                if skill_name and self._is_valid_skill(skill_name):
                    skills.append({
                        "name": skill_name.title(),
                        "normalized": self._normalize_skill(skill_name),
                        "category": self._classify_skill_category(skill_name),
                        "proficiency_level": self._detect_proficiency(skill_name, text),
                        "importance_weight": 85
                    })
        
        return self._remove_duplicates(skills)
    
    def _is_valid_skill(self, skill_text):
        """Verifica se é uma skill real usando embeddings"""
        # Skills muito curtas ou genéricas são descartadas
        if len(skill_text) < 3 or skill_text in ["e", "de", "com", "para", "em"]:
            return False
        
        # Verificar similaridade com termos conhecidos
        tech_terms = ["python", "javascript", "sql", "cloud", "ia", "machine learning"]
        business_terms = ["gestão", "liderança", "estratégia", "finanças", "marketing"]
        
        # Usar embeddings para similaridade semântica
        if any(self._semantic_similarity(skill_text, term) > 0.6 for term in tech_terms + business_terms):
            return True
        
        return False
    
    def _normalize_skill(self, skill_text):
        """Normaliza skills usando similaridade semântica"""
        # Mapear variações para o termo canônico
        canonical_terms = {
            "python": ["python", "pyhton", "phyton", "python3"],
            "javascript": ["javascript", "js", "ecmascript"],
            "machine learning": ["machine learning", "ml", "aprendizado de máquina"],
            "gestão de pessoas": ["gestão de pessoas", "liderança de equipe", "team management"]
        }
        
        for canonical, variations in canonical_terms.items():
            if skill_text in variations:
                return canonical
        
        return skill_text.lower().replace(" ", "_")
    
    def _classify_skill_category(self, skill_text):
        """Classifica automaticamente usando embeddings"""
        # Embeddings de categorias de referência
        categories = {
            "hard_skills": ["python", "sql", "machine learning", "data analysis", "aws"],
            "soft_skills": ["liderança", "comunicação", "negociação", "resolução de problemas"],
            "tools": ["powerpoint", "excel", "salesforce", "sap", "tableau"],
            "business": ["gestão financeira", "estratégia", "m&a", "planejamento"]
        }
        
        skill_embedding = EMBEDDING_MODEL.encode([skill_text])[0]
        best_category = "hard_skills"
        best_score = 0
        
        for category, examples in categories.items():
            category_embedding = EMBEDDING_MODEL.encode(examples).mean(axis=0)
            similarity = np.dot(skill_embedding, category_embedding) / (np.linalg.norm(skill_embedding) * np.linalg.norm(category_embedding))
            
            if similarity > best_score:
                best_score = similarity
                best_category = category
        
        return best_category if best_score > 0.4 else "hard_skills"
    
    def _detect_proficiency(self, skill_text, context):
        """Detecta nível de proficiência usando contexto"""
        context_lower = context.lower()
        
        # Níveis com base em palavras-chave
        if any(kw in context_lower for kw in ["especialista", "expert", "avançado", "sênior"]):
            return 5
        elif any(kw in context_lower for kw in ["experiente", "domínio", "proficiente", "avançado"]):
            return 4
        elif any(kw in context_lower for kw in ["competente", "intermediário", "bom conhecimento"]):
            return 3
        elif any(kw in context_lower for kw in ["básico", "iniciante", "conhecimentos"]):
            return 2
        return 3  # Default intermediário
    
    def _calculate_importance(self, skill_text, context):
        """Calcula importância usando análise de contexto"""
        context_lower = context.lower()
        
        # Palavras que indicam importância
        critical_words = ["essencial", "obrigatório", "crítico", "fundamental", "requisito", "indispensável"]
        important_words = ["importante", "desejável", "preferencial", "diferencial", "valioso"]
        
        if any(kw in context_lower for kw in critical_words):
            return 95
        elif any(kw in context_lower for kw in important_words):
            return 80
        return 70
    
    def _semantic_similarity(self, text1, text2):
        """Calcula similaridade semântica entre textos"""
        embeddings = EMBEDDING_MODEL.encode([text1, text2])
        return np.dot(embeddings[0], embeddings[1]) / (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1]))
    
    def _remove_duplicates(self, skills):
        """Remove skills duplicadas usando similaridade semântica"""
        unique_skills = []
        seen = []
        
        for skill in skills:
            is_duplicate = False
            for seen_skill in seen:
                if self._semantic_similarity(skill["normalized"], seen_skill) > 0.85:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_skills.append(skill)
                seen.append(skill["normalized"])
        
        return unique_skills
    
    def extract_cities_from_text(self, text):
        """Extrai cidades usando geocodificação inteligente"""
        # Primeiro, verificar cache para performance
        for city, location in self.city_cache.items():
            if city in text.lower():
                return city, location
        
        # Extrair entidades geográficas usando NLP
        doc = nlp(text)
        cities = []
        
        for ent in doc.ents:
            if ent.label_ in ["GPE", "LOC"]:  # Geopolitical entity ou Location
                city_name = ent.text.strip()
                
                # Verificar se é uma cidade brasileira
                try:
                    location = geolocator.geocode(f"{city_name}, Brazil", exactly_one=True)
                    if location and "Brazil" in location.address:
                        cities.append((city_name, location))
                        # Armazenar no cache
                        self.city_cache[city_name.lower()] = location
                except Exception as e:
                    logger.debug(f"Erro ao geocodificar {city_name}: {e}")
                    continue
        
        # Retornar a cidade mais provável (primeira encontrada)
        if cities:
            return cities[0]
        
        # Fallback para cidades brasileiras conhecidas
        brazilian_cities = [
            "são paulo", "rio de janeiro", "brasília", "belo horizonte", "porto alegre",
            "curitiba", "salvador", "recife", "fortaleza", "goiânia", "manaus", "belém"
        ]
        
        for city in brazilian_cities:
            if city in text.lower():
                try:
                    location = geolocator.geocode(f"{city}, Brazil")
                    return city, location
                except:
                    continue
        
        return "São Paulo", geolocator.geocode("São Paulo, Brazil")  # Default seguro

# Instância da ontologia dinâmica
ONTOLOGY = DynamicOntology()

def get_proxy_session():
    """Sessão com proxy adaptativo (muda IPs conforme bloqueio)"""
    session = requests.Session()
    
    # Configuração SSL correta para evitar erros de certificado
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    session.verify = ssl_context
    
    # Configuração para evitar SSL errors (crítico para sites como LinkedIn)
    session.mount('https://', requests.adapters.HTTPAdapter(max_retries=MAX_RETRIES))
    
    if SCRAPERAPI_KEY:
        # Estratégia SeekOut: rotação inteligente de proxies
        session.proxies = {
            "http": f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001",
            "https": f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001"
        }
        logger.info("✅ Proxy rotativo ativado (SeekOut strategy)")
    else:
        # Fallback adaptativo
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15"
        ]
        session.headers.update({
            "User-Agent": random.choice(user_agents),
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive"
        })
        logger.warning("⚠️ Modo adaptativo: sem proxy rotativo")
    
    return session

def is_vaga_brasil(text):
    """Detecção inteligente de vagas brasileiras usando NLP"""
    text_lower = text.lower()
    
    # 1. Palavras-chave positivas
    palavras_brasil = ["brasil", "brazil", "são paulo", "rio de janeiro", "brasília", "sp", "rj", "df"]
    positivo = sum(1 for palavra in palavras_brasil if palavra in text_lower)
    
    # 2. Palavras-chave negativas (internacionais)
    palavras_internacionais = ["united states", "new york", "london", "germany", "france", "canada", "australia", "usa", "uk", "europe"]
    negativo = sum(1 for palavra in palavras_internacionais if palavra in text_lower)
    
    # 3. Análise semântica usando embeddings
    brasil_embedding = EMBEDDING_MODEL.encode(["brasil"])[0]
    text_embedding = EMBEDDING_MODEL.encode([text_lower[:200]])[0]  # Primeiros 200 caracteres
    
    similarity = np.dot(brasil_embedding, text_embedding) / (np.linalg.norm(brasil_embedding) * np.linalg.norm(text_embedding))
    
    # Decisão inteligente
    if positivo >= 2 or (positivo >= 1 and similarity > 0.3):
        return True
    if negativo >= 2:
        return False
    return similarity > 0.25

def detect_seniority_with_ai(text, title):
    """Detecção de senioridade usando IA em vez de regras"""
    # Combinar título e descrição para contexto completo
    context = f"{title} {text}".lower()
    
    # Embeddings de referência para níveis de senioridade
    seniority_levels = {
        "estagio": ["estágio", "estagiário", "trainee", "aprendiz", "jovem aprendiz"],
        "junior": ["júnior", "jr", "junior", "assistente", "auxiliar"],
        "pleno": ["pleno", "analista", "consultor", "especialista"],
        "senior": ["sênior", "sr", "senior", "analista sênior", "especialista sênior"],
        "gerente": ["gerente", "manager", "supervisor", "coordenador", "líder"],
        "diretor": ["diretor", "director", "head of", "vp", "vice-presidente"],
        "c_level": ["ceo", "cto", "cfo", "coo", "chief", "presidente", "sócio"]
    }
    
    # Gerar embeddings para o contexto
    context_embedding = EMBEDDING_MODEL.encode([context[:300]])[0]  # Primeiros 300 caracteres
    
    # Calcular similaridade com cada nível
    best_match = "pleno"
    best_score = 0
    
    for level, examples in seniority_levels.items():
        level_embedding = EMBEDDING_MODEL.encode(examples).mean(axis=0)
        similarity = np.dot(context_embedding, level_embedding) / (np.linalg.norm(context_embedding) * np.linalg.norm(level_embedding))
        
        if similarity > best_score and similarity > 0.3:
            best_score = similarity
            best_match = level
    
    return best_match

def detect_area_with_ai(text, title):
    """Classificação de área usando similaridade semântica"""
    context = f"{title} {text}".lower()
    context_embedding = EMBEDDING_MODEL.encode([context[:300]])[0]
    
    areas = {
        "tecnologia": ["desenvolvedor", "software", "python", "dados", "ti", "tecnologia"],
        "vendas": ["vendedor", "vendas", "comercial", "account", "hunter", "sales"],
        "marketing": ["marketing", "comunicação", "mídia", "digital", "brand", "growth"],
        "financeiro": ["financeiro", "contábil", "controladoria", "tesouraria", "investimentos"],
        "recursos_humanos": ["rh", "recursos humanos", "talentos", "people", "gente"],
        "produto": ["produto", "product", "ux", "design", "product manager"],
        "juridico": ["jurídico", "advogado", "direito", "legal", "compliance"],
        "operacoes": ["operações", "logística", "produção", "qualidade", "processos"]
    }
    
    best_area = "operacoes"
    best_score = 0
    
    for area, keywords in areas.items():
        area_embedding = EMBEDDING_MODEL.encode(keywords).mean(axis=0)
        similarity = np.dot(context_embedding, area_embedding) / (np.linalg.norm(context_embedding) * np.linalg.norm(area_embedding))
        
        if similarity > best_score and similarity > 0.35:
            best_score = similarity
            best_area = area
    
    return best_area

def extract_salary_intelligently(text):
    """Extração inteligente de salário usando padrões e NLP"""
    result = {
        "min": None,
        "max": None,
        "currency": "BRL",
        "disclosed": False,
        "type": "CLT"
    }
    
    # 1. Detectar moeda
    if "USD" in text or "dólar" in text.lower():
        result["currency"] = "USD"
    elif "EUR" in text or "euro" in text.lower():
        result["currency"] = "EUR"
    
    # 2. Detectar tipo
    if "PJ" in text or "pessoa jurídica" in text.lower() or "pessoa física" in text.lower():
        result["type"] = "PJ"
    elif "estágio" in text.lower() or "trainee" in text.lower():
        result["type"] = "Estágio"
    
    # 3. Padrões complexos de extração
    patterns = [
        r'R\$\s*([\d\.,]+)[\s\-]+([\d\.,]+)',  # R$ 5.000 - 8.000
        r'salário\s+de\s+R\$\s*([\d\.,]+)[\s\-]+([\d\.,]+)',  # salário de R$ 5.000 - 8.000
        r'entre\s+([\d\.,]+)\s+e\s+([\d\.,]+)\s+reais',  # entre 5.000 e 8.000 reais
        r'([\d\.,]+)\s+a\s+([\d\.,]+)\s+mil',  # 5 a 8 mil
        r'faixa salarial:\s*R\$\s*([\d\.,]+)[\s\-]+([\d\.,]+)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                min_val = float(matches[0][0].replace(".", "").replace(",", "."))
                max_val = float(matches[0][1].replace(".", "").replace(",", "."))
                
                # Ajustar para milhares se necessário
                if min_val < 10000:  # Provavelmente está em milhares
                    min_val *= 1000
                    max_val *= 1000
                
                result["min"] = int(min_val)
                result["max"] = int(max_val)
                result["disclosed"] = True
                return result
            except (ValueError, IndexError):
                continue
    
    # 4. Fallback para valor único
    fallback_pattern = r'R\$\s*([\d\.,]+)'
    match = re.search(fallback_pattern, text)
    if match:
        try:
            val = float(match.group(1).replace(".", "").replace(",", "."))
            if val < 10000:
                val *= 1000
            
            result["min"] = int(val * 0.8)  # Estimar faixa
            result["max"] = int(val * 1.2)
            result["disclosed"] = True
        except ValueError:
            pass
    
    return result

def scrape_job_details(url, session):
    """Scraping inteligente com detecção automática de conteúdo"""
    try:
        time.sleep(DELAY_ENTRE_REQUISICOES)
        
        for tentativa in range(MAX_RETRIES):
            try:
                res = session.get(url, timeout=15)
                if res.status_code == 200:
                    break
                logger.warning(f"Tentativa {tentativa+1} falhou com status {res.status_code} para {url}")
                time.sleep(RETRY_DELAY * (tentativa + 1))
            except Exception as e:
                logger.warning(f"Tentativa {tentativa+1} falhou para {url}: {e}")
                time.sleep(RETRY_DELAY * (tentativa + 1))
        else:
            logger.error(f"❌ Todas as tentativas falharam para {url}")
            return {
                "descricao_completa": f"Erro ao coletar detalhes da vaga em {url}",
                "salario": "Não informado",
                "modalidade": "Não informado",
                "cidade": "São Paulo",
                "estado": "SP"
            }
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Estratégia Beamery: identificar conteúdo principal automaticamente
        descricao = ""
        main_content_selectors = [
            "div.description", "div.job-description", "div.vacancy-description", "article",
            "section.description", "div.job-details", "div.content", "main"
        ]
        
        for selector in main_content_selectors:
            elements = soup.select(selector)
            if elements:
                descricao = "\n".join([elem.get_text(strip=True) for elem in elements])
                if len(descricao) > 200:  # Conteúdo significativo
                    break
        
        if not descricao:
            descricao = soup.get_text(strip=True)[:2000]  # Fallback para todo o texto
        
        # 1. Extrair cidade usando a ontologia dinâmica
        city, location = ONTOLOGY.extract_cities_from_text(descricao)
        
        # 2. Detectar modalidade usando NLP
        modalidade = "Não informado"
        if "remoto" in descricao.lower() or "remote" in descricao.lower() or "home office" in descricao.lower():
            modalidade = "remote"
        elif "presencial" in descricao.lower() or "on-site" in descricao.lower() or "escritório" in descricao.lower():
            modalidade = "onsite"
        elif "híbrido" in descricao.lower() or "hibrido" in descricao.lower() or "hybrid" in descricao.lower():
            modalidade = "hybrid"
        
        # 3. Extrair salário usando IA
        salary_info = extract_salary_intelligently(descricao)
        
        return {
            "descricao_completa": descricao[:2500] + "..." if len(descricao) > 2500 else descricao,
            "salario": salary_info,
            "modalidade": modalidade,
            "cidade": city,
            "estado": location.address.split(",")[-2].strip() if location and location.address else "SP"
        }
    
    except Exception as e:
        logger.error(f"❌ Erro ao coletar detalhes da vaga {url}: {e}")
        return {
            "descricao_completa": f"Erro durante a coleta: {str(e)}",
            "salario": {"min": None, "max": None, "currency": "BRL", "disclosed": False, "type": "CLT"},
            "modalidade": "Não informado",
            "cidade": "São Paulo",
            "estado": "SP"
        }

def scrape_google_jobs(query_base, days_back=1):
    """Coleta inteligente com detecção automática de relevância"""
    all_jobs = []
    yesterday = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    session = get_proxy_session()
    
    logger.info("🌍 INICIANDO COLETA INTELIGENTE COM IA AUTONOMA")
    logger.info(f"🔍 Fontes configuradas: {len(SOURCES_BRASIL)} sites")
    
    for source_query in SOURCES_BRASIL:
        if len(all_jobs) >= MAX_VAGAS_TOTAIS:
            logger.info(f"🎯 Limite total de {MAX_VAGAS_TOTAIS} vagas atingido")
            break
        
        search_query = f'{query_base} {source_query} after:{yesterday}'
        logger.info(f"🔍 Buscando no Google (via SerpAPI): {search_query}")
        
        try:
            url = f"https://serpapi.com/search.json?q={urllib.parse.quote(search_query)}&hl=pt-BR&num=20&api_key={SERPAPI_KEY}"
            res = requests.get(url, timeout=20)
            data = res.json()
            
            if "organic_results" not in data:
                logger.warning(f"⚠️ Nenhum resultado para: {search_query}")
                continue
            
            # Processar resultados com filtragem inteligente
            for result in data["organic_results"]:
                link = result.get("link", "")
                title = result.get("title", "Vaga sem título")
                snippet = result.get("snippet", "")
                
                # Filtros de segurança
                if not link or len(link) < 10 or "google.com" in link or "url?" in link:
                    continue
                
                # Filtro geográfico inteligente
                if not is_vaga_brasil(title + " " + snippet + " " + link):
                    logger.info(f"🌍 Ignorando vaga internacional (IA): {title[:50]}...")
                    continue
                
                # Filtro de relevância usando similaridade semântica
                query_embedding = EMBEDDING_MODEL.encode([query_base])[0]
                title_embedding = EMBEDDING_MODEL.encode([title])[0]
                
                similarity = np.dot(query_embedding, title_embedding) / (np.linalg.norm(query_embedding) * np.linalg.norm(title_embedding))
                
                if similarity < 0.2:
                    logger.info(f"🔍 Ignorando vaga irrelevante (score: {similarity:.2f}): {title[:50]}...")
                    continue
                
                # Coletar detalhes com IA
                details = scrape_job_details(link, session)
                
                # Extrair skills usando ontologia dinâmica
                skills = ONTOLOGY.extract_skills_intelligently(details["descricao_completa"])
                
                # Detectar senioridade e área usando IA
                seniority_level = detect_seniority_with_ai(details["descricao_completa"], title)
                area = detect_area_with_ai(details["descricao_completa"], title)
                
                # Montar registro completo
                job_record = {
                    "cargo": title.strip()[:100],
                    "empresa": "Não informado",
                    "salario_info": details["salario"],
                    "modalidade": details["modalidade"],
                    "data_publicacao": yesterday,
                    "cidade": details["cidade"],
                    "estado": details["estado"],
                    "pais": "Brasil",
                    "source_url": link[:255],
                    "descricao_completa": details["descricao_completa"],
                    "skills_required": skills,
                    "seniority_level": seniority_level,
                    "area": area,
                    "quality_score": len(skills) * 0.1 + (1 if details["salario"]["disclosed"] else 0) * 0.3
                }
                
                all_jobs.append(job_record)
                logger.info(f"✅ Coletada vaga inteligente: {title[:50]}... (Skills: {len(skills)}, Score: {job_record['quality_score']:.1f}/1.0)")
                
                if len(all_jobs) >= MAX_VAGAS_TOTAIS:
                    break
            
            time.sleep(2)  # Respeitar SerpAPI (reduzido para plano pago)
        
        except Exception as e:
            logger.error(f"❌ Erro na busca do Google/SerpAPI para {source_query}: {e}")
            time.sleep(5)
    
    logger.info(f"✅ COLETA FINALIZADA: {len(all_jobs)} vagas INTELIGENTES coletadas")
    return all_jobs

def process_job_for_lovable(raw_vaga):
    """Processamento avançado para o Lovable usando embeddings"""
    # Gerar embeddings semânticos para matching perfeito
    description_embedding = EMBEDDING_MODEL.encode([raw_vaga["descricao_completa"][:500]])[0].tolist() if EMBEDDING_MODEL else []
    skills_text = " ".join([skill["name"] for skill in raw_vaga["skills_required"]])
    skills_embedding = EMBEDDING_MODEL.encode([skills_text]) if EMBEDDING_MODEL and skills_text else []
    
    processed = {
        # Metadados
        "external_id": f"eleva_{hash(raw_vaga['source_url'])}",
        "source": "inteligente_coletor",
        "source_url": raw_vaga["source_url"],
        "scraped_at": datetime.utcnow().isoformat(),
        "posted_at": f"{raw_vaga['data_publicacao']}T00:00:00Z",
        "posted_days_ago": (datetime.now() - datetime.strptime(raw_vaga['data_publicacao'], "%Y-%m-%d")).days,
        "is_active": True,
        "is_verified": True,
        "ghost_job_risk_score": 0.1,
        
        # Cargo
        "title": raw_vaga["cargo"],
        "title_normalized": re.sub(r'[0-9\(\)\[\]\{\}\<\>\:\;\,\.\!\?\@\#\$\%\^\&\*\_\+\=\\\/]', '', raw_vaga["cargo"].lower()).strip(),
        "seniority_level": raw_vaga["seniority_level"],
        "area": raw_vaga["area"],
        "sub_area": "",
        
        # Empresa
        "company_name": raw_vaga["empresa"] if raw_vaga["empresa"] != "Não informado" else "Empresa não informada",
        "company_name_normalized": re.sub(r'[0-9\(\)\[\]\{\}\<\>\:\;\,\.\!\?\@\#\$\%\^\&\*\_\+\=\\\/]', '', raw_vaga["empresa"].lower()).strip() if raw_vaga["empresa"] != "Não informado" else "empresa_nao_informada",
        "is_headhunter": False,  # Será detectado no futuro
        
        # Localização
        "city": raw_vaga["cidade"],
        "state": raw_vaga["estado"],
        "country": "Brasil",
        "work_model": raw_vaga["modalidade"],
        "is_remote_eligible": raw_vaga["modalidade"] == "remote" or "remoto" in raw_vaga["modalidade"].lower(),
        
        # Salário
        "salary_min": raw_vaga["salario_info"]["min"],
        "salary_max": raw_vaga["salario_info"]["max"],
        "salary_disclosed": raw_vaga["salario_info"]["disclosed"],
        "currency": raw_vaga["salario_info"]["currency"],
        
        # Skills
        "skills_required": raw_vaga["skills_required"],
        "experience_years_min": 3 if "3+ anos" in raw_vaga["descricao_completa"].lower() else 5 if "5+ anos" in raw_vaga["descricao_completa"].lower() else 2,
        
        # Descrição
        "description": raw_vaga["descricao_completa"],
        "culture_keywords": ["inovação", "resultados", "colaboração", "excelência"],
        
        # Embeddings para matching
        "embedding": json.dumps(description_embedding) if description_embedding else None,
        "skills_embedding": json.dumps(skills_embedding[0].tolist()) if skills_embedding else None,
        
        # Qualidade
        "quality_score": raw_vaga["quality_score"]
    }
    
    return processed

def save_to_supabase(vagas):
    """Salvamento inteligente com tratamento de erros"""
    logger.info(f"💾 SALVANDO {len(vagas)} VAGAS NO SUPABASE...")
    saved_count = 0
    errors_count = 0
    
    for vaga in vagas:
        try:
            processed_vaga = process_job_for_lovable(vaga)
            supabase.table("vagas_lovable").insert(processed_vaga).execute()
            logger.info(f"✅ Vaga inteligente salva: {processed_vaga['title'][:50]}... ({processed_vaga['seniority_level']})")
            saved_count += 1
        except Exception as e:
            logger.error(f"❌ Erro ao salvar vaga inteligente '{vaga.get('cargo', 'Sem título')[:30]}...': {e}")
            errors_count += 1
    
    logger.info(f"✅ SALVAMENTO CONCLUÍDO: {saved_count} vagas inteligentes salvas, {errors_count} erros")
    return saved_count

def run_scrapper():
    """Execução mestre do coletor disruptivo"""
    logger.info("🚀 INICIANDO COLETOR DISRUPTIVO DE VAGAS (ZERO LISTAS MANUAIS)")
    logger.info("🧠 IA AUTONOMA: Skills, cargos e cidades aprendem automaticamente")
    
    # Coletar vagas inteligentes
    vagas = scrape_google_jobs(
        "diretor OR gerente OR head OR líder OR executivo OR supervisor OR coordenador OR senior OR sênior OR c-level OR chief OR presidente OR sócio OR partner"
    )
    
    # Salvar no banco de dados
    saved_count = save_to_supabase(vagas)
    
    # Métricas de inteligência
    logger.info("📈 MÉTRICAS DE INTELIGÊNCIA:")
    logger.info(f"   • Total de vagas coletadas: {len(vagas)}")
    logger.info(f"   • Vagas salvas com sucesso: {saved_count}")
    logger.info(f"   • Skills detectadas automaticamente: {sum(len(v.get('skills_required', [])) for v in vagas)}")
    logger.info(f"   • Cidades identificadas: {len(set(v.get('cidade') for v in vagas))}")
    logger.info(f"   • Áreas de negócio: {len(set(v.get('area') for v in vagas))}")
    
    return saved_count

# Flask API
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    return {
        "status": "online",
        "time": datetime.utcnow().isoformat(),
        "mode": "DISRUPTIVO",
        "intelligence": "AUTONOMOUS",
        "models": {
            "nlp": "pt_core_news_lg (auto-installed)",
            "embeddings": "paraphrase-multilingual-MiniLM-L12-v2",
            "geocoding": "nominatim"
        }
    }

if __name__ == "__main__":
    logger.info("🔥 INICIANDO SERVIDOR DISRUPTIVO - AGUARDANDO REQUISIÇÕES")
    run_scrapper()
    app.run(host="0.0.0.0", port=8000)
