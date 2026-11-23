# Observatório Nacional da Formação em Fisioterapia

Site estático data-driven com indicadores de acesso territorial, qualidade e cobertura
assistencial dos cursos de Fisioterapia no Brasil.

Projeto irmão — e independente — do
[Observatório Nacional da Formação Farmacêutica](https://github.com/esidiao/observatorio-formacao-farmaceutica).
Compartilha o método e o design system; não compartilha código, dados nem dependências.

## O que este observatório mede

| | Fisioterapia (Censo 2024 · CPC 2023 · CNES 202610) |
|---|---|
| Registros no Censo | 5.870 |
| UFs com oferta **presencial** | **27** de 27 |
| Municípios com oferta presencial | 380 |
| Vagas presenciais | 164.661 |
| Vagas EaD (atribuídas à UF-sede) | 272.000 |
| **% da capacidade a distância** | **62,3%** |
| Polos de EaD | 4.837 registros em 1.561 municípios |
| Matrículas / concluintes | 227.223 / 24.425 |
| IES distintas | 763 |
| Cursos avaliados no CPC 2023 | 711, em **todas** as 27 UFs |

### A escala muda o que as páginas precisam dizer

Este é o maior curso de saúde da família de observatórios: 711 cursos avaliados
contra 74 da Fonoaudiologia e 452 da Odontologia. Três consequências não são
escolha editorial, são imposição do dado.

**Não existe seção de "UF sem oferta".** A Fonoaudiologia precisa dela — Amapá,
Mato Grosso do Sul e Roraima não têm curso nenhum, e omiti-los faria o país
parecer coberto. Aqui as 27 UFs têm curso presencial e curso avaliado. O que
separa os estados não é *ter*, é escala, concentração e qualidade.

**A EaD é o fato central, não uma ressalva.** 62,3% da capacidade é a
distância, atrás apenas de Administração na família. Na Odontologia a
modalidade é zero medido e fica fora da matriz de correlação por não ter
variância; aqui é o contrário, e errar a camada de `TP_DIMENSAO` não daria uma
imprecisão de margem — daria um país com um terço das vagas que tem.

**Presença não é cobertura, e a distância entre as duas é o achado.** Há curso
presencial em 380 municípios e polo de EaD em 1.561 — quatro vezes mais. A
manchete do sítio carrega os dois números de propósito: publicar só o
presencial subestimaria o alcance, e publicar só o total esconderia que quase
todo esse alcance é a distância.

## Estrutura

```
/etl                        Scripts ETL (Python): extração, índices, pipeline
/data                       Dados versionados: nacional.json, _proveniencia.json
/etl/dados                  Recortes brutos — NÃO versionados (ver .gitignore)
/site                       Gerador estático (Python/Jinja2) + templates + assets
/site/dist                  Site gerado — NÃO versionar
/tests                      Portão de qualidade (GO) + integridade + verificador de fontes
/.github/workflows/ci.yml   CI: valida -> constrói -> publica
```

## Fontes

| Indicador | Fonte | Acesso |
|---|---|---|
| Oferta, vagas, matrículas, polos | Censo da Educação Superior 2024 (INEP) | HTTPS, ZIP lido por `Range` |
| CPC, IDD, ENADE, perfil docente | CPC 2023 (INEP), área FISIOTERAPIA | HTTPS |
| Força de trabalho no SUS | CNES — vínculos nas **nove** ocupações de fisioterapeuta | FTP DATASUS |
| Rede especializada | CNES — serviço **126** inteiro + `135/003` e `135/011` | FTP DATASUS |
| População e municípios | IBGE (agregado 6579; API de localidades) | HTTPS |

### Por que dois indicadores de cobertura, e não um

O ICON do observatório de Farmácia é `municípios com Farmácia Popular / municípios com
oferta`. Essa proxy é específica da profissão farmacêutica e não transfere. Para
Fisioterapia a pergunta "onde existe rede pública que absorve a formação?" tem duas
metades que nenhuma fonte única responde:

* **ICAFT — força de trabalho:** municípios com ao menos um vínculo de fisioterapeuta
  no CNES, pelas nove ocupações nomeadas (ver abaixo);
* **ICRE — rede especializada:** municípios com estabelecimento que oferta **ao SUS**
  serviço de fisioterapia (serviço **126** inteiro, ou serviço 135 nas classificações
  **003** *Reabilitação física* e **011** *Atenção fisioterapêutica*).

São publicados separadamente, com escalas próprias. Fundi-los num índice único exigiria
um peso arbitrário entre "tem profissional" e "tem serviço habilitado" — e peso arbitrário
é estimativa disfarçada.

### A família de CBO aqui não é homogênea — e isso é só deste observatório

Nos cinco irmãos o filtro de ocupação é o prefixo da família, e é seguro: 2238 é toda
fonoaudiólogo, 2515 toda psicólogo, 2232 toda cirurgião-dentista. A família **2236
não é**. Medido em `tbAtividadeProfissional` da competência 202610, ela tem dez
ocupações — nove de fisioterapeuta e uma que não é:

```
2236I1  TECNICO EM ORIENTACAO E MOBILIDADE DE CEGOS E DEFICIENTES VISUAIS
```

Filtrar por `startswith("2236")` somaria esse técnico à contagem de fisioterapeutas. O
código tem **letra**, então nem uma guarda de "só dígitos" o pegaria sem ser escrita de
propósito. Por isso o filtro é a lista explícita das nove ocupações.

Lista explícita tem o defeito simétrico: ela falha **fechada**. Uma ocupação de
fisioterapeuta criada depois deste código ficaria de fora em silêncio, e a cobertura
cairia parecendo notícia sobre o SUS quando seria notícia sobre uma constante. Por isso
`conferir_familia_cbo` relê a família na tabela de domínio a cada execução e **derruba a
extração** quando aparece código novo, com o nome dele na tela, antes de qualquer leitura
longa. Nenhuma das duas escolhas acerta sozinha; a conferência é o que transforma erro
silencioso em pergunta.

Casar por **texto** também não serve: capturaria `234425 PROFESSOR DE FISIOTERAPIA`, que
é docência, não assistência.

### O rótulo CINE tem oito vizinhos, e o match é exato

Medido no Censo 2024: o rótulo exato `Fisioterapia` tem 5.870 registros. Uma busca por
substring `fisi` devolveria **30.353** — cinco vezes a medida certa:

| Registros | Rótulo |
|---|---|
| 10.117 | Educação física |
| 9.966 | Educação física formação de professor |
| **5.870** | **Fisioterapia** |
| 3.575 | Física formação de professor |
| 783 | Física |
| 13 | Engenharia física |
| 13 | Física médica |
| 8 | Geofísica |
| 8 | Física aplicada |

`Educação física` sozinha é maior que o curso inteiro, e nenhum desses rótulos é
Fisioterapia. Buscar `fisio` em vez de `fisi` devolveria só `Fisioterapia` **hoje** — o
que não autoriza substring: o vizinho que não existe nesta edição pode existir na
próxima, e um extrator que passou a casar por pedaço porque "dava no mesmo" somaria o
curso novo sem avisar ninguém. O diagnóstico refaz a verificação em qualquer edição:

```bash
python etl/extrair_censo.py --ano 2024 --listar-rotulos fisi
```

### A quarta camada de `TP_DIMENSAO`

Os observatórios irmãos conhecem três naturezas de linha: presencial, polo de EaD e sede
de EaD. O Censo 2024 de Fisioterapia traz uma quarta — uma linha com `TP_DIMENSAO = 4`,
modalidade EaD, **sem UF e sem município**, com 0 vagas e 2 matrículas.

No código dos irmãos uma linha assim desaparece: a atribuição de UF cai num `continue`
por falta de `SG_UF`, sem contador e sem aviso. O total nacional deixa de fechar com a
soma dos estados e nada diz por quê.

São duas matrículas — irrelevante na medida, e completamente relevante no método. Um
conjunto em que o total não fecha com as partes não permite distinguir "a fonte não
localizou" de "o pipeline perdeu". Aqui a camada é contada, entra no total nacional, não
entra em nenhuma UF, aparece em `metadados.sem_localizacao` e é conferida por dois testes
— um que fecha a conta (227.221 por UF + 2 = 227.223 no recorte) e outro que proíbe o
conserto errado, que seria distribuir as linhas por UF da mantenedora ou por rateio:
isso faria o total fechar **inventando dado**.

### Serviço declarado não é serviço público

`rlEstabServClass` traz `CO_AMBULATORIAL_SUS` e `CO_HOSPITALAR_SUS`, e sem olhá-las o
indicador conta clínica privada como rede pública. A cobertura pública é o que vira
índice; o total declarado sai ao lado, nos campos terminados em `_total`, porque a
distância entre os dois diz quanto da rede do município é acessível pelo SUS.

Medido na competência 202610, a diferença entre os dois recortes é desigual nas duas
unidades de contagem:

| | ofertado ao SUS | declarado no cadastro |
|---|---|---|
| Municípios com serviço de fisioterapia | **4.757** | 4.856 |
| Estabelecimentos com serviço de fisioterapia | **15.487** | 29.997 |

O número de municípios quase não se move (−2,0%) e o de estabelecimentos **cai à
metade** (−48,4%). As duas leituras não se contradizem: onde existe clínica privada de
fisioterapia em geral também existe serviço público, então somar a privada acrescenta
poucos municípios novos e muitos estabelecimentos. A distância é maior aqui do que na
Fonoaudiologia, onde o mesmo filtro medido leva os estabelecimentos de 5.568 a 9.354
(+68%); na Fisioterapia o acréscimo é de +94%, porque a clínica privada de fisioterapia
é abundante. Sem o filtro, o indicador mediria o mercado em vez da rede pública.

A contagem de profissionais segue a mesma lógica e tem um resultado próprio: **105.511
fisioterapeutas com vínculo SUS**, presentes em **5.545 dos 5.571 municípios** (99,5%) —
contra 161.574 profissionais no total declarado. O profissional chega praticamente a todo
o país; o *serviço* estruturado, a 85% dele; e a *formação* presencial, a 380 municípios
(6,8%). Os três alcances são medidos separadamente justamente porque não coincidem.

Na mesma tabela, a coluna `ST_ATIVO_SN` vem **vazia em todas as linhas** deste export. O
filtro de serviço inativo que existia no extrator lia coluna sempre em branco e nunca
excluiu nada — agora a ausência é contada e declarada, em vez de disfarçada de filtro.

### Três coisas que a fonte não permite medir, e por quê

Nenhuma delas é substituída por aproximação. Todas foram **medidas como ausentes**, não
deixadas de lado.

**O CER, que seria o indicador mais específico desta profissão.** A habilitação de Centro
Especializado em Reabilitação não é publicada na base do CNES. Os códigos existem em
`tbSubGruposHabilitacao` — 2208 a 2211 e 8223 a 8225, e o **2208 é exatamente a
modalidade FÍSICA**, a que mais interessaria aqui. Mas `tbSubGruposHabilitacao` é o único
membro do ZIP com "habilita" no nome, e nenhuma das 38 tabelas de relação liga habilitação
a estabelecimento. O indicador mais preciso que existiria para a Fisioterapia é
justamente o que a fonte não deixa construir.

**Infraestrutura.** O catálogo `tbInstalFisicaParaAssist` tem 66 instalações, de centro
cirúrgico a medicina nuclear, passando por diálise e radioterapia. **Nenhuma é de
fisioterapia ou reabilitação.** Não há indicador de "salas de fisioterapia" porque a
fonte não distingue a sala.

**E uma armadilha que parece medida.** O membro `rlEstabInstFisiAssist` tem 1.145.631
linhas ligando estabelecimento a instalação por `CO_UNIDADE` — e o "Fisi" dele é de
**física**: *instalação física para assistência*. Quem procurar "fisi" entre os 109
membros do ZIP acha essa tabela, vê o volume e a ligação, e constrói um indicador de
infraestrutura fisioterapêutica perfeitamente plausível e sem sentido nenhum. O nome do
membro não é critério; o catálogo é.

## Rodar localmente

```bash
pip install -r requirements.txt
```

### Gerar o site

```bash
python site/build.py
```

O site sai em `site/dist/`.

### Portões de qualidade (GO)

```bash
python etl/indices.py --autoteste
python site/estatistica.py
python site/catalogo.py
```

Conferem, respectivamente: as fórmulas dos índices contra um estado sintético
calculado à mão; Spearman, valor de p e regressão múltipla contra casos de
resultado conhecido; e a coerência interna do catálogo de indicadores.

### Testes

```bash
python tests/test_catalogo.py
python tests/test_validacao.py
python tests/test_check_fontes.py
```

Rodam como script ou sob `pytest`, se você o tiver instalado.

## Atualizar os dados

```bash
python etl/pipeline.py --check-only     # só verifica se as fontes mudaram
python etl/pipeline.py --ano 2024       # extrai, calcula, valida, publica
python etl/pipeline.py --so-riqueza     # só a guarda de riqueza
python etl/serie.py --anos 2023 2024    # série histórica
```

A extração do CNES leva perto de uma hora, porque o FTP do DATASUS derruba a
maior parte das conexões que usam `REST`. Ela guarda as fatias já filtradas em
`etl/dados/cnes_<competência>/`, então reprocessar a agregação depois é
instantâneo. Use `--pular-cnes` quando estiver mexendo em outra parte.

Se for atualizar também os observatórios de **Psicologia** e **Odontologia**,
que leem as mesmas tabelas-fato do CNES, existe uma ferramenta que produz as
três fatias numa leitura só — cerca de uma hora em vez de três:
[observatorio-ferramentas](https://github.com/esidiao/observatorio-ferramentas).

**Este repositório não depende dela.** O `etl/` aqui é completo e autônomo, e o
pipeline acima roda sozinho, do zero, sem nada instalado ao lado. A ferramenta
apenas preenche antes o cache de `etl/dados/cnes_<competência>/`; encontrando as
fatias prontas, o extrator daqui as aproveita e segue. Quem mantém só este
observatório pode ignorar o parágrafo inteiro.

O pipeline encadeia extração -> índices -> enriquecimento -> **conferência de riqueza** ->
validação, e só grava se tudo passar. A conferência de riqueza compara o número de campos
por UF com o que está em `git show HEAD` e aborta se o novo resultado for mais pobre —
guarda que existe porque, no projeto de Farmácia, republicar por um caminho parcial
derrubou 33 dos 51 campos com todos os testes verdes: nenhum teste checava *presença* de
campo.

## Publicação

O deploy é **manual**. Um push na `main` roda os portões, os testes e o build,
mas não publica nada: publicar é um ato deliberado.

Para colocar no ar, em **Actions → CI → Run workflow**, escolha a ação:

| Ação | O que faz |
|---|---|
| `publicar` | valida e publica no GitHub Pages |
| `so-validar` | roda portões, testes e build; não publica |
| `verificar-fontes` | só checa se INEP ou CNES publicaram edição nova |

A verificação de fontes também roda sozinha toda segunda-feira e abre issue
quando encontra edição nova — ou quando a verificação fica **indeterminada**,
que é diferente de não ter novidade.

## Princípio inegociável

Nenhum indicador é estimado, interpolado ou preenchido por analogia. Sem fonte oficial
para um recorte, o valor é `null` e aparece como **"sem dados"** — nunca zero, nunca média
plausível. Todo número carrega proveniência: fonte, ano e data de extração.

Isso pesa mais aqui do que no observatório de Farmácia: com 24 UFs e 74 cursos avaliados,
as lacunas são proporcionalmente maiores e a tentação de preencher por analogia é
constante.

## Autoria e direitos

**Edson Sidião de Souza Júnior** — sidiao@i9educar.com ·
[Lattes](http://lattes.cnpq.br/9464330669014306)
Farmacêutico, Mestre e Doutor em Medicina Tropical (UFG), avaliador *ad hoc*
INEP/MEC há mais de quinze anos.

© 2026, todos os direitos reservados sobre a obra autoral (Leis 9.610/1998 e
9.609/1998). Os **dados primários** são públicos e pertencem ao INEP, ao
Ministério da Saúde e ao IBGE; os **indicadores calculados** são liberados para
reúso com citação.

Termos completos, forma de citação e registro de anterioridade em
[`DIREITOS.md`](DIREITOS.md). Ver também [`SECURITY.md`](SECURITY.md) e a
página de aviso legal do site.
