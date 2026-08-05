# Como adicionar um novo post

Coloque aqui dois arquivos com o **mesmo nome-base**:

```
post-01.jpg   (ou .jpeg / .png)
post-01.txt   (a legenda, em texto puro)
```

O agente publica o próximo post pendente (em ordem alfabética do nome do
arquivo) todos os dias às 07h30 (horário de Brasília). Depois de publicado,
o par imagem+legenda é movido automaticamente para `publicados/posts/`.

(Carrosséis são diferentes — veja `pendentes/carrosseis/LEIA-ME.md`. Eles
são publicados às 18h30.)

Dica: numere os arquivos (`post-01`, `post-02`, `post-03`...) para controlar
a ordem de publicação.

**Atenção:** este repositório é público, então qualquer imagem colocada aqui
fica visível (via URL direta) antes mesmo de ser publicada no Instagram —
é assim que a API do Meta consegue "ver" a imagem para publicá-la. Não é
listada/indexada, mas não é privada. Evite colocar aqui conteúdo que precise
ficar 100% em sigilo até o lançamento.
