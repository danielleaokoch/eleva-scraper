#!/bin/bash
echo "🚀 Iniciando instalação de dependências críticas..."

# Forçar atualização do pip
pip install --upgrade pip

# Instalar spaCy
pip install spacy

# Baixar modelo NLP em português (com --force para garantir)
python -m spacy download pt_core_news_lg --force

# Verificar instalação
if python -c "import spacy; spacy.load('pt_core_news_lg'); print('✅ Modelo NLP carregado com sucesso!')" &> /dev/null; then
    echo "✅ Modelo NLP instalado e testado com sucesso!"
else
    echo "❌ Falha ao instalar o modelo NLP. O serviço pode não funcionar corretamente."
    exit 1
fi

echo "✨ Preparação concluída!"
