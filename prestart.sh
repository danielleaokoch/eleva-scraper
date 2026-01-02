#!/bin/bash
echo "🚀 Instalando dependências críticas..."
pip install spacy
echo "📥 Baixando modelo NLP em português..."
python -m spacy download pt_core_news_lg --quiet
echo "✅ Modelo NLP instalado com sucesso!"
