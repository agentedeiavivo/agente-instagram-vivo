#!/usr/bin/env bash
set -e

if [ "${FORCAR_MODO:-nenhum}" = "posts" ]; then
  echo "Forcado manualmente: disparando postar-posts.yml sem checar janela/duplicidade."
  gh workflow run postar-posts.yml --ref main
  exit 0
fi

if [ "${FORCAR_MODO:-nenhum}" = "carrosseis" ]; then
  echo "Forcado manualmente: disparando postar-carrosseis.yml sem checar janela/duplicidade."
  gh workflow run postar-carrosseis.yml --ref main
  exit 0
fi

HORA_UTC=$(date -u +%H:%M)
echo "Hora atual (UTC): $HORA_UTC"

# Janela dos posts: 10:20-10:59 UTC = 07:20-07:59 horario de Brasilia
if [[ "$HORA_UTC" > "10:19" && "$HORA_UTC" < "11:00" ]]; then
  JA_PUBLICOU=$(git log --since="20 hours ago" --grep="Post publicado automaticamente" --oneline)
  if [ -z "$JA_PUBLICOU" ]; then
    echo "Dentro da janela dos posts. Disparando postar-posts.yml..."
    gh workflow run postar-posts.yml --ref main
  else
    echo "Ja publicou um post nas ultimas 20h. Nada a fazer."
  fi
fi

# Janela dos carrosseis: 21:20-21:59 UTC = 18:20-18:59 horario de Brasilia
if [[ "$HORA_UTC" > "21:19" && "$HORA_UTC" < "22:00" ]]; then
  JA_PUBLICOU=$(git log --since="20 hours ago" --grep="Carrossel publicado automaticamente" --oneline)
  if [ -z "$JA_PUBLICOU" ]; then
    echo "Dentro da janela dos carrosseis. Disparando postar-carrosseis.yml..."
    gh workflow run postar-carrosseis.yml --ref main
  else
    echo "Ja publicou um carrossel nas ultimas 20h. Nada a fazer."
  fi
fi

echo "Verificacao concluida."
