# Como adicionar um novo post

Há dois formatos possíveis, e os dois convivem na mesma pasta.

## Post único

Dois arquivos com o **mesmo nome-base**:

```
post-01.jpg   (ou .jpeg / .png)
post-01.txt   (a legenda, em texto puro)
```

## Carrossel (2 a 10 slides)

Um arquivo de imagem por slide, numerado, mais **uma única legenda** pro carrossel inteiro:

```
carrossel-01_1.jpg
carrossel-01_2.jpg
carrossel-01_3.jpg
...
carrossel-01.txt     (legenda única, sem sufixo de número)
```

A numeração dos slides (`_1`, `_2`, `_3`...) tem que ser sequencial a partir de 1, sem pular número.

## Ordem de publicação

O agente publica o próximo item pendente (post único OU carrossel inteiro) em ordem
alfabética do nome-base — a cada execução, 07h30 e 18h30 (horário de Brasília). Um
carrossel inteiro conta como 1 publicação, igual a um post único.

Depois de publicado, todos os arquivos daquele item (imagem(ns) + legenda) são movidos
automaticamente para `publicados/`.

**Dica:** numere os arquivos (`post-01`, `post-02`, `carrossel-01`, `carrossel-02`...)
pra controlar a ordem. Como "carrossel" vem antes de "post" alfabeticamente, itens
`carrossel-*` tendem a furar a fila na frente de `post-*` de mesmo número — não é um
problema, só um detalhe de ordenação.

**Atenção:** este repositório é público, então qualquer imagem colocada aqui fica
visível (via URL direta) antes mesmo de ser publicada no Instagram — é assim que a
API do Meta consegue "ver" a imagem para publicá-la. Não é listada/indexada, mas não
é privada. Evite colocar aqui conteúdo que precise ficar 100% em sigilo até o
lançamento.
