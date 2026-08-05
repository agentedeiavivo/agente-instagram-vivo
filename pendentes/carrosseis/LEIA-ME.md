# Como adicionar um novo carrossel

Crie uma subpasta com um nome único, e dentro dela coloque as imagens do
carrossel (em ordem) + uma legenda:

```
carrossel-01-nome-do-tema/
    slide_01.png   (ou .jpg/.jpeg — a capa, primeira imagem do carrossel)
    slide_02.png
    slide_03.png
    ...
    caption.txt    (a legenda, em texto puro)
```

As imagens são publicadas na ordem alfabética dos nomes de arquivo dentro da
pasta — numere-as (`slide_01`, `slide_02`...) para controlar a ordem. O
Instagram aceita de 2 a 10 imagens por carrossel.

O agente publica o próximo carrossel pendente (em ordem alfabética do nome
da pasta) todos os dias às 18h30 (horário de Brasília). Depois de publicado,
a pasta inteira é movida automaticamente para `publicados/carrosseis/`.

**Atenção:** este repositório é público — qualquer imagem colocada aqui fica
acessível via URL direta antes de ser publicada no Instagram (necessário
para a API do Meta conseguir lê-la). Não é indexada, mas não é sigilosa.
