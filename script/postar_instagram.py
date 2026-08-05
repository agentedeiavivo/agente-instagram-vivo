#!/usr/bin/env python3
"""
Agente de Marketing Instagram — Framework VIVO

Dois modos de execução:
    python postar_instagram.py --modo posts        (rodado às 07h30)
    python postar_instagram.py --modo carrosseis    (rodado às 18h30)

Modo "posts": lê pendentes/posts/, escolhe o próximo par imagem+legenda
(mesmo nome-base), publica como post único e move o par para
publicados/posts/.

Modo "carrosseis": lê pendentes/carrosseis/, escolhe a próxima subpasta
(carrossel-01-.../slide_01.png ... slide_NN.png + caption.txt), publica
como carrossel (2 a 10 imagens) e move a pasta inteira para
publicados/carrosseis/.

Em ambos os casos: publica via Instagram Graph API oficial da Meta
(`image_url` = raw.githubusercontent.com da própria imagem no repo — por
isso o repo precisa ser público) e commita a mudança usando o GITHUB_TOKEN
padrão do Actions.
"""

import argparse
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
PENDENTES_POSTS_DIR = REPO_ROOT / "pendentes" / "posts"
PUBLICADOS_POSTS_DIR = REPO_ROOT / "publicados" / "posts"
PENDENTES_CARROSSEIS_DIR = REPO_ROOT / "pendentes" / "carrosseis"
PUBLICADOS_CARROSSEIS_DIR = REPO_ROOT / "publicados" / "carrosseis"


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


def montar_url_publica(caminho: Path, config: dict) -> str:
    caminho_relativo = caminho.relative_to(REPO_ROOT).as_posix()
    return f"https://raw.githubusercontent.com/{config['github_repository']}/{config['branch']}/{caminho_relativo}"


def criar_container_de_midia(image_url: str, config: dict, caption: str | None = None, is_carousel_item: bool = False) -> str:
    dados_form = {
        "image_url": image_url,
        "access_token": config["access_token"],
    }
    if caption is not None:
        dados_form["caption"] = caption
    if is_carousel_item:
        dados_form["is_carousel_item"] = "true"

    url = f"{GRAPH_API_BASE}/{config['ig_user_id']}/media"
    resp = requests.post(url, data=dados_form, timeout=60)
    dados = resp.json()
    if resp.status_code != 200 or "id" not in dados:
        erro_fatal(f"Falha ao criar container de mídia: {dados}")
    return dados["id"]


def criar_container_de_carrossel(children_ids: list[str], caption: str, config: dict) -> str:
    url = f"{GRAPH_API_BASE}/{config['ig_user_id']}/media"
    resp = requests.post(
        url,
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
            "access_token": config["access_token"],
        },
        timeout=60,
    )
    dados = resp.json()
    if resp.status_code != 200 or "id" not in dados:
        erro_fatal(f"Falha ao criar container de carrossel: {dados}")
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
        log(f"Status do container {creation_id} ({tentativa}/{tentativas}): {status}")
        if status == "FINISHED":
            return
        if status == "ERROR":
            erro_fatal(f"Container de mídia falhou no processamento: {dados}")
        time.sleep(intervalo_s)
    erro_fatal(f"Container {creation_id} não ficou pronto (status FINISHED) dentro do tempo esperado.")


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


def commit_e_push(mensagem: str) -> None:
    comandos = [
        ["git", "config", "user.name", "agente-instagram-vivo"],
        ["git", "config", "user.email", "agente-instagram-vivo@users.noreply.github.com"],
        ["git", "add", "pendentes", "publicados"],
        ["git", "commit", "-m", mensagem],
        ["git", "push"],
    ]
    for cmd in comandos:
        resultado = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        if resultado.returncode != 0:
            if "nothing to commit" in resultado.stdout + resultado.stderr:
                log("Nada para commitar (inesperado, mas seguindo em frente).")
                continue
            erro_fatal(f"Comando git falhou: {' '.join(cmd)}\n{resultado.stdout}\n{resultado.stderr}")


# ---------------------------------------------------------------------------
# Modo "posts" (imagem única)
# ---------------------------------------------------------------------------

def encontrar_proximo_post() -> tuple[Path, Path] | None:
    if not PENDENTES_POSTS_DIR.exists():
        return None

    imagens = sorted(
        p for p in PENDENTES_POSTS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    for imagem in imagens:
        legenda = imagem.with_suffix(".txt")
        if legenda.exists():
            return imagem, legenda
        log(f"Aviso: '{imagem.name}' não tem legenda correspondente ('{legenda.name}'). Pulando.")

    return None


def mover_post_para_publicados(imagem: Path, legenda: Path) -> None:
    PUBLICADOS_POSTS_DIR.mkdir(parents=True, exist_ok=True)
    for arquivo in (imagem, legenda):
        destino = PUBLICADOS_POSTS_DIR / arquivo.name
        arquivo.rename(destino)
        log(f"Movido: {arquivo.relative_to(REPO_ROOT)} -> {destino.relative_to(REPO_ROOT)}")


def executar_modo_posts(config: dict) -> None:
    proximo = encontrar_proximo_post()
    if proximo is None:
        log("Nenhum post pendente encontrado em pendentes/posts/. Nada a fazer.")
        return

    imagem, legenda_arquivo = proximo
    legenda_texto = legenda_arquivo.read_text(encoding="utf-8").strip()

    log(f"Próximo post: {imagem.name}")
    image_url = montar_url_publica(imagem, config)
    log(f"URL pública da imagem: {image_url}")

    creation_id = criar_container_de_midia(image_url, config, caption=legenda_texto)
    log(f"Container de mídia criado: {creation_id}")

    aguardar_container_pronto(creation_id, config)

    post_id = publicar_container(creation_id, config)
    log(f"Post publicado com sucesso. ID: {post_id}")

    mover_post_para_publicados(imagem, legenda_arquivo)
    commit_e_push("Post publicado automaticamente: move item de pendentes/posts/ para publicados/posts/")

    log("Concluído.")


# ---------------------------------------------------------------------------
# Modo "carrosseis" (múltiplas imagens)
# ---------------------------------------------------------------------------

def encontrar_proximo_carrossel() -> Path | None:
    if not PENDENTES_CARROSSEIS_DIR.exists():
        return None

    pastas = sorted(
        p for p in PENDENTES_CARROSSEIS_DIR.iterdir()
        if p.is_dir()
    )

    for pasta in pastas:
        legenda = pasta / "caption.txt"
        imagens = sorted(
            p for p in pasta.iterdir()
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
        if not legenda.exists():
            log(f"Aviso: pasta '{pasta.name}' não tem 'caption.txt'. Pulando.")
            continue
        if len(imagens) < 2:
            log(f"Aviso: pasta '{pasta.name}' tem menos de 2 imagens (mínimo do Instagram). Pulando.")
            continue
        if len(imagens) > 10:
            log(f"Aviso: pasta '{pasta.name}' tem mais de 10 imagens (máximo do Instagram). Pulando.")
            continue
        return pasta

    return None


def mover_carrossel_para_publicados(pasta: Path) -> None:
    PUBLICADOS_CARROSSEIS_DIR.mkdir(parents=True, exist_ok=True)
    destino = PUBLICADOS_CARROSSEIS_DIR / pasta.name
    pasta.rename(destino)
    log(f"Movido: {pasta.relative_to(REPO_ROOT)} -> {destino.relative_to(REPO_ROOT)}")


def executar_modo_carrosseis(config: dict) -> None:
    pasta = encontrar_proximo_carrossel()
    if pasta is None:
        log("Nenhum carrossel pendente encontrado em pendentes/carrosseis/. Nada a fazer.")
        return

    legenda_texto = (pasta / "caption.txt").read_text(encoding="utf-8").strip()
    imagens = sorted(
        p for p in pasta.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    log(f"Próximo carrossel: {pasta.name} ({len(imagens)} imagens)")

    children_ids = []
    for imagem in imagens:
        image_url = montar_url_publica(imagem, config)
        log(f"Criando item do carrossel a partir de: {image_url}")
        child_id = criar_container_de_midia(image_url, config, is_carousel_item=True)
        aguardar_container_pronto(child_id, config, tentativas=8, intervalo_s=3)
        children_ids.append(child_id)

    log(f"{len(children_ids)} itens criados. Criando container do carrossel...")
    creation_id = criar_container_de_carrossel(children_ids, legenda_texto, config)
    log(f"Container de carrossel criado: {creation_id}")

    aguardar_container_pronto(creation_id, config, tentativas=15, intervalo_s=5)

    post_id = publicar_container(creation_id, config)
    log(f"Carrossel publicado com sucesso. ID: {post_id}")

    mover_carrossel_para_publicados(pasta)
    commit_e_push("Carrossel publicado automaticamente: move pasta de pendentes/carrosseis/ para publicados/carrosseis/")

    log("Concluído.")


# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--modo", choices=["posts", "carrosseis"], required=True)
    args = parser.parse_args()

    config = carregar_configuracao()

    if args.modo == "posts":
        executar_modo_posts(config)
    else:
        executar_modo_carrosseis(config)


if __name__ == "__main__":
    main()
