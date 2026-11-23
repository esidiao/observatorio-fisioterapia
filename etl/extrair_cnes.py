"""
etl/extrair_cnes.py
Extrai do CNES as duas metades da cobertura assistencial fisioterapêutica,
lendo a base mensal do DATASUS por FTP sem baixar os 700 MB do ZIP.

Uso:
    python etl/extrair_cnes.py                      # competência mais recente
    python etl/extrair_cnes.py --competencia 202609
    python etl/extrair_cnes.py --listar             # competências disponíveis
    python etl/extrair_cnes.py --rebaixar           # ignora o cache e rebaixa

Saída: data/cobertura_cnes.json — por município.

AS DUAS METADES
---------------
  · força de trabalho — municípios com ao menos um vínculo de fisioterapeuta
    em `tbCargaHorariaSus`;
  · rede especializada — municípios com estabelecimento que declara serviço
    de fisioterapia ou reabilitação física em `rlEstabServClass`.

Publicadas separadamente porque fundi-las exigiria arbitrar um peso entre "tem
profissional" e "tem serviço", e peso arbitrário é estimativa disfarçada.

AQUI O CBO NÃO PODE SER POR PREFIXO — E ISSO É PARTICULAR DESTE PROJETO
-----------------------------------------------------------------------
Nos observatórios irmãos o filtro de CBO é o prefixo da família, e é seguro:
2238 é toda fonoaudiólogo, 2515 toda psicólogo, 2232 toda cirurgião-dentista.

A família 2236 NÃO é homogênea. Medido em tbAtividadeProfissional da 202610:
são dez ocupações, nove de fisioterapeuta e uma que não é —

    2236I1  TECNICO EM ORIENTACAO E MOBILIDADE DE CEGOS E DEFICIENTES VISUAIS

Filtrar por `startswith("2236")` somaria esse técnico à contagem de
fisioterapeutas. O código tem LETRA, então nem uma guarda de "só dígitos"
pegaria sem ser escrita de propósito. Por isso o filtro é a LISTA EXPLÍCITA
das nove ocupações.

Lista explícita tem o defeito simétrico: falha FECHADA. Se o CNES registrar
uma ocupação de fisioterapeuta nova, ela ficaria de fora em silêncio e a
cobertura cairia sem motivo aparente. É para isso que existe
`conferir_familia_cbo`: a cada execução ele relê a família na tabela de
domínio e compara com o que está declarado aqui. Código novo derruba a
extração com o nome dele na tela, para que uma pessoa decida se é
fisioterapeuta ou não. Nenhuma das duas escolhas acerta sozinha; a
conferência é o que transforma erro silencioso em pergunta.

Casar por TEXTO também não serve: capturaria `234425 PROFESSOR DE
FISIOTERAPIA`, que é docência, não assistência.

DUAS FASES, COM CACHE ENTRE ELAS
---------------------------------
Baixar e filtrar leva perto de uma hora (236 MB por um FTP que derruba a maior
parte das conexões). Agregar leva segundos. Misturar as duas coisas num passo
só significa pagar a hora de novo a cada ajuste de fórmula, o que na prática
desestimula ajustar a fórmula. As fatias filtradas ficam em
`etl/dados/cnes_<competência>/`, fora do versionamento.

O QUE NÃO DÁ PARA MEDIR AQUI
-----------------------------
A habilitação de Centro Especializado em Reabilitação (CER) NÃO é publicada
nesta base. Os códigos existem em `tbSubGruposHabilitacao` (2208–2211 para as
modalidades do CER, 8223–8225 para CER II/III/IV), mas nenhuma tabela-fato os
relaciona a estabelecimento ou município: `tbIncentivos` traz apenas cinco
códigos, todos de incentivo financeiro, e nenhum deles de reabilitação. Medir
outra coisa e chamar de CER seria inventar o indicador. Ele fica ausente.
"""
import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from rede import ZipRemotoFTP

REPO = Path(__file__).parent.parent
DADOS = REPO / "etl" / "dados"
DATA = REPO / "data"

HOST = "ftp.datasus.gov.br"
DIRETORIO = "/cnes"
PADRAO = "BASE_DE_DADOS_CNES_{competencia}.ZIP"

# Blocos grandes reduzem o número de conexões FTP, e cada conexão é uma aposta:
# o DATASUS derruba boa parte das conexões que usam REST. Blocos pequenos
# multiplicam as apostas; blocos grandes desperdiçam mais a cada queda.
BLOCO = 16 << 20

CBO_FAMILIA = "2236"           # família do fisioterapeuta — NÃO homogênea

# As nove ocupações de fisioterapeuta, nomeadas. Ver o cabeçalho: a família tem
# uma décima que não é fisioterapeuta, então prefixo não serve.
CBO_FISIOTERAPEUTA = frozenset({
    "223605",   # FISIOTERAPEUTA GERAL
    "223625",   # FISIOTERAPEUTA RESPIRATORIA
    "223630",   # FISIOTERAPEUTA NEUROFUNCIONAL
    "223635",   # FISIOTERAPEUTA TRAUMATOORTOPEDICA FUNCIONAL
    "223640",   # FISIOTERAPEUTA OSTEOPATA
    "223645",   # FISIOTERAPEUTA QUIROPRAXISTA
    "223650",   # FISIOTERAPEUTA ACUPUNTURISTA
    "223655",   # FISIOTERAPEUTA ESPORTIVO
    "223660",   # FISIOTERAPEUTA DO TRABALHO
})

# A décima, declarada para que a conferência distinga "código que já
# conhecemos e excluímos de propósito" de "código novo, que ninguém olhou".
# Sem essa distinção a guarda dispararia em toda execução e seria desligada.
CBO_FAMILIA_NAO_FISIOTERAPEUTA = frozenset({
    "2236I1",   # TECNICO EM ORIENTACAO E MOBILIDADE DE CEGOS E DEF. VISUAIS
})

# Serviço 126 inteiro é fisioterapia: as oito classificações são assistência
# fisioterapêutica em alguma área (obstétrica, oncológica, oftalmológica,
# cardiovascular, músculo-esquelética, queimados, neurologia) mais o
# diagnóstico cinético-funcional, ato privativo do fisioterapeuta.
SERVICO_FISIOTERAPIA = "126"

# Do serviço 135 (reabilitação), só as duas classificações fisioterapêuticas.
# As outras onze são de outras profissões — visual, intelectual, auditiva,
# fonoaudiológica, estomizadas — ou de dispositivo (as três oficinas
# ortopédicas). O 135 inteiro inflaria a rede com serviço que fisioterapeuta
# não presta.
SERVICO_REABILITACAO = "135"
CLASSIF_REABILITACAO_FISIO = {"003", "011"}   # reabilitação física; atenção fisioterapêutica

# Medidos e deliberadamente FORA: 155 (traumatologia e ortopedia) é
# especialidade médica; 164 (órteses, próteses e meios auxiliares de
# locomoção) é dispensação de dispositivo. E a varredura inversa na tabela de
# classificações não achou nenhuma outra com "fisioterap" fora do 126 e do 135.
#
# DUAS AUSÊNCIAS MEDIDAS, PARA NÃO SEREM PROCURADAS DE NOVO
# ---------------------------------------------------------
# 1. INFRAESTRUTURA não é indicador possível. O ZIP traz
#    `tbInstalFisicaParaAssist` com 66 instalações catalogadas, e NENHUMA é de
#    fisioterapia ou reabilitação — o catálogo vai de centro cirúrgico a
#    medicina nuclear, passando por diálise e radioterapia. Um indicador de
#    "salas de fisioterapia" não existe porque a fonte não distingue a sala,
#    não porque ninguém o calculou.
#
# 2. `rlEstabInstFisiAssist` NÃO é de fisioterapia. O "Fisi" é de FÍSICA:
#    instalação física para assistência. São 1.145.631 linhas ligando
#    estabelecimento a tipo de instalação por `CO_UNIDADE`, e é justamente o
#    volume e a ligação que tornam a armadilha perigosa — quem procurar "fisi"
#    entre os 109 membros do ZIP acha essa tabela, vê que ela liga
#    estabelecimento a alguma coisa, e constrói um indicador plausível e sem
#    sentido nenhum. O nome do membro não é critério; o catálogo é.

UF_POR_CODIGO = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP",
    "17": "TO", "21": "MA", "22": "PI", "23": "CE", "24": "RN", "25": "PB",
    "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS",
    "51": "MT", "52": "GO", "53": "DF",
}

# Fração de registros cujo CO_UNIDADE não existe em NENHUM estabelecimento do
# cadastro. Diferente de "estabelecimento desabilitado", que é exclusão
# deliberada e pode ser alta sem indicar defeito nenhum.
LIMITE_SEM_CADASTRO = 0.02

csv.field_size_limit(1 << 24)


def _limpo(valor):
    return (valor or "").strip().strip('"')


def competencias_disponiveis():
    z = ZipRemotoFTP(HOST, DIRETORIO, PADRAO.format(competencia="000000"))
    nomes = z.listar_diretorio()
    return sorted(
        m.group(1) for m in
        (re.match(r"BASE_DE_DADOS_CNES_(\d{6})\.ZIP$", n, re.I) for n in nomes)
        if m
    )


def _membro(z, sufixo, competencia):
    alvo = z.localizar(sufixo.lower(), competencia)
    if not alvo:
        raise SystemExit(f"[ERRO] membro {sufixo}{competencia} não encontrado no ZIP")
    return alvo


# --------------------------------------------------------------------------- #
# FASE 1 — baixar e filtrar (cara, cacheada)
# --------------------------------------------------------------------------- #

def _escrever(caminho, cabecalho, linhas):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)


def _filtro_atual():
    """O recorte em vigor, no formato em que fica gravado junto do cache."""
    return {
        "cbo_ocupacoes": sorted(CBO_FISIOTERAPEUTA),
        "servico_fisioterapia": SERVICO_FISIOTERAPIA,
        "servico_reabilitacao": SERVICO_REABILITACAO,
        "classificacoes_reabilitacao": sorted(CLASSIF_REABILITACAO_FISIO),
    }


def _gravar_filtro(cache):
    (cache / "_filtro.json").write_text(
        json.dumps(_filtro_atual(), ensure_ascii=False, indent=1),
        encoding="utf-8")


def conferir_filtro_do_cache(cache):
    """
    O cache foi filtrado com o recorte que está em vigor agora?

    Este é o modo de errar que o cache introduz. Mudar `CBO_FISIOTERAPEUTA` ou
    as classificações do 135 e rodar de novo NÃO refaz as fatias — elas existem,
    então são aproveitadas, e a medição publicada continua sendo a do recorte
    antigo. O número sai plausível, o pipeline passa, os testes de âncora
    passam (porque as âncoras também não mudaram), e nada no sítio diz que o
    critério declarado não é o critério aplicado.

    A conferência é local e instantânea: compara o recorte em vigor com o que
    foi gravado quando as fatias foram escritas. Não custa conexão nenhuma, que
    é o que permite mantê-la no caminho do cache-hit.

    Cache sem `_filtro.json` é anterior a esta conferência; avisa e segue, em
    vez de obrigar a rebaixar 700 MB por falta de um arquivo de metadado.
    """
    registro = cache / "_filtro.json"
    if not registro.exists():
        print("[CNES] AVISO: cache sem registro de filtro (anterior a esta "
              "conferência). Não é possível afirmar que ele foi filtrado com o "
              "recorte atual. Use --rebaixar se houve mudança de critério.")
        return
    try:
        gravado = json.loads(registro.read_text(encoding="utf-8"))
    except ValueError:
        print(f"[CNES] AVISO: {registro} ilegível; filtro não conferido.")
        return
    atual = _filtro_atual()
    if gravado == atual:
        return
    diferencas = [f"    {k}: cache={gravado.get(k)!r}  código={v!r}"
                  for k, v in atual.items() if gravado.get(k) != v]
    raise SystemExit(
        "[ERRO] as fatias em cache foram filtradas com um recorte diferente do "
        "que está no código:\n" + "\n".join(diferencas) +
        "\n\nRode com --rebaixar. Aproveitar este cache publicaria uma medição "
        "feita com o critério antigo sob a proveniência do critério novo.")


def conferir_familia_cbo(z, competencia):
    """
    Relê a família 2236 na tabela de domínio e compara com o declarado aqui.

    Existe porque o filtro é uma lista explícita, e lista explícita falha
    fechada: uma ocupação de fisioterapeuta criada depois deste código ficaria
    de fora sem que nada acusasse, e a cobertura cairia parecendo notícia sobre
    o SUS quando seria notícia sobre esta constante.

    Três desfechos possíveis, e os três importam:

      · a família confere         — segue em silêncio;
      · apareceu código novo      — derruba a extração, com o código e o nome
                                    na tela, para uma pessoa classificar;
      · a tabela não pôde ser lida — AVISA e segue. O domínio é um luxo de
                                    rótulo; a medição não depende dele, e
                                    abortar uma leitura de uma hora porque o
                                    FTP caiu num arquivo de 200 KB trocaria um
                                    risco pequeno por um custo grande.

    Note que ela não pode dizer se o código novo é de fisioterapeuta: isso é
    leitura de nome, e nome é exatamente o que este projeto não usa como
    critério. Ela sabe dizer que algo mudou — que é o que uma guarda deve fazer.
    """
    declarados = CBO_FISIOTERAPEUTA | CBO_FAMILIA_NAO_FISIOTERAPEUTA

    # Orçamento curto e próprio: a tabela é minúscula e insistir doze vezes
    # nela custaria mais do que ela vale.
    z_curto = ZipRemotoFTP(z.host, z.diretorio, z.nome, timeout=60, tentativas=3)
    z_curto._indice = z.indice()
    z_curto._tamanho = z.tamanho()

    alvo = z_curto.localizar("tbatividadeprofissional", competencia)
    if not alvo:
        print("[CNES] AVISO: tbAtividadeProfissional não está no ZIP; a família "
              f"{CBO_FAMILIA} não pôde ser reconferida nesta execução.")
        return None
    try:
        encontrados = {}
        with z_curto.membro_arquivo(alvo) as f:
            for linha in csv.DictReader(f, delimiter=";"):
                cbo = _limpo(linha.get("CO_CBO"))
                if cbo.startswith(CBO_FAMILIA):
                    encontrados[cbo] = _limpo(
                        linha.get("DS_ATIVIDADE_PROFISSIONAL"))
    except Exception as e:                                     # noqa: BLE001
        print(f"[CNES] AVISO: não foi possível reler a família {CBO_FAMILIA} "
              f"({type(e).__name__}); segue sem a conferência.")
        return None

    novos = sorted(set(encontrados) - declarados)
    sumidos = sorted(declarados - set(encontrados))

    if novos:
        linhas = "\n".join(f"    {c}  {encontrados[c]}" for c in novos)
        raise SystemExit(
            f"[ERRO] a família {CBO_FAMILIA} ganhou ocupação que este código "
            f"não conhece:\n{linhas}\n\n"
            "Decida se é fisioterapeuta e acrescente o código a "
            "CBO_FISIOTERAPEUTA, ou, se não for, a "
            "CBO_FAMILIA_NAO_FISIOTERAPEUTA. Seguir sem decidir publicaria uma "
            "cobertura que ignora a ocupação nova sem dizer que a ignora.")

    if sumidos:
        # Sumir não é motivo para abortar: o filtro continua correto, só mais
        # largo do que precisa. Mas tem de aparecer, porque pode ser renomeação
        # de código — e aí a ocupação nova viria no ramo de cima.
        print(f"[CNES] AVISO: ocupações declaradas que não estão mais na "
              f"família {CBO_FAMILIA}: {sumidos}")

    print(f"[CNES] família {CBO_FAMILIA} conferida: {len(encontrados)} "
          f"ocupações, {len(CBO_FISIOTERAPEUTA)} de fisioterapeuta")
    return encontrados


def baixar_fatias(competencia, cache, rebaixar=False):
    """Grava três fatias filtradas em `cache`. Só baixa o que faltar."""
    alvos = {
        "estabelecimentos": cache / "estabelecimentos.csv",
        "vinculos": cache / "vinculos_fisio.csv",
        "servicos": cache / "servicos_fisio.csv",
    }
    if not rebaixar and all(p.exists() for p in alvos.values()):
        conferir_filtro_do_cache(cache)
        print(f"[CNES] usando fatias já filtradas em {cache}")
        return alvos

    nome = PADRAO.format(competencia=competencia)
    z = ZipRemotoFTP(HOST, DIRETORIO, nome)
    print(f"[CNES] {nome} — {z.tamanho() / 1048576:.0f} MB no servidor; "
          "lendo só os membros necessários")

    # Antes de ler qualquer tabela-fato: a família de CBO ainda é a que este
    # código conhece? Se ganhou ocupação nova, para aqui — não depois de uma
    # hora de leitura.
    conferir_familia_cbo(z, competencia)

    if rebaixar or not alvos["estabelecimentos"].exists():
        alvo = _membro(z, "tbEstabelecimento", competencia)
        print(f"[CNES] lendo {alvo} ...")
        linhas, ativos, desabilitados = [], 0, 0
        with z.membro_arquivo(alvo, bloco=BLOCO) as f:
            for linha in csv.DictReader(f, delimiter=";"):
                unidade = _limpo(linha.get("CO_UNIDADE"))
                if not unidade:
                    continue
                # Guardamos TODOS, com uma coluna dizendo se está ativo. O
                # desabilitado precisa continuar conhecido: é ele que permite
                # distinguir "excluído de propósito" de "não encontrado", e
                # essa distinção é o que dá sentido à guarda de junção.
                ativo = "0" if _limpo(linha.get("CO_MOTIVO_DESAB")) else "1"
                if ativo == "1":
                    ativos += 1
                else:
                    desabilitados += 1
                linhas.append([unidade,
                               _limpo(linha.get("CO_MUNICIPIO_GESTOR")),
                               _limpo(linha.get("CO_ESTADO_GESTOR")),
                               ativo])
        _escrever(alvos["estabelecimentos"],
                  ["CO_UNIDADE", "CO_MUNICIPIO_GESTOR", "CO_ESTADO_GESTOR", "ATIVO"],
                  linhas)
        print(f"[CNES] {ativos} estabelecimentos ativos, "
              f"{desabilitados} desabilitados -> {alvos['estabelecimentos'].name}")

    if rebaixar or not alvos["vinculos"].exists():
        alvo = _membro(z, "tbCargaHorariaSus", competencia)
        print(f"[CNES] lendo {alvo} ... (834 MB descomprimidos; leitura em fluxo)")
        linhas, total = [], 0
        with z.membro_arquivo(alvo, bloco=BLOCO) as f:
            for linha in csv.DictReader(f, delimiter=";"):
                total += 1
                cbo = _limpo(linha.get("CO_CBO"))
                if cbo not in CBO_FISIOTERAPEUTA:
                    continue
                linhas.append([_limpo(linha.get("CO_UNIDADE")),
                               _limpo(linha.get("CO_PROFISSIONAL_SUS")),
                               cbo,
                               _limpo(linha.get("TP_SUS_NAO_SUS"))])
        _escrever(alvos["vinculos"],
                  ["CO_UNIDADE", "CO_PROFISSIONAL_SUS", "CO_CBO", "TP_SUS_NAO_SUS"],
                  linhas)
        print(f"[CNES] {total} vínculos lidos; {len(linhas)} das "
              f"{len(CBO_FISIOTERAPEUTA)} ocupações de fisioterapeuta "
              f"-> {alvos['vinculos'].name}")
        _gravar_filtro(cache)

    if rebaixar or not alvos["servicos"].exists():
        alvo = _membro(z, "rlEstabServClass", competencia)
        print(f"[CNES] lendo {alvo} ...")
        linhas, total = [], 0
        with z.membro_arquivo(alvo, bloco=BLOCO) as f:
            for linha in csv.DictReader(f, delimiter=";"):
                total += 1
                servico = _limpo(linha.get("CO_SERVICO"))
                classificacao = _limpo(linha.get("CO_CLASSIFICACAO"))
                if servico != SERVICO_FISIOTERAPIA and not (
                        servico == SERVICO_REABILITACAO
                        and classificacao in CLASSIF_REABILITACAO_FISIO):
                    continue
                linhas.append([_limpo(linha.get("CO_UNIDADE")), servico,
                               classificacao, _limpo(linha.get("ST_ATIVO_SN")),
                               _limpo(linha.get("CO_AMBULATORIAL_SUS")),
                               _limpo(linha.get("CO_HOSPITALAR_SUS"))])
        _escrever(alvos["servicos"],
                  ["CO_UNIDADE", "CO_SERVICO", "CO_CLASSIFICACAO", "ST_ATIVO_SN",
                   "CO_AMBULATORIAL_SUS", "CO_HOSPITALAR_SUS"],
                  linhas)
        print(f"[CNES] {total} registros de serviço; {len(linhas)} "
              f"de fisioterapia -> {alvos['servicos'].name}")

    return alvos


# --------------------------------------------------------------------------- #
# FASE 2 — agregar (barata, refaz à vontade)
# --------------------------------------------------------------------------- #

def carregar_estabelecimentos(caminho):
    """Devolve (ativos, conhecidos): dict CO_UNIDADE->(mun, uf) e set de todos."""
    ativos, conhecidos = {}, set()
    with open(caminho, encoding="utf-8") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            unidade = linha["CO_UNIDADE"]
            conhecidos.add(unidade)
            if linha["ATIVO"] == "1" and linha["CO_MUNICIPIO_GESTOR"]:
                ativos[unidade] = (linha["CO_MUNICIPIO_GESTOR"],
                                   UF_POR_CODIGO.get(linha["CO_ESTADO_GESTOR"]))
    return ativos, conhecidos


def _classificar(unidade, ativos, conhecidos, contadores):
    """
    Resolve o município de um CO_UNIDADE e classifica o que não resolve.

    Três desfechos, e a diferença entre eles é o ponto:
      · resolveu                   -> devolve o município
      · existe, mas desabilitado   -> exclusão DELIBERADA, esperada, não é erro
      · não existe no cadastro     -> falha de junção; é isso que a guarda vigia
    """
    local = ativos.get(unidade)
    if local:
        return local[0]
    if unidade in conhecidos:
        contadores["desabilitado"] += 1
    else:
        contadores["sem_cadastro"] += 1
    return None


def forca_de_trabalho(caminho, ativos, conhecidos):
    """
    Conta PROFISSIONAIS DISTINTOS por município, não vínculos: o mesmo
    fisioterapeuta pode ter três vínculos no mesmo município, e contá-lo três
    vezes transformaria precariedade de vínculo em abundância de força de
    trabalho.
    """
    sus, todos = defaultdict(set), defaultdict(set)
    contadores = defaultdict(int)
    total = 0
    with open(caminho, encoding="utf-8") as f:
        for i, linha in enumerate(csv.DictReader(f, delimiter=";")):
            total += 1
            municipio = _classificar(linha["CO_UNIDADE"], ativos, conhecidos,
                                     contadores)
            if not municipio:
                continue
            chave = linha["CO_PROFISSIONAL_SUS"] or f"{linha['CO_UNIDADE']}:{i}"
            todos[municipio].add(chave)
            if linha["TP_SUS_NAO_SUS"].upper() == "S":
                sus[municipio].add(chave)
    return sus, todos, {
        "vinculos_fisioterapia": total,
        "vinculos_em_estabelecimento_desabilitado": contadores["desabilitado"],
        "vinculos_sem_cadastro": contadores["sem_cadastro"],
    }


def rede_especializada(caminho, ativos, conhecidos):
    """
    Estabelecimentos com serviço de fisioterapia, por município.

    SERVIÇO DECLARADO NÃO É SERVIÇO PÚBLICO. `rlEstabServClass` traz
    `CO_AMBULATORIAL_SUS` e `CO_HOSPITALAR_SUS` (1 = sim, 2 = não), e sem
    olhá-las a clínica privada que declara o serviço entra como rede pública.
    Como a pergunta deste observatório é sobre a rede que absorve quem se
    forma, o indicador conta apenas quem oferta AO SUS; o total declarado sai
    ao lado, porque a distância entre os dois também é informação.

    O ST_ATIVO_SN NUNCA FILTROU NADA. A coluna existe no layout e vem VAZIA em
    100% das linhas deste export — medido aqui e no observatório de Odontologia,
    onde o defeito foi descoberto. O filtro que havia aqui era decorativo: lia
    uma coluna sempre em branco e nunca excluía registro algum. Em vez de
    mantê-lo fingindo trabalhar, agora se CONTA quantas linhas trazem situação
    preenchida e isso vai para o diagnóstico. Se uma competência futura passar
    a preencher a coluna, o número aparece e a decisão volta a ser possível.
    """
    por_municipio = defaultdict(set)
    por_municipio_sus = defaultdict(set)
    detalhe = defaultdict(lambda: defaultdict(set))
    contadores = defaultdict(int)
    total = com_situacao = 0
    with open(caminho, encoding="utf-8") as f:
        for linha in csv.DictReader(f, delimiter=";"):
            total += 1
            if linha.get("ST_ATIVO_SN"):
                com_situacao += 1
            municipio = _classificar(linha["CO_UNIDADE"], ativos, conhecidos,
                                     contadores)
            if not municipio:
                continue
            rotulo = f"{linha['CO_SERVICO']}/{linha['CO_CLASSIFICACAO']}"
            por_municipio[municipio].add(linha["CO_UNIDADE"])
            detalhe[municipio][rotulo].add(linha["CO_UNIDADE"])
            if (linha.get("CO_AMBULATORIAL_SUS") == "1"
                    or linha.get("CO_HOSPITALAR_SUS") == "1"):
                por_municipio_sus[municipio].add(linha["CO_UNIDADE"])
    return por_municipio_sus, por_municipio, detalhe, {
        "servicos_fisioterapicos": total,
        "servicos_com_situacao_preenchida": com_situacao,
        "st_ativo_sn_vazio_no_export": com_situacao == 0,
        "servicos_em_estabelecimento_desabilitado": contadores["desabilitado"],
        "servicos_sem_cadastro": contadores["sem_cadastro"],
    }


def conferir_juncao(casos, limite=LIMITE_SEM_CADASTRO):
    """
    Aborta se registros demais apontarem para CO_UNIDADE que não existe.

    Vigia SÓ o desconhecido. A primeira versão desta guarda somava o
    desabilitado junto e reprovou uma execução correta com 10,6% — dos quais
    quase tudo era estabelecimento fechado que o indicador exclui de propósito.
    Uma guarda que dispara no comportamento certo é pior que nenhuma: ensina a
    ignorá-la.

    A junção é por CO_UNIDADE, e o formato do campo não é uniforme na base (há
    registros de 30 caracteres ao lado dos de 13). Se o layout mudar numa
    competência futura, a junção degrada em silêncio: o pipeline roda, os testes
    passam, e a cobertura despenca como se a rede tivesse encolhido. Um número
    que cai por defeito de junção é pior que um erro, porque parece notícia.
    """
    problemas = []
    for rotulo, total, desconhecidos, desabilitados in casos:
        if total <= 0:
            problemas.append(f"{rotulo}: nenhum registro lido")
            continue
        fracao = desconhecidos / total
        marca = "OK" if fracao <= limite else "FALHOU"
        print(f"[JUNCAO] {marca}  {rotulo}: {desconhecidos}/{total} "
              f"({fracao:.2%}) sem cadastro; "
              f"{desabilitados} ({desabilitados / total:.1%}) em "
              "estabelecimento desabilitado (exclusão esperada)")
        if fracao > limite:
            problemas.append(
                f"{rotulo}: {fracao:.2%} sem cadastro (limite {limite:.0%})")
    if problemas:
        raise SystemExit("[ERRO] junção CO_UNIDADE degradada:\n  - "
                         + "\n  - ".join(problemas))


def montar(competencia, sus, todos, rede, rede_total, detalhe, diagnostico):
    municipios = {}
    for codigo in set(sus) | set(todos) | set(rede_total):
        municipios[codigo] = {
            "fisioterapeutas_sus": len(sus.get(codigo, ())) or None,
            "fisioterapeutas_total": len(todos.get(codigo, ())) or None,
            # O indicador conta quem oferta ao SUS; o total declarado (público
            # mais privado) fica ao lado, e a diferença diz quanto da rede
            # especializada do município é acessível pelo SUS.
            "estabelecimentos_servico_fisio": len(rede.get(codigo, ())) or None,
            "estabelecimentos_servico_fisio_total": len(
                rede_total.get(codigo, ())) or None,
            "servicos": sorted(detalhe.get(codigo, {})) or None,
        }
    arquivo = PADRAO.format(competencia=competencia)
    return {
        "metadados": {
            "fonte": "Cadastro Nacional de Estabelecimentos de Saúde (CNES/DATASUS)",
            "arquivo": arquivo,
            "url": f"ftp://{HOST}{DIRETORIO}/{arquivo}",
            "competencia": competencia,          # do ARQUIVO, não do calendário
            "cbo_familia": CBO_FAMILIA,
            "cbo_criterio": (
                "Lista explícita das nove ocupações de fisioterapeuta, não o "
                "prefixo da família: a 2236 inclui 2236I1 (técnico em "
                "orientação e mobilidade de cegos e deficientes visuais), que "
                "não é fisioterapeuta. A família é reconferida contra a tabela "
                "de domínio a cada execução."
            ),
            "cbo_ocupacoes": sorted(CBO_FISIOTERAPEUTA),
            "cbo_excluidos_da_familia": sorted(CBO_FAMILIA_NAO_FISIOTERAPEUTA),
            "servicos_considerados": {
                "126": "Serviço de Fisioterapia (todas as classificações)",
                "135/003": "Reabilitação física",
                "135/011": "Atenção fisioterapêutica",
            },
            "servico_criterio_sus": (
                "A rede especializada conta estabelecimentos que ofertam o "
                "serviço AO SUS (CO_AMBULATORIAL_SUS ou CO_HOSPITALAR_SUS = 1). "
                "O total declarado, que inclui a clínica privada, sai no campo "
                "*_total: serviço declarado no cadastro não é serviço público."
            ),
            "st_ativo_sn_nao_filtra": (
                "A coluna ST_ATIVO_SN de rlEstabServClass vem vazia em todas as "
                "linhas deste export, então não há como excluir serviço "
                "marcado como inativo. O filtro que existia aqui lia coluna "
                "sempre em branco e nunca excluiu nada; agora a ausência é "
                "contada e declarada em vez de passar por filtro que funciona."
            ),
            "cer_indisponivel": (
                "A habilitação de Centro Especializado em Reabilitação não é "
                "publicada nesta base: os códigos existem em "
                "tbSubGruposHabilitacao (2208-2211, 8223-8225) mas nenhuma "
                "tabela-fato os liga a estabelecimento ou município. O "
                "indicador de CER não existe e não foi substituído por proxy."
            ),
            "extraido_em": date.today().isoformat(),
            "diagnostico": diagnostico,
        },
        "municipios": municipios,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--competencia", help="AAAAMM; default: a mais recente publicada")
    p.add_argument("--listar", action="store_true",
                   help="lista as competências disponíveis e sai")
    p.add_argument("--rebaixar", action="store_true",
                   help="ignora o cache de fatias e baixa tudo de novo")
    p.add_argument("--saida", default=str(DATA / "cobertura_cnes.json"))
    args = p.parse_args()

    if args.listar:
        comps = competencias_disponiveis()
        print(f"{len(comps)} competências: {comps[0]} .. {comps[-1]}")
        print("últimas 12:", ", ".join(comps[-12:]))
        return

    competencia = args.competencia
    if not competencia:
        comps = competencias_disponiveis()
        if not comps:
            raise SystemExit("[ERRO] nenhuma competência encontrada no FTP")
        competencia = comps[-1]
        print(f"[CNES] competência mais recente: {competencia}")

    cache = DADOS / f"cnes_{competencia}"
    fatias = baixar_fatias(competencia, cache, args.rebaixar)

    ativos, conhecidos = carregar_estabelecimentos(fatias["estabelecimentos"])
    print(f"[CNES] {len(ativos)} estabelecimentos ativos de "
          f"{len(conhecidos)} cadastrados")

    sus, todos, diag_ch = forca_de_trabalho(fatias["vinculos"], ativos, conhecidos)
    rede, rede_total, detalhe, diag_sc = rede_especializada(
        fatias["servicos"], ativos, conhecidos)

    conferir_juncao([
        ("vínculos de fisioterapeuta",
         diag_ch["vinculos_fisioterapia"],
         diag_ch["vinculos_sem_cadastro"],
         diag_ch["vinculos_em_estabelecimento_desabilitado"]),
        ("serviços de fisioterapia",
         diag_sc["servicos_fisioterapicos"],
         diag_sc["servicos_sem_cadastro"],
         diag_sc["servicos_em_estabelecimento_desabilitado"]),
    ])

    saida = montar(competencia, sus, todos, rede, rede_total, detalhe,
                   {**diag_ch, **diag_sc})
    Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(args.saida).write_text(
        json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")

    n_forca = sum(1 for m in saida["municipios"].values() if m["fisioterapeutas_sus"])
    n_rede = sum(1 for m in saida["municipios"].values()
                 if m["estabelecimentos_servico_fisio"])
    n_rede_total = sum(1 for m in saida["municipios"].values()
                       if m["estabelecimentos_servico_fisio_total"])
    print(f"\n[CNES] municípios com fisioterapeuta no SUS: {n_forca}")
    print(f"[CNES] municípios com serviço de fisioterapia ofertado ao SUS: "
          f"{n_rede} (declarado por qualquer natureza: {n_rede_total})")
    print(f"[CNES] -> {args.saida}")


if __name__ == "__main__":
    main()
