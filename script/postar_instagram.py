#!/usr/bin/env python3
"""
Agente de Marketing Instagram — Framework VIVO
Lê a pasta pendentes/, escolhe o próximo item (post único OU carrossel),
publica no Instagram via Graph API oficial da Meta, e move os arquivos
publicados para publicados/.

Convenção de arquivos em pendentes/:
    Post único:
        post-01.jpg  (ou .jpeg / .png)
        post-01.txt  (legenda em texto puro, mesmo nome-base da imagem)

    Carrossel (2 a 10 slides):
        carrossel-01_1.jpg  carrossel-01_2.jpg  ...  carrossel-01_N.jpg
        carrossel-01.txt    (legenda única do carrossel, sem sufixo de slide)

Um item por execução (post único OU carrossel inteiro conta como 1 execução;
o workflow do GitHub Actions roda 2x por dia). Itens são escolhidos em ordem
alfabética do nome-base (ex.: "carrossel-01" vem antes de "post-01").
"""

import os
import re
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

POST_RE = re.compile(r"^(post-\d+)\.(jpg|jpeg|png)$", re.IGNORECASE)
CAROUSEL_SLIDE_RE = re.compile(r"^(carrossel-\d+)_(\d+)\.(jpg|jpeg|png)$", re.IGNORECASE)


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


def encontrar_proximo_item() -> dict | None:
    """
    Varre pendentes/ e retorna o próximo item completo (post único ou carrossel),
    em ordem alfabética do nome-base. Formato do retorno:
        {"tipo": "post", "imagem": Path, "legenda": Path}
        {"tipo": "carrossel", "imagens": [Path, ...], "legenda": Path}
    Ignora arquivos incompletos (imagem sem legenda, ou carrossel com slide faltando)
    com um aviso, e continua procurando o próximo candidato.
    """
    if not PENDENTES_DIR.exists():
        return None

    arquivos = [p for p in PENDENTES_DIR.iterdir() if p.is_file()]

    posts: dict[str, Path] = {}
    carrosseis: dict[str, dict[int, Path]] = {}

    for p in arquivos:
        m_post = POST_RE.match(p.name)
        if m_post:
            posts[m_post.group(1)] = p
            continue
        m_slide = CAROUSEL_SLIDE_RE.match(p.name)
        if m_slide:
            base, indice = m_slide.group(1), int(m_slide.group(2))
            carrosseis.setdefault(base, {})[indice] = p

    candidatos: list[tuple[str, dict]] = []

    for base, imagem in posts.items():
        legenda = imagem.with_suffix(".txt")
        if legenda.exists():
            candidatos.append((base, {"tipo": "post", "imagem": imagem, "legenda": legenda}))
        else:
            log(f"Aviso: '{imagem.name}' não tem legenda correspondente ('{legenda.name}'). Pulando.")

    for base, slides_dict in carrosseis.items():
        legenda = PENDENTES_DIR / f"{base}.txt"
        indices = sorted(slides_dict.keys())
        sequencia_ok = indices == list(range(1, len(indices) + 1))
        if not sequencia_ok:
            log(f"Aviso: carrossel '{base}' tem slides fora de sequência ({indices}). Pulando.")
            continue
        if not legenda.exists():
            log(f"Aviso: carrossel '{base}' não tem legenda correspondente ('{base}.txt'). Pulando.")
            continue
        if len(indices) < 2:
            log(f"Aviso: carrossel '{base}' tem só 1 slide — trate como post único. Pulando.")
            continue
        if len(indices) > 10:
            log(f"Aviso: carrossel '{base}' tem mais de 10 slides (limite da API). Pulando.")
            continue
        imagens_em_ordem = [slides_dict[i] for i in indices]
        candidatos.append((base, {"tipo": "carrossel", "imagens": imagens_em_ordem, "legenda": legenda}))

    if not candidatos:
        return None

    candidatos.sort(key=lambda c: c[0])
    return candidatos[0][1]


def montar_url_publica(imagem: Path, config: dict) -> str:
    caminho_relativo = imagem.relative_to(REPO_ROOT).as_posix()
    return f"https://raw.githubusercontent.com/{config['github_repository']}/{config['branch']}/{caminho_relativo}"


def criar_container_de_midia(image_url: str, legenda: str, config: dict) -> str:
    """Cria o container de um post único (com legenda embutida)."""
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


def criar_item_de_carrossel(image_url: str, config: dict) -> str:
    """Cria o container de UM slide de carrossel (sem legenda — a legenda vai só no pai)."""
    url = f"{GRAPH_API_BASE}/{config['ig_user_id']}/media"
    resp = requests.post(
        url,
        data={
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": config["access_token"],
        },
        timeout=60,
    )
    dados = resp.json()
    if resp.status_code != 200 or "id" not in dados:
        erro_fatal(f"Falha ao criar item de carrossel: {dados}")
    return dados["id"]


def criar_container_pai_carrossel(children_ids: list[str], legenda: str, config: dict) -> str:
    url = f"{GRAPH_API_BASE}/{config['ig_user_id']}/media"
    resp = requests.post(
        url,
        data={
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": legenda,
            "access_token": config["access_token"],
        },
        timeout=60,
    )
    dados = resp.json()
    if resp.status_code != 200 or "id" not in dados:
        erro_fatal(f"Falha ao criar container pai do carrossel: {dados}")
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


def mover_para_publicados(arquivos: list[Path]) -> None:
    PUBLICADOS_DIR.mkdir(exist_ok=True)
    for arquivo in arquivos:
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
            if "nothing to commit" in resultado.stdout + resultado.stderr:
                log("Nada para commitar (inesperado, mas seguindo em frente).")
                continue
            erro_fatal(f"Comando git falhou: {' '.join(cmd)}\n{resultado.stdout}\n{resultado.stderr}")


def publicar_post_unico(item: dict, config: dict) -> None:
    imagem, legenda_arquivo = item["imagem"], item["legenda"]
    legenda_texto = legenda_arquivo.read_text(encoding="utf-8").strip()

    log(f"Próximo item: post único — {imagem.name}")
    image_url = montar_url_publica(imagem, config)
    log(f"URL pública da imagem: {image_url}")

    creation_id = criar_container_de_midia(image_url, legenda_texto, config)
    log(f"Container de mídia criado: {creation_id}")

    aguardar_container_pronto(creation_id, config)

    post_id = publicar_container(creation_id, config)
    log(f"Post publicado com sucesso. ID: {post_id}")

    mover_para_publicados([imagem, legenda_arquivo])


def publicar_carrossel(item: dict, config: dict) -> None:
    imagens, legenda_arquivo = item["imagens"], item["legenda"]
    legenda_texto = legenda_arquivo.read_text(encoding="utf-8").strip()

    log(f"Próximo item: carrossel com {len(imagens)} slides — base '{imagens[0].stem.rsplit('_', 1)[0]}'")

    children_ids = []
    for imagem in imagens:
        image_url = montar_url_publica(imagem, config)
        log(f"Criando item de carrossel: {imagem.name} -> {image_url}")
        child_id = criar_item_de_carrossel(image_url, config)
        log(f"Item de carrossel criado: {child_id}")
        children_ids.append(child_id)

    creation_id = criar_container_pai_carrossel(children_ids, legenda_texto, config)
    log(f"Container pai do carrossel criado: {creation_id}")

    aguardar_container_pronto(creation_id, config)

    post_id = publicar_container(creation_id, config)
    log(f"Carrossel publicado com sucesso. ID: {post_id}")

    mover_para_publicados(imagens + [legenda_arquivo])


def main() -> None:
    config = carregar_configuracao()

    item = encontrar_proximo_item()
    if item is None:
        log("Nenhum item pendente encontrado em pendentes/. Nada a fazer.")
        return

    if item["tipo"] == "post":
        publicar_post_unico(item, config)
    else:
        publicar_carrossel(item, config)

    commit_e_push()
    log("Concluído.")


if __name__ == "__main__":
    main()
