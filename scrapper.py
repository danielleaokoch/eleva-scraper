# scrapper.py
import requests
from bs4 import BeautifulSoup
import time
import json
import logging

# Configurar logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_trabalha_brasil():
    """Fonte 100% aberta do governo brasileiro"""
    url = "https://api.trabalhabrasil.com.br/v1/Job/List"
    try:
        response = requests.post(url, json={
            "filters": {"uf": "", "job": "", "page": 1, "pageSize": 100}
        }, timeout=10)
        jobs = []
        for item in response.json().get("data", []):
            jobs.append({
                "title": item.get("tituloVaga", "").strip(),
                "company": item.get("nomeEmpresa", "Não informado").strip(),
                "location": f"{item.get('municipio', '')} - {item.get('uf', '')}".strip(),
                "level": item.get("nivel", "Não informado").strip(),
                "source": "Trabalha Brasil",
                "url": f"https://www.trabalhabrasil.com.br/vagas/{item.get('idVaga', '')}",
                "date_posted": item.get("dataPublicacao", "").split("T")[0] if item.get("dataPublicacao") else "Recente",
                "salary": item.get("salario", "Não informado")
            })
        return jobs
    except Exception as e:
        logging.error(f"Erro Trabalha Brasil: {e}")
        return []

def scrape_indeed_brasil(job="desenvolvedor", location="Brasil", pages=2):
    """Coleta do Indeed Brasil (público)"""
    jobs = []
    for page in range(pages):
        url = f"https://br.indeed.com/jobs?q={job}&l={location}&start={page*10}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            for div in soup.select("div.job_seen_beacon"):
                title = div.select_one("h2 a")?.get("title") or "Não informado"
                company = div.select_one("span.companyName")?.text or "Não informado"
                loc = div.select_one("div.companyLocation")?.text or "Brasil"
                link = "https://br.indeed.com" + (div.select_one("h2 a")?.get("href") or "")
                level = "Não informado"
                # Tentar extrair nível (ex: Júnior, Pleno, Sênior)
                if "júnior" in title.lower() or "jr" in title.lower():
                    level = "Júnior"
                elif "pleno" in title.lower():
                    level = "Pleno"
                elif "sênior" in title.lower() or "sr" in title.lower():
                    level = "Sênior"
                
                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": loc.strip(),
                    "level": level,
                    "source": "Indeed",
                    "url": link,
                    "date_posted": "Recente",
                    "salary": "Não informado"
                })
            time.sleep(5)  # respeitar o site
        except Exception as e:
            logging.error(f"Erro Indeed: {e}")
    return jobs[:50]

def scrape_glassdoor(job="desenvolvedor", location="Brasil", pages=1):
    """Coleta do Glassdoor (público, com cuidado)"""
    jobs = []
    for page in range(pages):
        url = f"https://www.glassdoor.com.br/Job/{job}-jobs-SRCH_KO0,10.htm?locT={location}&locId="
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            res = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(res.text, "html.parser")
            for job_card in soup.select("li.react-job-listing"):
                title = job_card.select_one("a.jobLink")?.get("title") or "Não informado"
                company = job_card.select_one("div.employerName")?.text or "Não informado"
                loc = job_card.select_one("div.location")?.text or "Brasil"
                link = "https://www.glassdoor.com.br" + (job_card.select_one("a.jobLink")?.get("href") or "")
                level = "Não informado"
                jobs.append({
                    "title": title.strip(),
                    "company": company.strip(),
                    "location": loc.strip(),
                    "level": level,
                    "source": "Glassdoor",
                    "url": link,
                    "date_posted": "Recente",
                    "salary": "Não informado"
                })
            time.sleep(10)  # Glassdoor é mais sensível
        except Exception as e:
            logging.error(f"Erro Glassdoor: {e}")
    return jobs[:20]

# Roda todas as fontes
all_jobs = []
all_jobs.extend(scrape_trabalha_brasil())
all_jobs.extend(scrape_indeed_brasil(job="engenheiro de software", location="Brasil"))
all_jobs.extend(scrape_glassdoor(job="analista de dados", location="Brasil"))

# Salva em arquivo JSON (vamos carregar no banco depois)
with open("vagas_do_dia.json", "w", encoding="utf-8") as f:
    json.dump(all_jobs, f, ensure_ascii=False, indent=2)

print(f"✅ Coletadas {len(all_jobs)} vagas!")
