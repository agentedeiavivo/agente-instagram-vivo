#!/usr/bin/env python3
"""
Agente de Marketing Instagram — Framework VIVO
Lê a pasta pendentes/, escolhe o próximo post (imagem + legenda), publica no
Instagram via Graph API oficial da Meta, e move o par publicado para publicados/.

Convenção de arquivos em pendentes/:
    post-01.jpg  (ou .jpeg / .png)
    post-01.txt  (legenda em texto puro, mesmo nome-base da imagem)

Um post por execução (o workflow do GitHub Actions roda 2x por dia).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import requests

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}

REPO_ROOT = Path(__file__).resolve().parent.parent
PENDENTES_DIR = REPO_ROOT / "pendentes"
PUBLICADOS_DIR = REPO_ROOT / "publicados"


def log(msg: str) -> None:
    print(f"[agente-instagram] {msg}", flush=True)


def erro_fatal(msg: str) -> None:
    print(f"[agente-instagram] ERRO: {msg}", flush=True)
    sys.exit(1)


def carregar_configuracao() -> dict:
    access_token = os.environ.get("IG_ACCESS_TOKEN")
    ig_user_id = os.environ.get("IG_BUSINESS_ACCOUNT_ID")

    if not access_token or not ig_user_id:
        erro_fatal(
            "Faltam variáveis de ambiente IG_ACCESS_TOKEN e/ou IG_BUSINESS_ACCOUNT_ID "
            "(devem vir dos GitHub Secrets)."
        )

    github_repository = os.environ.get("GITHUB_REPOSITORY")  # ex.: agentedeiavivo/agente-instagram-vivo
    branch = os.environ.get("GITHUB_REF_NAME", "main")

    if not github_repository:
        erro_fatal("Variável GITHUB_REPOSITORY não encontrada (esperado quando rodando no GitHub Actions).")

    return {
        "access_token": access_token,
        "ig_user_id": ig_user_id,
        "github_repository": github_repository,
        "branch": branch,
    }


def encontrar_proximo_post() -> tuple[Path, Path] | None:
    """Retorna (arquivo_imagem, arquivo_legenda) do próximo post pendente, em ordem alfabética."""
    if not PENDENTES_DIR.exists():
        return None

    imagens = sorted(
        p for p in PENDENTES_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    for imagem in imagens:
        legenda = imagem.with_suffix(".txt")
        if legenda.exists():
            return imagem, legenda
        else:
            log(f"Aviso: '{imagem.name}' não tem legenda correspondente ('{legenda.name}'). Pulando.")

    return None


def montar_url_publica(imagem: Path, config: dict) -> str:
    caminho_relativo = imagem.relative_to(REPO_ROOT).as_posix()
    return f"https://raw.githubusercontent.com/{config['github_repository']}/{config['branch']}/{caminho_relativo}"


def criar_container_de_midia(image_url: str, legenda: str, config: dict) -> str:
    url = f"{GRAPH_API_BASE}/{config['ig_user_id']}/media"
    resp = requests.post(
        url,
        data={
            "image_url": image_url,
            "caption": legenda,
            "access_token": config["access_token"],
        },
        timeout=60,
    )
    dados = resp.json()
    if resp.status_code != 200 or "id" not in dados:
        erro_fatal(f"Falha ao criar container de mídia: {dados}")
    return dados["id"]


def aguardar_container_pronto(creation_id: str, config: dict, tentativas: int = 10, intervalo_s: int = 5) -> None:
    url = f"{GRAPH_API_BASE}/{creation_id}"
    for tentativa in range(1, tentativas + 1):
        resp = requests.get(
            url,
            params={"fields": "status_code", "access_token": config["access_token"]},
            timeout=30,
        )
        dados = resp.json()
        status = dados.get("status_code")
        log(f"Status do container ({tentativa}/{tentativas}): {status}")
        if status == "FINISHED":
            return
        if status == "ERROR":
            erro_fatal(f"Container de mídia falhou no processamento: {dados}")
        time.sleep(intervalo_s)
    erro_fatal("Container de mídia não ficou pronto (status FINISHED) dentro do tempo esperado.")


def publicar_container(creation_id: str, config: dict) -> str:
    url = f"{GRAPH_API_BASE}/{config['ig_user_id']}/media_publish"
    resp = requests.post(
        url,
        data={"creation_id": creation_id, "access_token": config["access_token"]},
        timeout=60,
    )
    dados = resp.json()
    if resp.status_code != 200 or "id" not in dados:
        erro_fatal(f"Falha ao publicar o post: {dados}")
    return dados["id"]


def mover_para_publicados(imagem: Path, legenda: Path) -> None:
    PUBLICADOS_DIR.mkdir(exist_ok=True)
    for arquivo in (imagem, legenda):
        destino = PUBLICADOS_DIR / arquivo.name
        arquivo.rename(destino)
        log(f"Movido: {arquivo.relative_to(REPO_ROOT)} -> {destino.relative_to(REPO_ROOT)}")


def commit_e_push() -> None:
    comandos = [
        ["git", "config", "user.name", "agente-instagram-vivo"],
        ["git", "config", "user.email", "agente-instagram-vivo@users.noreply.github.com"],
        ["git", "add", "pendentes", "publicados"],
        ["git", "commit", "-m", "Post publicado automaticamente: move item de pendentes/ para publicados/"],
        ["git", "push"],
    ]
    for cmd in comandos:
        resultado = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        if resultado.returncode != 0:
            # 'nothing to commit' não deve derrubar o processo
            if "nothing to commit" in resultado.stdout + resultado.stderr:
                log("Nada para commitar (inesperado, mas seguindo em frente).")
                continue
            erro_fatal(f"Comando git falhou: {' '.join(cmd)}\n{resultado.stdout}\n{resultado.stderr}")


def main() -> None:
    config = carregar_configuracao()

    proximo = encontrar_proximo_post()
    if proximo is None:
        log("Nenhum post pendente encontrado em pendentes/. Nada a fazer.")
        return

    imagem, legenda_arquivo = proximo
    legenda_texto = legenda_arquivo.read_text(encoding="utf-8").strip()

    log(f"Próximo post: {imagem.name}")
    image_url = montar_url_publica(imagem, config)
    log(f"URL pública da imagem: {image_url}")

    creation_id = criar_container_de_midia(image_url, legenda_texto, config)
    log(f"Container de mídia criado: {creation_id}")

    aguardar_container_pronto(creation_id, config)

    post_id = publicar_container(creation_id, config)
    log(f"Post publicado com sucesso. ID: {post_id}")

    mover_para_publicados(imagem, legenda_arquivo)
    commit_e_push()

    log("Concluído.")


if __name__ == "__main__":
    main()
