# app.py — Coletor de Vagas para Matching Perfeito (Padrão Unicórnio)
# Última atualização: 02/01/2026
# Este código coleta, processa e prepara dados para matching 10/10 conforme especificação Lovable

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
from typing import Dict, List, Optional, Any
import numpy as np

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
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SCRAPERAPI_KEY = os.getenv("SCRAPERAPI_KEY")

# Verificar variáveis obrigatórias
required_vars = {
    "SERPAPI_KEY": SERPAPI_KEY,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_ANON_KEY": SUPABASE_ANON_KEY,
    "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    logger.error(f"❌ Variáveis de ambiente não configuradas: {', '.join(missing_vars)}")
    exit(1)

# Criar clientes Supabase
supabase_read = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_write = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# ⚙️ Configurações do coletor (AJUSTÁVEL PELO CTO)
MAX_VAGAS_POR_FONTE = 8  # ⭐⭐⭐ MÁXIMO DE VAGAS POR FONTE/SITE
MAX_VAGAS_TOTAIS = 120   # ⭐⭐⭐ MÁXIMO TOTAL DE VAGAS POR EXECUÇÃO
DELAY_ENTRE_REQUISICOES = 4  # segundos (respeitar sites)
MIN_QUALIDADE_SCORE = 0.4  # Descartar vagas abaixo deste score

# 🌐 Fontes de vagas com filtros geográficos embutidos
SOURCES_BRASIL = [
    ("site:linkedin.com/jobs", "brasil OR brazil OR são paulo OR rio de janeiro OR brasília"),
    ("site:gupy.com.br", ""),
    ("site:vagas.com.br", ""),
    ("site:trampos.co", ""),
    ("site:ciadetalentos.com.br", ""),
    ("site:glassdoor.com.br", "brasil OR brazil"),
    ("site:br.indeed.com", "brasil OR brazil"),
    ("site:roberthalf.com.br", ""),
    ("site:michaelpage.com.br", ""),
    ("site:talenses.com", "brasil OR brazil"),
    ("site:hays.com.br", ""),
    ("site:exec.com.br", ""),
    ("site:kornferry.com", "brazil OR brasil"),
    ("site:spencerstuart.com", "brazil OR brasil"),
    ("site:heidrick.com", "brazil OR brasil"),
    ("site:russellreynolds.com", "brazil OR brasil"),
    ("site:pageexecutive.com", "brazil OR brasil"),
    ("site:foxhumancapital.com", "brasil OR brazil"),
    ("site:workable.com", "brasil OR brazil"),
    ("site:novare.com.br", ""),
    ("site:pulsobrasil.com.br", ""),
    ("site:recrutabrasil.com.br", ""),
    ("site:curriculo.99jobs.com", ""),
    ("site:empregos.com.br", "")
]

# 🤖 Dicionários especializados para NLP leve (sem dependências pesadas)
SENIORITY_RULES = [...]  # (como definido acima)
SKILLS_DATABASE = [...]  # (como definido acima)

def is_vaga_brasil(text: str) -> bool:
    """Verificação rigorosa de localização brasileira"""
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

def generate_uuid(title: str, url: str, posted_at: str) -> str:
    """Gera um ID único baseado no conteúdo da vaga"""
    import hashlib
    hash_input = f"{title.lower().strip()}{url}{posted_at}"
    return hashlib.md5(hash_input.encode()).hexdigest()

def calculate_quality_score(vaga: Dict) -> float:
    """Calcula score de qualidade baseado em critérios do Lovable"""
    score = 0.0
    
    # Descrição completa (>200 caracteres)
    if len(vaga.get("description", "")) > 200:
        score += 0.2
    
    # Skills identificadas
    if vaga.get("skills_required") and len(vaga["skills_required"]) > 0:
        score += 0.3
    
    # Salário divulgado
    if vaga.get("salary_disclosed") and vaga["salary_disclosed"]:
        score += 0.2
    
    # Localização clara
    if vaga.get("city") and vaga.get("state"):
        score += 0.15
    
    # Modelo de trabalho definido
    if vaga.get("work_model") and vaga["work_model"] in ["remote", "hybrid", "onsite"]:
        score += 0.15
    
    return min(score, 1.0)

def process_job_for_lovable(raw_vaga: Dict) -> Dict:
    """Processa vaga para o formato exato do Lovable"""
    processed = {
        # 1. Identificação e Metadados
        "id": generate_uuid(raw_vaga["title"], raw_vaga["link"], raw_vaga["data_publicacao"]),
        "external_id": f"{raw_vaga['fonte']}_{hash(raw_vaga['link'])}",
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
        "title_english": "",  # Deixar vazio para processamento futuro
        "seniority_level": detect_seniority(raw_vaga["descricao_completa"], raw_vaga["cargo"]),
        "area": detect_area(raw_vaga["descricao_completa"], raw_vaga["cargo"]),  # Função a ser implementada
        "sub_area": "",  # Inferir com NLP futuro
        "sub_area_level_2": "",
        "sub_area_level_3": "",
        
        # 3. Informações da Empresa
        "company_name": raw_vaga["empresa"] if raw_vaga["empresa"] != "Não informado" else extract_company(raw_vaga["descricao_completa"]),
        "company_name_normalized": normalize_company_name(raw_vaga["empresa"]) if raw_vaga["empresa"] != "Não informado" else "",
        "company_size": "",  # Inferir futuramente
        "industry_sector": "",  # Inferir futuramente
        "market_type": "",  # Inferir futuramente
        "company_logo_url": "",
        "is_headhunter": raw_vaga["fonte"] in ["Korn Ferry", "Spencer Stuart", "Egon Zehnder", "Heidrick & Struggles"],
        "is_tech_specialized": raw_vaga["fonte"] in ["LinkedIn", "Gupy", "Trampos.co", "Glassdoor"],
        
        # 4. Localização e Modelo de Trabalho
        "city": extract_city(raw_vaga["descricao_completa"], raw_vaga["localizacao"]),
        "state": extract_state(raw_vaga["descricao_completa"], raw_vaga["localizacao"]),
        "country": "Brasil",
        "region": extract_region(raw_vaga["localizacao"]),
        "work_model": detect_work_model(raw_vaga["descricao_completa"], raw_vaga["modalidade"]),
        "is_remote_eligible": "remoto" in raw_vaga["modalidade"].lower() or "remoto" in raw_vaga["descricao_completa"].lower(),
        "remote_countries": ["Brasil"],
        
        # 5. Remuneração e Benefícios
        "salary_min": raw_vaga["salario_min"] if "salario_min" in raw_vaga else None,
        "salary_max": raw_vaga["salario_max"] if "salario_max" in raw_vaga else None,
        "salary_median": raw_vaga["salario_median"] if "salario_median" in raw_vaga else None,
        "salary_disclosed": bool(raw_vaga.get("salario_min")),
        "salary_type": "CLT",
        "currency": "BRL",
        "benefits": extract_benefits(raw_vaga["descricao_completa"], raw_vaga.get("beneficios", [])),
        
        # 6. Skills e Requisitos
        "skills_required": extract_skills(raw_vaga["descricao_completa"]),
        "experience_years_min": extract_experience_years(raw_vaga["descricao_completa"]),
        "experience_years_max": None,
        
        # 7. Qualificações
        "education_required": extract_education(raw_vaga["descricao_completa"]),
        "certifications_required": [],
        "languages_required": extract_languages(raw_vaga["descricao_completa"]),
        
        # 8. Conteúdo e Descrição
        "description": raw_vaga["descricao_completa"],
        "description_summary": generate_summary(raw_vaga["descricao_completa"]),  # Função a ser implementada
        "responsibilities": extract_responsibilities(raw_vaga["descricao_completa"]),
        "requirements_raw": "",  # Pode ser extraído da descrição
        "benefits_description": "",
        "culture_keywords": extract_culture_keywords(raw_vaga["descricao_completa"]),
        
        # 9. Embeddings e AI (serão preenchidos em lote futuramente)
        "embedding": [],
        "skills_embedding": [],
        "culture_embedding": [],
        
        # 10. Métricas e Analytics
        "view_count": 0,
        "application_count": 0,
        "competition_level": "alta" if raw_vaga["fonte"] == "LinkedIn" else ("média" if raw_vaga["fonte"] == "Indeed" else "baixa"),
        "market_demand_score": 0,
        "avg_match_score_platform": 0.0,
        
        # Campos de timestamp
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Calcular qualidade
    processed["quality_score"] = calculate_quality_score(processed)
    
    return processed

def scrape_with_serpapi(query: str, location_filter: str = "", after_date: str = "") -> List[Dict]:
    """Coleta inteligente usando SerpAPI com proxy rotativo"""
    session = get_proxy_session()
    all_jobs = []
    
    url = f"https://serpapi.com/search.json?q={urllib.parse.quote(query)}&location={urllib.parse.quote(location_filter)}&hl=pt-BR&gl=br&num=20&api_key={SERPAPI_KEY}"
    
    try:
        logger.info(f"🔍 Buscando no Google (via SerpAPI): {query} {location_filter}")
        res = session.get(url, timeout=20)
        data = res.json()
        
        if "organic_results" not in 
            logger.warning(f"⚠️ Nenhum resultado para query: {query}")
            return []
        
        for result in data["organic_results"]:
            link = result.get("link", "")
            title = result.get("title", "").strip()
            snippet = result.get("snippet", "")
            
            # Filtro de qualidade imediato
            if not link or len(link) < 10 or "google.com" in link or "url?" in link:
                continue
            
            # Filtro geográfico rigoroso
            if not is_vaga_brasil(title + " " + snippet):
                logger.info(f"🌍 Ignorando vaga internacional: {title[:50]}...")
                continue
            
            # Filtro de relevância executiva
            if not is_vaga_executiva(title):
                logger.info(f"🏢 Ignorando vaga não executiva: {title[:50]}...")
                continue
            
            # Extrair detalhes da vaga
            details = scrape_job_details(link, session)
            
            # Montar registro
            job_record = {
                "cargo": title,
                "empresa": extract_company_from_result(result),
                "link_candidatura": link,
                "data_publicacao": after_date,
                "localizacao": extract_location_from_result(result),
                "descricao_completa": details["descricao_completa"],
                "fonte": detect_source(link),
                "salario": details["salario"],
                "modalidade": details["modalidade"],
                "requisitos": details["requisitos"]
            }
            
            all_jobs.append(job_record)
            
            if len(all_jobs) >= MAX_VAGAS_POR_FONTE:
                break
    
    except Exception as e:
        logger.error(f"❌ Erro na busca SerpAPI: {e}")
    
    return all_jobs

def run_scrapper():
    """Função mestre de coleta inteligente"""
    logger.info("🚀 INICIANDO COLETA INTELIGENTE PARA MATCHING PERFEITO")
    logger.info("🎯 Foco: Vagas executivas no Brasil com dados completos para Lovable")
    
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    all_vagas_processed = []
    
    # 1. Coletar de fontes estratégicas
    for source, location_filter in SOURCES_BRASIL:
        if len(all_vagas_processed) >= MAX_VAGAS_TOTAIS:
            break
        
        # Construir query com palavras-chave executivas
        query = f"diretor OR gerente OR head OR líder OR executivo OR supervisor OR coordenador OR senior OR sênior OR c-level OR chief {source}"
        
        # Coletar vagas
        raw_vagas = scrape_with_serpapi(query, location_filter, yesterday)
        logger.info(f"✅ Coletadas {len(raw_vagas)} vagas brutas de {source}")
        
        # 2. Processar cada vaga para formato Lovable
        for raw_vaga in raw_vagas:
            try:
                processed_vaga = process_job_for_lovable(raw_vaga)
                
                # Filtro de qualidade final
                if processed_vaga["quality_score"] >= MIN_QUALIDADE_SCORE:
                    all_vagas_processed.append(processed_vaga)
                    logger.info(f"⭐ Vaga processada: {processed_vaga['title'][:50]}... (Qualidade: {processed_vaga['quality_score']:.1f})")
                else:
                    logger.info(f"🗑️ Descartada vaga de baixa qualidade: {raw_vaga['cargo'][:50]}")
            except Exception as e:
                logger.error(f"❌ Erro ao processar vaga '{raw_vaga.get('cargo', 'Sem título')}': {e}")
        
        time.sleep(5)  # Respeitar SerpAPI
    
    logger.info(f"📊 TOTAL DE VAGAS PROCESSADAS: {len(all_vagas_processed)}")
    
    # 3. Salvar no Supabase (com batch processing)
    if all_vagas_processed:
        try:
            # Batch insert para performance
            result = supabase_write.table("vagas_lovable").upsert(all_vagas_processed).execute()
            logger.info(f"✅ Salvadas {len(result.data)} vagas no Supabase")
            
            # 4. Gerar relatório de qualidade
            quality_metrics = {
                "total_vagas": len(all_vagas_processed),
                "media_qualidade": sum(v["quality_score"] for v in all_vagas_processed) / len(all_vagas_processed),
                "fontes": list(set(v["source"] for v in all_vagas_processed)),
                "seniority_distribution": {},
                "area_distribution": {}
            }
            
            for vaga in all_vagas_processed:
                # Seniority distribution
                level = vaga["seniority_level"]
                quality_metrics["seniority_distribution"][level] = quality_metrics["seniority_distribution"].get(level, 0) + 1
                
                # Area distribution
                area = vaga["area"]
                quality_metrics["area_distribution"][area] = quality_metrics["area_distribution"].get(area, 0) + 1
            
            logger.info("📈 MÉTRICAS DE QUALIDADE:")
            logger.info(f"   • Total de vagas: {quality_metrics['total_vagas']}")
            logger.info(f"   • Qualidade média: {quality_metrics['media_qualidade']:.2f}/1.0")
            logger.info(f"   • Fontes: {', '.join(quality_metrics['fontes'])}")
            logger.info(f"   • Distribuição por senioridade: {quality_metrics['seniority_distribution']}")
            logger.info(f"   • Distribuição por área: {quality_metrics['area_distribution']}")
        
        except Exception as e:
            logger.error(f"❌ Erro ao salvar no Supabase: {e}")
    
    return len(all_vagas_processed)

# Flask API (simplificada para este exemplo)
app = Flask(__name__)

@app.route("/health", methods=["GET"])
def health_check():
    return {
        "status": "online",
        "time": datetime.utcnow().isoformat(),
        "message": "✅ Coletor Inteligente de Vagas para Lovable está online!",
        "config": {
            "max_vagas_por_fonte": MAX_VAGAS_POR_FONTE,
            "max_vagas_totais": MAX_VAGAS_TOTAIS,
            "min_qualidade_score": MIN_QUALIDADE_SCORE,
            "fontes_configuradas": len(SOURCES_BRASIL)
        }
    }

if __name__ == "__main__":
    logger.info("🔥 INICIANDO SERVIDOR - AGUARDANDO REQUISIÇÕES")
    run_scrapper()
    app.run(host="0.0.0.0", port=8000)
