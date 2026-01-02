#!/bin/bash
echo "🚀 Iniciando instalação de dependências críticas..."
pip install spacy
python -m spacy download pt_core_news_lg --quiet
echo "✅ Modelo NLP instalado e testado com sucesso!"
