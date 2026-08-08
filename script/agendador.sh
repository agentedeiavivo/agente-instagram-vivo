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
HOJE_UTC=$(date -u +%Y-%m-%d)
echo "Hora atual (UTC): $HORA_UTC"

# Corte de duplicidade: inicio da JANELA DE HOJE (nao uma janela rolante de
# N horas, nem "desde a meia-noite"). Motivo: uma publicacao atrasada de um
# dia anterior (ex.: carrossel que deveria ter saido as 18h30 de ontem mas
# so disparou de madrugada de hoje) NAO pode contar como "ja publicado hoje"
# e bloquear a janela de hoje — isso ja aconteceu de verdade em 2026-08-07
# e bloqueou o carrossel do dia por engano. Ancorar o "--since" no inicio da
# propria janela (10:20 UTC pra posts, 21:20 UTC pra carrosseis) resolve os
# dois problemas ao mesmo tempo: ignora publicacoes de outros horarios/dias,
# e ainda evita duplicar se o agendador rodar mais de uma vez dentro da
# mesma janela de ~40min.

# Janela dos posts: 10:20-10:59 UTC = 07:20-07:59 horario de Brasilia
if [[ "$HORA_UTC" > "10:19" && "$HORA_UTC" < "11:00" ]]; then
  JA_PUBLICOU=$(git log --since="${HOJE_UTC}T10:20:00" --grep="Post publicado automaticamente" --oneline)
  if [ -z "$JA_PUBLICOU" ]; then
    echo "Dentro da janela dos posts. Disparando postar-posts.yml..."
    gh workflow run postar-posts.yml --ref main
  else
    echo "Ja publicou um post na janela de hoje. Nada a fazer."
  fi
fi

# Janela dos carrosseis: 21:20-21:59 UTC = 18:20-18:59 horario de Brasilia
if [[ "$HORA_UTC" > "21:19" && "$HORA_UTC" < "22:00" ]]; then
  JA_PUBLICOU=$(git log --since="${HOJE_UTC}T21:20:00" --grep="Carrossel publicado automaticamente" --oneline)
  if [ -z "$JA_PUBLICOU" ]; then
    echo "Dentro da janela dos carrosseis. Disparando postar-carrosseis.yml..."
    gh workflow run postar-carrosseis.yml --ref main
  else
    echo "Ja publicou um carrossel na janela de hoje. Nada a fazer."
  fi
fi

echo "Verificacao concluida."
