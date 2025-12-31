# scrapper.py
import requests
from bs4 import BeautifulSoup
import time
import json
import logging

# Configurar logs
logging.basicConfig(level=logging.INFO)

def scrape_trabalha_brasil():
    """Fonte 100% aberta do governo brasileiro"""
    url = "https://api.trabalhabrasil.com.br/v1/Job/List"
    try:
        response = requests.post(url, json={
            "filters": {"uf": "", "job": "", "page": 1, "pageSize": 100}
        })
        jobs = []
        for item in response.json().get("data", []):
            jobs.append({
                "title": item.get("tituloVaga", ""),
                "company": "Não informado",
                "location": f"{item.get('municipio', '')} - {item.get('uf', '')}",
                "level": "Não informado",
                "source": "Trabalha Brasil",
                "url": f"https://www.trabalhabrasil.com.br/vagas/{item.get('idVaga', '')}",
                "date_posted": item.get("dataPublicacao", "")
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
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            res = requests.get(url, headers=headers)
            soup = BeautifulSoup(res.text, "html.parser")
            for div in soup.select("div.job_seen_beacon"):
                title = div.select_one("h2 a")?.get("title") or "Não informado"
                company = div.select_one("span.companyName")?.text or "Não informado"
                loc = div.select_one("div.companyLocation")?.text or "Brasil"
                link = "https://br.indeed.com" + (div.select_one("h2 a")?.get("href") or "")
                jobs.append({
                    "title": title,
                    "company": company,
                    "location": loc,
                    "level": "Não informado",
                    "source": "Indeed",
                    "url": link,
                    "date_posted": "Recente"
                })
            time.sleep(5)  # respeitar o site
        except Exception as e:
            logging.error(f"Erro Indeed: {e}")
    return jobs[:50]  # limite seguro

# Roda todas as fontes
all_jobs = []
all_jobs.extend(scrape_trabalha_brasil())
all_jobs.extend(scrape_indeed_brasil())

# Salva em arquivo JSON (vamos carregar no banco depois)
with open("vagas_do_dia.json", "w", encoding="utf-8") as f:
    json.dump(all_jobs, f, ensure_ascii=False, indent=2)

print(f"✅ Coletadas {len(all_jobs)} vagas!")
