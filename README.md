# Observatório Nacional da Formação em Fisioterapia

Site estático data-driven com indicadores de acesso territorial, qualidade e cobertura
assistencial dos cursos de Fisioterapia no Brasil.

Projeto irmão — e independente — do
[Observatório Nacional da Formação Farmacêutica](https://github.com/esidiao/observatorio-formacao-farmaceutica).
Compartilha o método e o design system; não compartilha código, dados nem dependências.

## O que este observatório mede

| | Fisioterapia (Censo 2025 · CPC 2023 · CNES 202610) |
|---|---|
| Cursos no Censo | 1.076 — 955 em atividade, 121 encerrados ou em extinção |
| UFs com oferta **presencial** | **27** de 27 |
| Municípios com oferta presencial | 396 |
| Vagas presenciais | 177.391 |
| Vagas semipresenciais | 95.464 *(categoria nova)* |
| Vagas **a distância em atividade** | **0** — encerradas pelo Decreto 12.456/2025 |
| Vagas em cursos encerrados ou em extinção | 302.594, publicadas **ao lado** da capacidade |
| **% da capacidade ativa não presencial** | **35,0%** |
| Polos da rede ativa | 14.158 registros em 3.006 municípios |
| Polos da rede em extinção | 28.950 registros em 3.429 municípios |
| Matrículas / concluintes / ingressos | 254.789 / 25.313 / 116.412 |
| Matrículas em curso em extinção | 103.118 — e 62.330 pessoas **ingressaram** neste ano |
| IES distintas | 780 — a soma por UF dá 838, e conta oito vezes quem atua em oito estados |
| Cursos avaliados no CPC 2023 | 711, em **todas** as 27 UFs |

### O Censo 2025 mudou de forma, não só de número

Duas rupturas caem na mesma edição, e confundi-las produz leituras falsas.

**O INEP normalizou os microdados.** O cadastro único de curso virou sete tabelas
(`curso`, `aluno`, `ies`, `docente`, `local_oferta`, `biblioteca`, `laboratorio`) e a
coluna `TP_DIMENSAO` **deixou de existir**: as camadas presencial / polo / sede viraram
bandeiras na tabela de local de oferta. Por isso a contagem de registros cai de 5.870
(Censo 2024) para 1.076 **sem que nada tenha encolhido** — antes era uma linha por curso
*e por camada*, agora é uma linha por curso. Quem comparar os dois números como série
anunciará um colapso que não houve.

**O Decreto 12.456/2025 encerrou a graduação em saúde inteiramente a distância.** Em
Fisioterapia não sobrou **nenhum** curso EaD em atividade: os 117 que existem estão, um a
um, marcados "em extinção" na nova coluna `TP_SITUACAO`. E surgiu o formato
**semipresencial**, que não existia. Somar as vagas de formato 2 sem olhar a situação diz
que a EaD cresceu no ano em que ela foi proibida — foi exatamente o erro que apareceu na
série do observatório de Farmácia e que está consertado lá.

A regra adotada: **vaga de curso em extinção não entra na capacidade** (é oferta que a
regulação já encerrou) e **não desaparece** (sai em campo próprio). **Pessoas não se
filtram por situação** — quem está matriculado agora existe e tem direito a concluir no
formato em que ingressou.

### A escala muda o que as páginas precisam dizer

Este é o maior curso de saúde da família de observatórios: 711 cursos avaliados
contra 74 da Fonoaudiologia e 452 da Odontologia. Cinco consequências não são
escolha editorial, são imposição do dado.

**Não existe seção de "UF sem oferta".** A Fonoaudiologia precisa dela — Amapá,
Mato Grosso do Sul e Roraima não têm curso nenhum, e omiti-los faria o país
parecer coberto. Aqui as 27 UFs têm curso presencial e curso avaliado. O que
separa os estados não é *ter*, é escala, concentração e qualidade.

**A ruptura da EaD é o fato central, não uma ressalva.** No Censo 2024, 62,3% da
capacidade era a distância. Em 2025 a capacidade ativa a distância é zero e o
semipresencial responde por 35,0% — e há 103.118 pessoas matriculadas na oferta
encerrada. A manchete do sítio é essa, porque publicar só a capacidade ativa esconderia
um terço de milhão de vagas em desmonte, e publicar os dois somados afirmaria uma oferta
que a lei acabou.

**Presença não é cobertura, e a distância entre as duas é o achado.** Há curso
presencial em 396 municípios e polo da rede ativa em 3.006 — quase oito vezes mais. Os dois
números vão juntos de propósito: publicar só o presencial subestimaria o alcance, e
publicar só o total esconderia que quase todo esse alcance não é presencial.

**Polo que a fonte não localiza é contado e declarado.** Vinte e nove polos
ativos e setenta e cinco em extinção vêm sem `SG_UF_LO`. Antes caíam num
`continue` sem contador, e o total nacional — que é a soma das UFs — ficava
alguns polos abaixo das linhas da fonte, sem nada explicando a diferença. Agora
saem em `metadados.sem_localizacao.polos_sem_uf`. Não são atribuídos a UF
nenhuma: um polo é por definição um endereço, e se a fonte não diz onde é, não
há o que inferir — ao contrário da oferta a distância, que não tem endereço por
natureza.

**Polo não é uma população só, são três.** A soma ingênua por endereço dá 29.921 polos
em 3.438 municípios, misturando a rede EaD em extinção (28.950), a rede semipresencial
que nasceu no lugar dela (14.158) e **471 endereços de curso presencial** que a fonte
também marca como polo. Contar os três juntos como alcance de oferta a distância infla o
país; o alcance ativo real é 3.006 municípios.

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
| Oferta, vagas, matrículas, polos | Censo da Educação Superior 2025 (INEP) | HTTPS, ZIP lido por `Range` |
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

Medido no Censo 2025: o rótulo exato `Fisioterapia` tem 1.076 cursos. Uma busca por
substring `fisi` devolveria **3.116** — quase três vezes a medida certa:

| Cursos | Rótulo |
|---|---|
| **1.076** | **Fisioterapia** |
| 917 | Educação física |
| 691 | Educação física formação de professor |
| 321 | Física formação de professor |
| 70 | Física |
| 13 | Engenharia física |
| 12 | Física médica |
| 8 | Geofísica |
| 8 | Física aplicada |

Nenhum desses rótulos é Fisioterapia. Buscar `fisio` em vez de `fisi` devolveria só
`Fisioterapia` **hoje** — o que não autoriza substring: o vizinho que não existe nesta
edição pode existir na próxima, e um extrator que passou a casar por pedaço porque "dava
no mesmo" somaria o curso novo sem avisar ninguém. O diagnóstico refaz a verificação em
qualquer edição:

```bash
python etl/extrair_censo.py --ano 2025 --listar-rotulos fisi
```

Os nove rótulos são os mesmos de 2024, e as contagens caem em bloco pelo mesmo motivo da
linha anterior: uma linha por curso em vez de uma por curso × camada.

### A camada sem endereço, antes e depois de `TP_DIMENSAO`

Até 2024 a oferta a distância ocupava três naturezas de linha — presencial, polo e sede
—, e o Censo 2024 de Fisioterapia trazia uma quarta: `TP_DIMENSAO = 4`, modalidade EaD,
**sem UF e sem município**. Essa quarta camada era a fonte dizendo *não sei onde é*, e a
sede era a fonte dizendo *não tem onde ser* — a oferta a distância não tem endereço por
natureza. Duas ausências diferentes, com tratamentos diferentes: a sede era atribuída à
UF da mantenedora, a camada 4 era contada e deixada fora de toda UF.

Sem `TP_DIMENSAO`, as duas viraram a mesma ausência, e o que as separa passou a ser o
**formato**: curso presencial tem endereço por definição; a distância e semipresencial,
não. Medido em 2025, as 29 linhas sem local de oferta próprio são 19 a distância e 10
semipresenciais — **nenhuma presencial**. São 199.724 vagas, 35% da capacidade do país:
descartá-las publicaria um Brasil com dois terços do que tem.

Por isso a atribuição pela UF-sede continua, agora com a guarda explícita do formato, e o
contador saiu em `metadados.sem_localizacao.atribuidas_pela_sede_da_ies`. O teste que
guardava isso **mudou de alvo, não de rigor**: ele proibia "distribuir por UF da
mantenedora" porque em 2024 isso significaria inventar a localização da camada 4; agora
exige que só a oferta sem endereço seja atribuída, e **derruba a validação** se alguma
linha presencial entrar nessa conta. Um conjunto em que o total não fecha com as partes
não permite distinguir "a fonte não localizou" de "o pipeline perdeu".

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
o país; o *serviço* estruturado, a 85% dele; e a *formação* presencial, a 396 municípios
(7,1%). Os três alcances são medidos separadamente justamente porque não coincidem.

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
python tests/test_acessibilidade.py
python tests/test_sem_vazamento.py
python tests/test_conteudo_publicado.py
python tests/test_links.py
```

Rodam como script ou sob `pytest`, se você o tiver instalado. São 66 testes.

Três deles guardam a mudança de edição em vez de um número:
`test_o_esquema_declarado_bate_com_a_edicao` derruba a validação se o ano do Censo e o
esquema lido discordarem; `test_composicao_da_capacidade_ativa` só aceita vaga EaD zerada
**acompanhada** de capacidade em extinção, que é o rastro que a lei deixa e que um erro de
leitura não deixaria; e `test_so_a_oferta_sem_endereco_e_atribuida_pela_sede` impede que
oferta presencial entre na atribuição pela UF-sede.

## Atualizar os dados

```bash
python etl/pipeline.py --check-only          # só verifica se as fontes mudaram
python etl/pipeline.py --ano 2025            # extrai, calcula, valida, publica
python etl/pipeline.py --so-riqueza          # só a guarda de riqueza
python etl/serie.py --anos 2021 2025         # série histórica
```

A extração de 2025 lê 2,4 GB em fluxo — a tabela de local de oferta tem 1,6 GB e a de
aluno 796 MB. Ela é **retomável fatia por fatia**: cada recorte é gravado em `.parcial` e
renomeado no fim, então *existir* significa *estar completo*, e uma segunda execução pula
o que já está em `etl/dados/`. Use `--rebaixar` para forçar a releitura.

O nome do arquivo no INEP mudou nesta edição — `microdados_censo_educacao_superior_2025.zip`,
sem o `da` —, e o verificador de fontes sonda **os dois** padrões. Sondar só o antigo
responderia "não há edição nova" no dia em que ela saiu.

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

A edição de 2025 cobra esse princípio de um jeito novo: há três ausências que **não são
zero**. `vagas_ead` em 2025 é zero *medido* — a categoria existe e está vazia. Já
`vagas_semipresencial` e `vagas_em_extincao` antes de 2025 são `null`, porque a categoria
não existia: escrever zero ali afirmaria "nenhum curso em extinção em 2021", quando a
fonte simplesmente não distinguia situação. Na série, a linha da EaD **termina em 2024** e
não desce até zero, e a soma nacional preserva o nulo em vez de somá-lo como zero.

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
