#!/usr/bin/env bash
set -e

# Diretório base do projeto
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================="
echo "      BaseGov - Inicializador do Sistema   "
echo "=========================================="

# 1. Verifica ambiente virtual Python
if [ -d ".venv" ]; then
    PYTHON_BIN="./.venv/bin/python"
elif command -v python3 &> /dev/null; then
    PYTHON_BIN="python3"
else
    echo "❌ Erro: Python não encontrado."
    exit 1
fi

# Menu de opções caso passe argumentos ou execute interativo
echo "Selecione uma opção:"
echo "1) Atualizar toda a base (Rodar ingestão / recortar imagens)"
echo "2) Iniciar o Bot do Telegram"
echo "3) Iniciar a API (FastAPI)"
echo "4) Iniciar tudo (Atualizar base + Iniciar Bot do Telegram)"
echo "5) Limpar apenas o Cache"
echo "------------------------------------------"

ACTION="${1:-}"

if [ -z "$ACTION" ]; then
    read -rp "Digite o número da opção desejada [1-5]: " ACTION
fi

case "$ACTION" in
    1)
        echo -e "\n🔄 Atualizando toda a base de dados vetoriais e imagens..."
        $PYTHON_BIN ingest.py
        echo -e "\n✅ Base atualizada com sucesso!"
        ;;
    2)
        echo -e "\n🤖 Iniciando o Bot do Telegram..."
        $PYTHON_BIN bot.py
        ;;
    3)
        echo -e "\n🚀 Iniciando a API FastAPI na porta 8000..."
        if [ -f "./.venv/bin/uvicorn" ]; then
            ./.venv/bin/uvicorn api:app --host 0.0.0.0 --port 8000 --reload
        else
            $PYTHON_BIN -m uvicorn api:app --host 0.0.0.0 --port 8000 --reload
        fi
        ;;
    4)
        echo -e "\n🔄 Passo 1/2: Atualizando a base..."
        $PYTHON_BIN ingest.py
        echo -e "\n🤖 Passo 2/2: Iniciando o Bot do Telegram..."
        $PYTHON_BIN bot.py
        ;;
    5)
        echo -e "\n🧹 Limpando cache de respostas..."
        $PYTHON_BIN -c "import cache; cache.clear(); print('Cache SQLite limpo com sucesso!')"
        ;;
    *)
        echo "Opção inválida: $ACTION"
        exit 1
        ;;
esac
