# app.py — Coletor de Vagas RICO (CTO da Eleva) — VERSÃO FINAL
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

# Criar clientes Supabase
supabase_read = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_write = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def extract_keywords(text):
    """Extração RICA de palavras-chave (sem NLP)"""
    if not text or not isinstance(text, str):
        return []
    
    # Banco de palavras-chave especializadas
    palavras_chave = [
        # Tecnologia
        "python", "javascript", "react", "vue", "angular", "node.js", "typescript", "java", "c#", "c++", 
        "sql", "nosql", "mongodb", "postgresql", "mysql", "aws", "azure", "gcp", "docker", "kubernetes", 
        "terraform", "jenkins", "git", "github", "gitlab", "devops", "ci/cd", "machine learning", "deep learning",
        "ia", "inteligência artificial", "data science", "big data", "spark", "hadoop", "tableau", "power bi",
        
        # Gestão e Negócios
        "gestão", "liderança", "equipe", "time", "pessoas", "rh", "recursos humanos", "liderança técnica",
        "gerência", "diretoria", "estratégia", "planejamento", "kpis", "metas", "orçamento", "finanças",
        "contabilidade", "controladoria", "m&a", "investimentos", "mergulho financeiro", "business intelligence",
        "bi", "crm", "salesforce", "marketing digital", "seo", "google ads", "social media", "vendas", "b2b", "b2c",
        
        # Habilidades Comportamentais
        "comunicação", "comunicação verbal", "apresentação", "negociação", "resolução de conflitos",
        "adaptabilidade", "resiliência", "criatividade", "inovação", "pensamento crítico", "tomada de decisão",
        "gestão de tempo", "organização", "multitarefa", "pressão", "deadline", "disponibilidade para viagens",
        
        # Idiomas e Certificações
        "inglês", "espanhol", "francês", "mandarim", "alemão", "fluente", "avançado", "intermediário", "básico",
        "toefl", "ielts", "pmp", "scrum", "agile", "six sigma", "mba", "mestrado", "doutorado", "phd",
        
        # Domínios de Negócio
        "saúde", "educação", "tecnologia", "finanças", "varejo", "logística", "energia", "sustentabilidade",
        "e-commerce", "startups", "scale-ups", "banco", "seguro", "imobiliário", "jurídico", "advocacia",
        "compliance", "governança", "risco", "auditoria"
    ]
    
    encontradas = []
    texto_lower = text.lower()
    
    for palavra in palavras_chave:
        if palavra in texto_lower:
            encontradas.append(palavra)
    
    return list(dict.fromkeys(encontradas))[:15]

def scrape_job_details(url, fonte):
    """Scraping PROFUNDO para dados RICOS"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Connection": "keep-alive"
        }
        
        time.sleep(2)
        
        for tentativa in range(3):
            try:
                res = requests.get(url, headers=headers, timeout=15)
                if res.status_code == 200:
                    break
                time.sleep(3)
            except Exception as e:
                logging.warning(f"Tentativa {tentativa+1} falhou: {e}")
                time.sleep(5)
        else:
            logging.error(f"❌ Todas as tentativas falharam para {url}")
            return {
                "descricao_completa": f"Erro ao coletar detalhes da vaga em {url}",
                "requisitos": ["Não foi possível extrair requisitos"],
                "beneficios": ["Não foi possível extrair benefícios"],
                "habilidades_extraidas": ["erro_coleta"],
                "salario": "Não informado",
                "modalidade": "Não informado"
            }
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Estratégias específicas por fonte
        if "linkedin.com/jobs" in url:
            return scrape_linkedin_job(soup, url)
        elif "gupy.com.br" in url:
            return scrape_gupy_job(soup, url)
        elif "talenses.com" in url:
            return scrape_talenses_job(soup, url)
        elif "vagas.com.br" in url:
            return scrape_vagas_job(soup, url)
        elif "glassdoor.com.br" in url:
            return scrape_glassdoor_job(soup, url)
        else:
            return scrape_generic_job(soup, url)
            
    except Exception as e:
        logging.error(f"❌ Erro ao coletar detalhes da vaga {url}: {e}")
        return {
            "descricao_completa": f"Erro durante a coleta: {str(e)}",
            "requisitos": ["Erro durante a coleta"],
            "beneficios": ["Erro durante a coleta"],
            "habilidades_extraidas": ["erro"],
            "salario": "Não informado",
            "modalidade": "Não informado"
        }

def scrape_linkedin_job(soup, url):
    """Estratégia RICA para LinkedIn Jobs"""
    try:
        descricao_div = soup.select_one("div.description__text")
        descricao = descricao_div.get_text(strip=True) if descricao_div else "Descrição não disponível no LinkedIn"
        
        requisitos = []
        sections = soup.select("section.core-section")
        for section in sections:
            section_title = section.select_one("h3")
            if section_title and "requisitos" in section_title.text.lower():
                requisitos = [li.get_text(strip=True) for li in section.select("li")]
                break
        
        if not requisitos:
            requisitos_elements = soup.select("li.application-requirements__item")
            requisitos = [elem.get_text(strip=True) for elem in requisitos_elements]
        
        beneficios = []
        benefits_section = soup.select_one("section.benefits-section")
        if benefits_section:
            beneficios = [li.get_text(strip=True) for li in benefits_section.select("li")]
        
        salario_elem = soup.select_one("span.salary")
        salario = salario_elem.get_text(strip=True) if salario_elem else "Não informado"
        
        modalidade = "Não informado"
        job_details = soup.select_one("ul.job-details-jobs")
        if job_details and "modalidade" in job_details.text.lower():
            modalidade = "Híbrido" if "híbrido" in job_details.text.lower() else "Presencial"
        
        return {
            "descricao_completa": descricao[:2000] + "..." if len(descricao) > 2000 else descricao,
            "requisitos": requisitos[:10],
            "beneficios": beneficios[:10],
            "habilidades_extraidas": extract_keywords(descricao),
            "salario": salario,
            "modalidade": modalidade
        }
    except Exception as e:
        logging.error(f"Erro no scraping do LinkedIn: {e}")
        return {
            "descricao_completa": "Erro ao coletar detalhes do LinkedIn",
            "requisitos": ["Erro"],
            "beneficios": ["Erro"],
            "habilidades_extraidas": ["linkedin_erro"],
            "salario": "Não informado",
            "modalidade": "Não informado"
        }

def scrape_gupy_job(soup, url):
    """Estratégia para Gupy"""
    try:
        descricao = ""
        description_sections = soup.select("div.description, div.job-description")
        for section in description_sections:
            descricao += section.get_text(strip=True) + "\n"
        
        if not descricao:
            main_content = soup.select_one("main")
            descricao = main_content.get_text(strip=True) if main_content else "Descrição não disponível"
        
        requisitos = []
        beneficios = []
        
        sections = soup.select("section")
        for section in sections:
            title = section.select_one("h2, h3")
            if title:
                title_text = title.text.lower()
                if "requisitos" in title_text or "requirements" in title_text:
                    requisitos = [li.get_text(strip=True) for li in section.select("li")]
                elif "benefícios" in title_text or "benefits" in title_text:
                    beneficios = [li.get_text(strip=True) for li in section.select("li")]
        
        salario = "Não informado"
        salario_elems = soup.select("span.salary, div.salary")
        for elem in salario_elems:
            if "R$" in elem.text or "salário" in elem.text.lower():
                salario = elem.text.strip()
                break
        
        modalidade = "Não informado"
        if "presencial" in descricao.lower():
            modalidade = "Presencial"
        elif "remoto" in descricao.lower():
            modalidade = "Remoto"
        elif "híbrido" in descricao.lower() or "hibrido" in descricao.lower():
            modalidade = "Híbrido"
        
        return {
            "descricao_completa": descricao[:2000] + "..." if len(descricao) > 2000 else descricao,
            "requisitos": requisitos[:10],
            "beneficios": beneficios[:10],
            "habilidades_extraidas": extract_keywords(descricao),
            "salario": salario,
            "modalidade": modalidade
        }
    except Exception as e:
        logging.error(f"Erro no scraping do Gupy: {e}")
        return {
            "descricao_completa": "Erro ao coletar detalhes do Gupy",
            "requisitos": ["Erro"],
            "beneficios": ["Erro"],
            "habilidades_extraidas": ["gupy_erro"],
            "salario": "Não informado",
            "modalidade": "Não informado"
        }

def scrape_talenses_job(soup, url):
    """Estratégia para Talenses"""
    try:
        descricao = ""
        description_div = soup.select_one("div.job-description, div.vacancy-description")
        if description_div:
            descricao = description_div.get_text(strip=True)
        else:
            main_content = soup.select_one("main article")
            descricao = main_content.get_text(strip=True) if main_content else "Descrição não encontrada"
        
        requisitos = []
        requirements_section = soup.select_one("section.requisitos, div.requirements")
        if requirements_section:
            requisitos = [li.get_text(strip=True) for li in requirements_section.select("li")]
        
        beneficios = []
        benefits_section = soup.select_one("section.beneficios, div.benefits")
        if benefits_section:
            beneficios = [li.get_text(strip=True) for li in benefits_section.select("li")]
        
        salario = "Não informado"
        modalidade = "Não informado"
        
        meta_tags = soup.select("meta[name='description'], meta[property='og:description']")
        for tag in meta_tags:
            content = tag.get("content", "").lower()
            if "salário" in content or "salario" in content:
                salario = "Salário a combinar"
            if "remoto" in content:
                modalidade = "Remoto"
            elif "presencial" in content:
                modalidade = "Presencial"
            elif "híbrido" in content:
                modalidade = "Híbrido"
        
        return {
            "descricao_completa": descricao[:2000] + "..." if len(descricao) > 2000 else descricao,
            "requisitos": requisitos[:10],
            "beneficios": beneficios[:10],
            "habilidades_extraidas": extract_keywords(descricao),
            "salario": salario,
            "modalidade": modalidade
        }
    except Exception as e:
        logging.error(f"Erro no scraping do Talenses: {e}")
        return {
            "descricao_completa": "Erro ao coletar detalhes do Talenses",
            "requisitos": ["Erro"],
            "beneficios": ["Erro"],
            "habilidades_extraidas": ["talenses_erro"],
            "salario": "Não informado",
            "modalidade": "Não informado"
        }

def scrape_vagas_job(soup, url):
    """Estratégia para Vagas.com.br"""
    try:
        descricao = ""
        description_div = soup.select_one("div.description, div.job-description")
        if description_div:
            descricao = description_div.get_text(strip=True)
        else:
            main_content = soup.select_one("main article")
            descricao = main_content.get_text(strip=True) if main_content else "Descrição não encontrada"
        
        requisitos = []
        requirements_section = soup.select_one("div.requisitos, div.requirements")
        if requirements_section:
            requisitos = [li.get_text(strip=True) for li in requirements_section.select("li")]
        
        beneficios = []
        benefits_section = soup.select_one("div.beneficios, div.benefits")
        if benefits_section:
            beneficios = [li.get_text(strip=True) for li in benefits_section.select("li")]
        
        salario = "Não informado"
        modalidade = "Não informado"
        
        # Detecção de modalidade
        if "remoto" in descricao.lower():
            modalidade = "Remoto"
        elif "presencial" in descricao.lower():
            modalidade = "Presencial"
        elif "híbrido" in descricao.lower():
            modalidade = "Híbrido"
        
        return {
            "descricao_completa": descricao[:2000] + "..." if len(descricao) > 2000 else descricao,
            "requisitos": requisitos[:10],
            "beneficios": beneficios[:10],
            "habilidades_extraidas": extract_keywords(descricao),
            "salario": salario,
            "modalidade": modalidade
        }
    except Exception as e:
        logging.error(f"Erro no scraping do Vagas.com.br: {e}")
        return {
            "descricao_completa": "Erro ao coletar detalhes do Vagas.com.br",
            "requisitos": ["Erro"],
            "beneficios": ["Erro"],
            "habilidades_extraidas": ["vagas_erro"],
            "salario": "Não informado",
            "modalidade": "Não informado"
        }

def scrape_glassdoor_job(soup, url):
    """Estratégia para Glassdoor"""
    try:
        descricao = ""
        description_div = soup.select_one("div.jobDescriptionContent, div.description")
        if description_div:
            descricao = description_div.get_text(strip=True)
        else:
            main_content = soup.select_one("main article")
            descricao = main_content.get_text(strip=True) if main_content else "Descrição não encontrada"
        
        requisitos = []
        requirements_section = soup.select_one("div.requisitos, div.requirements")
        if requirements_section:
            requisitos = [li.get_text(strip=True) for li in requirements_section.select("li")]
        
        beneficios = []
        benefits_section = soup.select_one("div.benefits, div.benefitsSection")
        if benefits_section:
            beneficios = [li.get_text(strip=True) for li in benefits_section.select("li")]
        
        salario = "Não informado"
        modalidade = "Não informado"
        
        # Detecção de modalidade
        if "remote" in descricao.lower():
            modalidade = "Remoto"
        elif "on-site" in descricao.lower():
            modalidade = "Presencial"
        elif "hybrid" in descricao.lower():
            modalidade = "Híbrido"
        
        return {
            "descricao_completa": descricao[:2000] + "..." if len(descricao) > 2000 else descricao,
            "requisitos": requisitos[:10],
            "beneficios": beneficios[:10],
            "habilidades_extraidas": extract_keywords(descricao),
            "salario": salario,
            "modalidade": modalidade
        }
    except Exception as e:
        logging.error(f"Erro no scraping do Glassdoor: {e}")
        return {
            "descricao_completa": "Erro ao coletar detalhes do Glassdoor",
            "requisitos": ["Erro"],
            "beneficios": ["Erro"],
            "habilidades_extraidas": ["glassdoor_erro"],
            "salario": "Não informado",
            "modalidade": "Não informado"
        }

def scrape_generic_job(soup, url):
    """Fallback para sites genéricos"""
    try:
        descricao = ""
        candidates = [
            "div.description", "div.job-description", "div.content", "article",
            "section.description", "div.job-details", "div.vacancy-description",
            "div.main-content", "div.job-post-description"
        ]
        
        for selector in candidates:
            elements = soup.select(selector)
            if elements:
                descricao = "\n".join([elem.get_text(strip=True) for elem in elements])
                if len(descricao) > 200:
                    break
        
        if not descricao:
            main = soup.select_one("main, #main, .main")
            if main:
                descricao = main.get_text(strip=True)
        
        requisitos = []
        beneficios = []
        
        sections = re.split(r'\n\s*\n', descricao)
        for section in sections:
            lower_section = section.lower()
            if "requisito" in lower_section or "requirement" in lower_section:
                requisitos = [line.strip() for line in section.split("\n") if line.strip() and len(line.strip()) > 10][:5]
            elif "benefício" in lower_section or "beneficio" in lower_section or "benefit" in lower_section:
                beneficios = [line.strip() for line in section.split("\n") if line.strip() and len(line.strip()) > 10][:5]
        
        salario = "Não informado"
        modalidade = "Não informado"
        
        if "salário" in descricao.lower() or "salario" in descricao.lower():
            salario = "Salário a combinar"
        if "remoto" in descricao.lower():
            modalidade = "Remoto"
        elif "presencial" in descricao.lower():
            modalidade = "Presencial"
        elif "híbrido" in descricao.lower() or "hibrido" in descricao.lower():
            modalidade = "Híbrido"
        
        return {
            "descricao_completa": descricao[:2000] + "..." if len(descricao) > 2000 else descricao,
            "requisitos": requisitos,
            "beneficios": beneficios,
            "habilidades_extraidas": extract_keywords(descricao),
            "salario": salario,
            "modalidade": modalidade
        }
    except Exception as e:
        logging.error(f"Erro no scraping genérico: {e}")
        return {
            "descricao_completa": f"Erro genérico: {str(e)}",
            "requisitos": ["Erro"],
            "beneficios": ["Erro"],
            "habilidades_extraidas": ["generico_erro"],
            "salario": "Não informado",
            "modalidade": "Não informado"
        }

def scrape_google_jobs(query, days_back=1, max_results=100):
    """Busca RICA no Google usando SerpAPI"""
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
        "site:talenses.com/vagas",
        "site:talenses.com/jobs"
    ]
    
    for source in sources:
        search_query = f'{query} {source} after:{yesterday}'
        logging.info(f"🔍 Buscando no Google (via SerpAPI): {search_query}")
        
        try:
            url = f"https://serpapi.com/search.json?q={urllib.parse.quote(search_query)}&hl=pt-BR&num=20&api_key={SERPAPI_KEY}"
            res = requests.get(url, timeout=20)
            data = res.json()
            
            if "organic_results" in data:
                for result in data["organic_results"][:25]:
                    link = result.get("link", "")
                    title = result.get("title", "Vaga executiva")
                    
                    if not link or "google.com" in link or "url?" in link or len(link) < 10:
                        continue
                    
                    fonte = "Google"
                    if "linkedin.com/jobs" in link:
                        fonte = "LinkedIn"
                    elif "gupy.com.br" in link:
                        fonte = "Gupy"
                    elif "talenses.com" in link:
                        fonte = "Talenses"
                    elif "vagas.com.br" in link:
                        fonte = "Vagas.com.br"
                    elif "glassdoor.com.br" in link:
                        fonte = "Glassdoor"
                    elif "indeed.com" in link:
                        fonte = "Indeed"
                    elif "trampos.co" in link:
                        fonte = "Trampos.co"
                    elif "ciadetalentos.com.br" in link:
                        fonte = "Cia de Talentos"
                    
                    details = scrape_job_details(link, fonte)
                    
                    senioridade = "Sênior+"
                    title_lower = title.lower()
                    descricao_lower = details["descricao_completa"].lower()
                    
                    if any(kw in title_lower for kw in ["diretor", "head", "c-level", "chief", "vp", "vice-presidente"]):
                        senioridade = "Diretor/VP"
                    elif any(kw in title_lower for kw in ["gerente", "manager", "head of"]):
                        senioridade = "Gerente"
                    elif any(kw in title_lower for kw in ["coordenador", "coordinator"]):
                        senioridade = "Coordenador"
                    elif any(kw in title_lower for kw in ["sênior", "senior", "sr.", "sr"]):
                        senioridade = "Sênior"
                    elif any(kw in title_lower for kw in ["pleno", "mid-level"]):
                        senioridade = "Pleno"
                    elif any(kw in title_lower for kw in ["júnior", "junior", "jr.", "jr", "estágio", "estagiário"]):
                        senioridade = "Júnior/Estágio"
                    else:
                        if "5+ anos" in descricao_lower or "mínimo de 5 anos" in descricao_lower:
                            senioridade = "Sênior"
                        elif "3+ anos" in descricao_lower or "mínimo de 3 anos" in descricao_lower:
                            senioridade = "Pleno"
                    
                    localizacao = "Brasil"
                    if "são paulo" in title_lower or "são paulo" in descricao_lower:
                        localizacao = "São Paulo - SP"
                    elif "rio de janeiro" in title_lower or "rio de janeiro" in descricao_lower:
                        localizacao = "Rio de Janeiro - RJ"
                    elif "brasília" in title_lower or "brasília" in descricao_lower:
                        localizacao = "Brasília - DF"
                    
                    job_record = {
                        "cargo": title.strip()[:100],
                        "empresa": "Não informado",
                        "salario": details["salario"][:50],
                        "modalidade": details["modalidade"][:30],
                        "data_publicacao": yesterday,
                        "localizacao": localizacao,
                        "senioridade": senioridade,
                        "requisitos": json.dumps(details["requisitos"], ensure_ascii=False),
                        "experiencias": json.dumps(details["habilidades_extraidas"], ensure_ascii=False),
                        "descricao_completa": details["descricao_completa"],
                        "beneficios": json.dumps(details["beneficios"], ensure_ascii=False),
                        "habilidades_extraidas": json.dumps(details["habilidades_extraidas"], ensure_ascii=False),
                        "link_candidatura": link[:255],
                        "fonte": fonte,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    all_jobs.append(job_record)
                    logging.info(f"✅ Coletada vaga RICA: {title[:50]}... ({fonte})")
                    
                    time.sleep(2)
                    
                    if len(all_jobs) >= max_results:
                        return all_jobs
            
            time.sleep(3)
            
        except Exception as e:
            logging.error(f"❌ Erro na busca do Google/SerpAPI para {source}: {e}")
            time.sleep(5)
    
    return all_jobs

def scrape_talenses_direct():
    """Coleta DIRETA do site Talenses"""
    logging.info("🔍 Coletando vagas DIRETAMENTE do site Talenses")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }
    
    try:
        url = "https://talenses.com/vagas"
        res = requests.get(url, headers=headers, timeout=15)
        
        if res.status_code != 200:
            logging.warning(f"⚠️ Talenses retornou status {res.status_code} - tentando URL alternativa")
            url = "https://talenses.com/jobs"
            res = requests.get(url, headers=headers, timeout=15)
        
        if res.status_code != 200:
            logging.error(f"❌ Falha ao acessar Talenses: status {res.status_code}")
            return []
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        jobs = []
        job_elements = soup.select(
            "div.vacancy-card, "
            "div.job-card, "
            "div.vaga-item, "
            "article.vaga, "
            "div.job-listing, "
            ".job-posting"
        )
        
        logging.info(f"🔍 Encontrados {len(job_elements)} elementos de vagas no Talenses")
        
        for elem in job_elements[:30]:
            try:
                title_elem = elem.select_one("h2, h3, h4, a.title, .job-title")
                link_elem = elem.select_one("a[href*='/vaga/'], a[href*='/jobs/']")
                
                if not title_elem or not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link_path = link_elem.get("href", "").strip()
                link = urllib.parse.urljoin("https://talenses.com", link_path)
                
                details = scrape_job_details(link, "Talenses")
                
                job_record = {
                    "cargo": title[:100],
                    "empresa": "Talenses",
                    "salario": details["salario"][:50],
                    "modalidade": details["modalidade"][:30],
                    "data_publicacao": datetime.now().strftime("%Y-%m-%d"),
                    "localizacao": "Brasil",
                    "senioridade": "Não informado",
                    "requisitos": json.dumps(details["requisitos"], ensure_ascii=False),
                    "experiencias": json.dumps(details["habilidades_extraidas"], ensure_ascii=False),
                    "descricao_completa": details["descricao_completa"],
                    "beneficios": json.dumps(details["beneficios"], ensure_ascii=False),
                    "habilidades_extraidas": json.dumps(details["habilidades_extraidas"], ensure_ascii=False),
                    "link_candidatura": link[:255],
                    "fonte": "Talenses (coleta direta)",
                    "created_at": datetime.now().isoformat()
                }
                
                jobs.append(job_record)
                logging.info(f"✅ Talenses: {title[:50]}...")
                time.sleep(2)
            
            except Exception as e:
                logging.error(f"❌ Erro ao processar vaga do Talenses: {e}")
                continue
        
        logging.info(f"✅ Total de {len(jobs)} vagas coletadas DIRETAMENTE do Talenses")
        return jobs
    
    except Exception as e:
        logging.error(f"❌ Erro CRÍTICO ao coletar do Talenses: {e}")
        return []

def scrape_all_sources():
    """Função mestre para coletar dados RICOS de TODAS as fontes"""
    logging.info("🚀 INICIANDO COLETA RICA DE VAGAS EXECUTIVAS (MÁXIMA QUALIDADE)")
    all_jobs = []    
    google_jobs = scrape_google_jobs(
        "diretor OR gerente OR head OR líder OR executivo OR supervisor OR coordenador OR senior OR sênior OR c-level OR chief",
        days_back=1,
        max_results=80
    )
    logging.info(f"✅ Google/SerpAPI: {len(google_jobs)} vagas RICAS")
    all_jobs.extend(google_jobs)    
    talenses_jobs = scrape_talenses_direct()
    all_jobs.extend(talenses_jobs)    
    logging.info(f"📊 TOTAL de vagas RICAS coletadas: {len(all_jobs)}")
    return all_jobs

def run_scrapper():
    """Executa a coleta RICA e salva no Supabase"""
    all_jobs = scrape_all_sources()    
    saved_count = 0
    errors_count = 0
    
    for job in all_jobs:
        try:
            supabase_write.table("vagas").insert(job).execute()
            logging.info(f"💾 Vaga RICA salva no Supabase: {job['cargo'][:50]}... ({job['fonte']})")
            saved_count += 1
        except Exception as e:
            logging.error(f"❌ Erro ao salvar vaga no Supabase: {e}")
            errors_count += 1
    
    logging.info(f"✅ COLETA FINALIZADA: {saved_count} vagas RICAS salvas no Supabase! ({errors_count} erros)")
    return saved_count

# Flask API
app = Flask(__name__)

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """API para consulta de vagas RICAS"""
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
        logging.info(f"🔍 API retornou {len(jobs)} vagas para consulta: q='{q}', location='{location}', senioridade='{senioridade}'")
        return jsonify(jobs)
    
    except Exception as e:
        logging.error(f"❌ Erro na API /api/jobs: {e}")
        return jsonify({"error": "Erro ao buscar vagas", "details": str(e)}), 500

@app.route("/api/job-details/<job_id>", methods=["GET"])
def get_job_details(job_id):
    """API para detalhes RICOS de uma vaga específica"""
    try:
        response = supabase_read.table("vagas").select("*").eq("id", job_id).execute()
        job = response.data[0] if response.data else None
        
        if not job:
            return jsonify({"error": "Vaga não encontrada"}), 404
        
        if job.get("requisitos"):
            job["requisitos"] = json.loads(job["requisitos"])
        if job.get("beneficios"):
            job["beneficios"] = json.loads(job["beneficios"])
        if job.get("habilidades_extraidas"):
            job["habilidades_extraidas"] = json.loads(job["habilidades_extraidas"])
        
        return jsonify(job)
    
    except Exception as e:
        logging.error(f"❌ Erro na API /api/job-details/{job_id}: {e}")
        return jsonify({"error": "Erro ao buscar detalhes da vaga", "details": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de saúde do serviço"""
    return {
        "status": "online",
        "time": datetime.now().isoformat(),
        "message": "✅ Eleva Scraper está online e coletando vagas RICAS!"
    }

if __name__ == "__main__":
    logging.info("🔥 INICIANDO SERVIDOR - AGUARDANDO REQUISIÇÕES")
    run_scrapper()
    app.run(host="0.0.0.0", port=8000)
