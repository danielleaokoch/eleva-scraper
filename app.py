# api.py
from flask import Flask, jsonify, request
import json

app = Flask(__name__)

# Carrega vagas do dia
def load_jobs():
    try:
        with open("vagas_do_dia.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    jobs = load_jobs()
    
    # Filtros via URL: ?q=desenvolvedor&location=São Paulo&level=Pleno
    q = request.args.get("q", "").lower()
    location = request.args.get("location", "").lower()
    level = request.args.get("level", "").lower()

    filtered = []
    for job in jobs:
        if q and q not in job["title"].lower():
            continue
        if location and location not in job["location"].lower():
            continue
        if level and level not in job["level"].lower():
            continue
        filtered.append(job)
    
    return jsonify(filtered[:100])  # máximo 100 por busca

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
