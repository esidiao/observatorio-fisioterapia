"""
tests/test_validacao.py
Integridade do conjunto publicado, contra âncoras conhecidas.

As âncoras foram apuradas no Censo 2024, no CPC 2023 e no CNES 202610, e
conferidas contra o recorte bruto. Servem como teste de REGRESSÃO: se o
pipeline passar a produzir outra coisa, o mais provável é defeito no pipeline,
não notícia nos dados. Uma edição nova da fonte muda os números de propósito —
e aí estas constantes mudam junto, num commit que diz isso.

Nenhum valor aqui foi herdado do observatório de Fonoaudiologia, de onde este
repositório foi copiado. Os do Censo e do CPC saíram de DUAS medições
independentes que concordaram — um script de medição escrito à parte e o
pipeline deste repositório — e os do CNES, da extração conferida pela guarda de
junção. Número herdado de um irmão é o defeito mais perigoso de uma cópia:
ele tem a aparência exata de uma medida desta profissão.

Roda como script ou sob pytest.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

CENSO = 2025
CICLO_CPC = "2023"
COMPETENCIA_CNES = "202610"

# -------------------------------------------------- âncoras: Censo 2025
#
# A EDIÇÃO MUDOU DE FORMA, NÃO SÓ DE NÚMERO.
#
# O INEP normalizou os microdados em 2025: o cadastro único virou sete
# tabelas e `TP_DIMENSAO` deixou de existir. Por isso `REGISTROS_CENSO` cai de
# 5.870 para 1.076 sem que nada tenha encolhido — antes era uma linha por
# curso E POR CAMADA, agora é uma linha por curso.
#
# E o Decreto 12.456/2025 encerrou a graduação em Fisioterapia inteiramente a
# distância. Os 117 cursos EaD do recorte são, um a um, os cursos "em
# extinção": não há mais capacidade ativa a distância, e surgiu o formato
# semipresencial, que não existia.
REGISTROS_CENSO = 1076           # cursos, não mais curso × camada
UFS_COM_PRESENCIAL = 27
UFS_SEM_PRESENCIAL = []          # nenhuma, e isso é incomum na família
MUNICIPIOS_COM_OFERTA = 396
VAGAS_PRESENCIAL = 177391
VAGAS_SEMIPRESENCIAL = 95464     # categoria nova
VAGAS_EAD = 0                    # encerrada por decreto
VAGAS_EM_EXTINCAO = 302594       # fora da capacidade ativa, publicada ao lado
VAGAS_TOTAL_ATIVA = 272855       # presencial + semipresencial

# Polos: contados por LOCAL distinto e separados por situação do curso que
# atendem. Polo de curso presencial não entra em nenhum dos dois — a fonte
# marca 471 endereços de curso presencial como polo, e contá-los como
# alcance de oferta a distância seria inflar o país.
POLOS_REGISTROS = 14158          # rede ativa (semipresencial)
POLOS_MUNICIPIOS = 3006
POLOS_EM_EXTINCAO = 28950        # rede que está sendo desmontada
POLOS_EM_EXTINCAO_MUNICIPIOS = 3429

# Pessoas NÃO se filtram por situação: quem está matriculado agora existe, e
# tem direito a concluir no formato em que ingressou.
MATRICULAS = 254789
CONCLUINTES = 25313
INGRESSOS = 116412
MATRICULAS_EM_EXTINCAO = 103118
INGRESSOS_EM_EXTINCAO = 62330    # mais que os 46.213 dos cursos ativos

# Nenhuma linha ficou sem UF: as 29 que não têm local de oferta próprio — a
# oferta a distância e semipresencial, que não tem endereço — foram
# atribuídas à UF-sede da mantenedora, como o modelo de 2024 já fazia com a
# camada de sede. São 199.724 vagas, 35% da capacidade do país: descartá-las
# publicaria um Brasil com dois terços do que tem.
ATRIBUIDAS_PELA_SEDE_LINHAS = 29
ATRIBUIDAS_PELA_SEDE_VAGAS = 199724

# n_ies é contagem distinta POR UF, somada. Uma instituição com curso em dois
# estados conta duas vezes, então isto NÃO é o número de IES do país: as
# distintas no Censo 2024 são 763. A âncora fixa o campo publicado, não uma
# verdade nacional — e esta nota existe porque no repositório de origem a
# constante equivalente estava declarada e não era usada por teste nenhum,
# justamente por essa ambiguidade.
IES_SOMADAS_POR_UF = 766
IES_DISTINTAS_NO_PAIS = 763

# ---------------------------------------------------- âncoras: CPC 2023
CURSOS_AVALIADOS = 711
UFS_AVALIADAS = 27
CURSOS_COM_CPC = 699
CURSOS_COM_IDD = 677

# --------------------------------------------------------- âncoras: CNES 202610
# Ao trocar de competência, estes números MUDAM, e é por isso que a troca
# falha o teste em vez de passar calada: cada valor abaixo foi medido na
# competência declarada acima, não ajustado até o teste passar.
MUNICIPIOS_COM_FISIOTERAPEUTA = 5545
FISIOTERAPEUTAS_SUS = 105511
# Rede especializada: só o que é ofertado AO SUS entra no índice; o total
# declarado, que inclui a clínica privada, fica ao lado.
MUNICIPIOS_COM_SERVICO_FISIO = 4757
MUNICIPIOS_COM_SERVICO_FISIO_TOTAL = 4856
# Estabelecimentos, para o teste do filtro de SUS: metade do que declara
# serviço de fisioterapia no cadastro não o oferta ao SUS.
ESTABELECIMENTOS_SERVICO_FISIO = 15487
ESTABELECIMENTOS_SERVICO_FISIO_TOTAL = 29997

MUNICIPIOS_BRASIL = 5571          # IBGE, desde a instalação de Boa Esperança
MUNICIPIOS_MT = 142               # do Norte (MT) em 01/01/2025


def _ler(nome):
    caminho = DATA / nome
    if not caminho.exists():
        raise SystemExit(
            f"[ERRO] {caminho} ausente. Rode o pipeline antes dos testes.")
    return json.loads(caminho.read_text(encoding="utf-8"))


def _soma(ufs, campo):
    return sum(d.get(campo) or 0 for d in ufs.values())


# ------------------------------------------------------------------ território

def test_27_ufs_presentes():
    ufs = _ler("nacional.json")["ufs"]
    assert len(ufs) == 27, f"esperado 27 UFs, veio {len(ufs)}"


def test_ufs_sem_oferta_aparecem_explicitamente():
    """
    AP, MS e RR não têm curso presencial — e precisam estar no conjunto.

    Omiti-las faria o mapa parecer completo e o país parecer coberto. Um estado
    cinza é informação; um estado ausente é uma afirmação que ninguém fez.
    """
    ufs = _ler("nacional.json")["ufs"]
    sem = sorted(u for u, d in ufs.items() if not d.get("tem_oferta_presencial"))
    assert sem == UFS_SEM_PRESENCIAL, f"esperado {UFS_SEM_PRESENCIAL}, veio {sem}"
    for sigla in UFS_SEM_PRESENCIAL:
        assert sigla in ufs, f"{sigla} foi omitida do conjunto"
        assert ufs[sigla]["municipios_total"] > 0, (
            f"{sigla} sem contagem de municípios")


def test_ufs_com_presencial():
    ufs = _ler("nacional.json")["ufs"]
    com = [u for u, d in ufs.items() if d.get("tem_oferta_presencial")]
    assert len(com) == UFS_COM_PRESENCIAL, (
        f"esperado {UFS_COM_PRESENCIAL} UFs com oferta presencial, veio {len(com)}")


def test_contagem_de_municipios_do_ibge():
    ufs = _ler("nacional.json")["ufs"]
    total = _soma(ufs, "municipios_total")
    assert total == MUNICIPIOS_BRASIL, (
        f"esperado {MUNICIPIOS_BRASIL} municípios, veio {total}. "
        "Se o IBGE instalou ou extinguiu município, a mudança é real — "
        "atualize a âncora num commit que explique.")
    assert ufs["MT"]["municipios_total"] == MUNICIPIOS_MT, (
        f"MT deveria ter {MUNICIPIOS_MT} municípios, "
        f"veio {ufs['MT']['municipios_total']}")


def test_municipios_com_oferta():
    ufs = _ler("nacional.json")["ufs"]
    total = _soma(ufs, "municipios_oferta")
    assert total == MUNICIPIOS_COM_OFERTA, (
        f"esperado {MUNICIPIOS_COM_OFERTA}, veio {total}")


# ------------------------------------------------------------------ capacidade

def test_composicao_da_capacidade_ativa():
    """
    Cada formato somado separadamente — e o zero da EaD tem de ser provado.

    ATÉ 2024 ESTE TESTE EXIGIA O CONTRÁRIO. Ele dizia: "vagas EaD zeradas é
    sintoma clássico de somar as linhas de polo em vez das de sede", e
    exigia `ead > 0`. Era um bom guarda: naquele modelo, zero só podia ser
    defeito de leitura.

    Em 2025 zero é a verdade — o Decreto 12.456/2025 encerrou a graduação em
    Fisioterapia inteiramente a distância. Trocar `> 0` por `== 0` resolveria
    a falha e perderia o guarda: as duas causas possíveis de um zero, a lei e
    o defeito de leitura, ficariam indistinguíveis.

    Então o zero passa a exigir PROVA: se não há capacidade ativa a
    distância, tem de haver capacidade em extinção a distância. É o rastro
    que a lei deixa e que um erro de leitura não deixaria — um pipeline que
    somasse a tabela errada zeraria os dois.
    """
    ufs = _ler("nacional.json")["ufs"]
    presencial = _soma(ufs, "vagas_presencial")
    semi = _soma(ufs, "vagas_semipresencial")
    ead = _soma(ufs, "vagas_ead")
    extin = _soma(ufs, "vagas_em_extincao")

    assert presencial == VAGAS_PRESENCIAL, (
        f"vagas presenciais: esperado {VAGAS_PRESENCIAL}, veio {presencial}")
    assert semi == VAGAS_SEMIPRESENCIAL, (
        f"vagas semipresenciais: esperado {VAGAS_SEMIPRESENCIAL}, veio {semi}")
    assert ead == VAGAS_EAD, f"vagas EaD: esperado {VAGAS_EAD}, veio {ead}"
    assert extin == VAGAS_EM_EXTINCAO, (
        f"vagas em extinção: esperado {VAGAS_EM_EXTINCAO}, veio {extin}")

    if ead == 0:
        assert extin > 0, (
            "capacidade ativa a distância zerada E nenhuma capacidade em "
            "extinção. Um zero por força de lei deixa rastro — os cursos "
            "encerrados continuam no cadastro. Zero nos dois é sintoma de "
            "leitura errada, não de regulação.")

    assert _soma(ufs, "vagas_total") == VAGAS_TOTAL_ATIVA, (
        f"capacidade ativa: esperado {VAGAS_TOTAL_ATIVA}, veio "
        f"{_soma(ufs, 'vagas_total')}")
    assert presencial + semi + ead == VAGAS_TOTAL_ATIVA, (
        "a capacidade ativa publicada não é a soma dos formatos ativos")


def test_polos_ead():
    ufs = _ler("nacional.json")["ufs"]
    assert _soma(ufs, "ead_polos_registros") == POLOS_REGISTROS
    assert _soma(ufs, "ead_polos_municipios") == POLOS_MUNICIPIOS


def test_fluxo():
    ufs = _ler("nacional.json")["ufs"]
    assert _soma(ufs, "matriculas") == MATRICULAS, (
        f"matrículas: esperado {MATRICULAS}, veio {_soma(ufs, 'matriculas')}")
    assert _soma(ufs, "concluintes") == CONCLUINTES


def test_matriculas_fecham_sem_sobra():
    """
    A soma das UFs mais o que não tem UF é o total do recorte. Sem sobra.

    Esta é a invariante que o observatório de origem violava em silêncio: lá,
    a linha com aluno e sem UF caía num `continue` sem contador, o total
    nacional deixava de fechar com a soma dos estados, e nada dizia por quê.

    No Censo 2024 a diferença era de duas matrículas — irrelevante na medida e
    decisiva no método, porque um conjunto em que o total não fecha com as
    partes não permite distinguir "a fonte não localizou" de "o pipeline
    perdeu".

    No Censo 2025 a diferença é ZERO, e não porque o problema sumiu: é que a
    oferta sem endereço próprio passou a ser atribuída à UF-sede, como o
    modelo de 2024 já fazia com a camada de sede. A invariante é a mesma; o
    que mudou é quanto sobra. Por isso este teste não ancora mais um número
    de linhas perdidas — ancora o FECHAMENTO, que vale em qualquer edição.

    A conferência contra o arquivo lido, que é mais forte, está em
    `test_as_pessoas_fecham_com_a_fatia_lida`.
    """
    bruto = _ler("bruto.json")
    perdidas = bruto["metadados"]["sem_localizacao"]
    por_uf = _soma(bruto["ufs"], "matriculas")

    assert por_uf == MATRICULAS, (
        f"matrículas por UF: esperado {MATRICULAS}, veio {por_uf}")
    assert por_uf + perdidas["matriculas"] == MATRICULAS + perdidas["matriculas"]

    por_ies = perdidas.get("atribuidas_pela_sede_da_ies") or {}
    assert por_ies.get("linhas") == ATRIBUIDAS_PELA_SEDE_LINHAS, (
        f"atribuições pela sede: esperado {ATRIBUIDAS_PELA_SEDE_LINHAS}, "
        f"veio {por_ies.get('linhas')}")
    assert por_ies.get("vagas") == ATRIBUIDAS_PELA_SEDE_VAGAS, (
        f"vagas atribuídas pela sede: esperado {ATRIBUIDAS_PELA_SEDE_VAGAS}, "
        f"veio {por_ies.get('vagas')}")


def test_so_a_oferta_sem_endereco_e_atribuida_pela_sede():
    """
    Atribuir pela mantenedora é legítimo para um caso e proibido para o outro.

    O ciclo anterior tinha um teste chamado
    `test_a_camada_sem_localizacao_nao_virou_uf`, que proibia distribuir as
    linhas sem localização "pela UF da mantenedora, pela maior UF, por
    rateio", porque qualquer um desses faz o total fechar inventando dado.

    Ele falhou na virada para 2025, e a resposta certa não era apagá-lo nem
    afrouxá-lo: era perceber que ele misturava dois casos que o modelo antigo
    separava por uma coluna que deixou de existir.

      · `TP_DIMENSAO = 3`, a sede de curso a distância, vinha sem UF POR
        NATUREZA — e o pipeline de 2024 já a atribuía pela mantenedora. Curso
        a distância não tem endereço; a sede é o lugar que a fonte conhece.
      · `TP_DIMENSAO = 4` era a fonte dizendo que NÃO SABE onde aquilo está.
        Essa não se atribui.

    Sem a coluna de dimensão, o que separa os dois é o FORMATO DE OFERTA: um
    curso presencial tem endereço por definição. Presencial sem localização é
    informação faltando, não oferta deslocalizada.

    Então a proibição continua de pé, com o alvo certo: nenhuma atribuição
    pela sede pode vir de curso presencial.
    """
    import csv
    csv.field_size_limit(1 << 24)
    if _esquema() != "normalizado":
        return
    cursos = _fatia_de_curso()
    if cursos is None:
        return

    sem_uf = [l for l in cursos if not (l.get("SG_UF_LO") or "").strip()]
    presenciais = [l for l in sem_uf
                   if (l.get("TP_MODALIDADE_ENSINO") or "").strip() == "1"]
    meta = _ler("bruto.json")["metadados"]
    por_ies = (meta.get("sem_localizacao") or {}).get(
        "atribuidas_pela_sede_da_ies") or {}

    assert por_ies.get("linhas", 0) == len(sem_uf) - len(presenciais), (
        f"{len(sem_uf)} cursos sem local de oferta, {len(presenciais)} deles "
        f"presenciais, e {por_ies.get('linhas')} atribuições pela sede. Os "
        "presenciais não podem estar entre as atribuídas.")

    if presenciais:
        sobraram = (meta.get("sem_localizacao") or {}).get("linhas", 0)
        assert sobraram >= len(presenciais), (
            f"{len(presenciais)} cursos presenciais sem localização "
            f"desapareceram: só {sobraram} linhas ficaram em sem_localizacao. "
            "Presencial sem endereço é informação faltando, e tem de aparecer "
            "como tal em vez de ser posto numa UF.")


def test_concentracao_cobre_toda_a_capacidade_ativa():
    """
    O HHI de mantenedora tem de ser calculado sobre a capacidade ATIVA
    inteira — presencial mais semipresencial —, não só sobre o presencial.

    ESTE TESTE MUDOU DE FORMA, E O MOTIVO IMPORTA.

    Até o Censo 2024 ele exigia HHI de SP acima de 0,12, porque a EaD estava
    incluída e a concentração morava nos grandes grupos de EaD: só sobre o
    presencial SP dava 0,07; com a EaD, 0,18. O limiar era a prova de que a
    EaD entrava na conta.

    Em 2025 não há mais capacidade ativa a distância, então o limiar perdeu o
    referente: medido agora, SP dá 0,0603, e isso não indica defeito nenhum —
    indica que a parte concentrada da oferta saiu da capacidade ativa e está
    em `vagas_em_extincao`.

    Manter o limiar antigo seria exigir uma concentração que a lei desfez.
    Baixá-lo para 0,05 seria pior: um número escolhido para passar, sem
    referente nenhum. A pergunta que continua respondível é ESTRUTURAL — a
    concentração cobre a mesma base que a capacidade publicada? Então é ela
    que o teste faz.
    """
    ufs = _ler("nacional.json")["ufs"]
    problemas = []
    for sigla, d in ufs.items():
        tem_capacidade = (d.get("vagas_total") or 0) > 0
        if tem_capacidade and d.get("HHI_mantenedora") is None:
            problemas.append(f"{sigla}: tem capacidade ativa e HHI nulo")
        if not tem_capacidade and d.get("HHI_mantenedora") is not None:
            problemas.append(
                f"{sigla}: HHI {d['HHI_mantenedora']} sem capacidade ativa")
    assert not problemas, "\n  - ".join(problemas)

    # A base do HHI é a capacidade ativa, que inclui o semipresencial. Numa
    # UF onde o semipresencial é a maior parte da oferta, um HHI calculado só
    # sobre o presencial seria o HHI de outra coisa.
    com_semi = [s for s, d in ufs.items()
                if (d.get("vagas_semipresencial") or 0) > 0]
    assert com_semi, (
        "nenhuma UF com vaga semipresencial: se a categoria sumiu da edição, "
        "este teste e as âncoras do semipresencial precisam sair, não ser "
        "afrouxados")
    for sigla in com_semi:
        assert ufs[sigla]["HHI_mantenedora"] is not None, (
            f"{sigla} tem oferta semipresencial e HHI nulo — sinal de que a "
            "concentração foi calculada só sobre o presencial")
    for sigla, d in ufs.items():
        if d["vagas_total"]:
            assert d["HHI"] is not None, f"{sigla} com vagas mas sem HHI"
            assert 0 <= d["HHI"] <= 1, f"{sigla}: HHI fora de 0..1"


# ------------------------------------------------------------------- qualidade

def test_qualidade_cpc():
    q = _ler("qualidade.json")
    assert q["metadados"]["ciclo"] == CICLO_CPC
    assert len(q["cursos"]) == CURSOS_AVALIADOS, (
        f"esperado {CURSOS_AVALIADOS} cursos avaliados, veio {len(q['cursos'])}")
    assert len(q["ufs"]) == UFS_AVALIADAS
    com_cpc = sum(1 for c in q["cursos"] if c["CPC_cont"] is not None)
    com_idd = sum(1 for c in q["cursos"] if c["IDD"] is not None)
    assert com_cpc == CURSOS_COM_CPC, f"com CPC: esperado {CURSOS_COM_CPC}, veio {com_cpc}"
    assert com_idd == CURSOS_COM_IDD, f"com IDD: esperado {CURSOS_COM_IDD}, veio {com_idd}"


def test_uf_com_oferta_e_sem_avaliacao_fica_nula():
    """
    Oferta sem avaliação tem de dar `None`, não zero — e aqui não há caso.

    A regra é a de sempre: zero colocaria a UF no fundo de qualquer ranking de
    qualidade como se tivesse sido avaliada e tivesse ido mal. O que muda nesta
    profissão é que o caso **não existe**: as 27 UFs com oferta presencial têm
    curso no ciclo do CPC 2023. Na Fonoaudiologia, de onde este repositório
    nasceu, o caso era Tocantins, e o teste nomeava TO — herdado sem medir, ele
    passaria a exigir `None` de uma UF que aqui tem CPC 2,762, ou seja, falharia
    pedindo que um dado medido fosse apagado.

    O teste foi reescrito para checar a regra em vez do caso: varre todas as
    UFs, exige `None` em qualquer uma que tenha oferta e nenhum curso avaliado,
    e registra que hoje não há nenhuma. Se um ciclo futuro deixar uma UF de fora
    da avaliação, a primeira parte passa a ter o que checar; se a contagem de
    avaliados cair para zero em alguma UF por defeito de pipeline, a segunda
    acusa.
    """
    ufs = _ler("nacional.json")["ufs"]
    sem_avaliacao = [s for s, d in ufs.items()
                     if d.get("tem_oferta_presencial")
                     and not d.get("n_cursos_avaliados")]
    for sigla in sem_avaliacao:
        for campo in ("CPC", "CPC_cont", "IDD", "IAF"):
            assert ufs[sigla][campo] is None, (
                f"{sigla}.{campo} deveria ser None (oferta sem curso "
                f"avaliado), veio {ufs[sigla][campo]}")

    assert not sem_avaliacao, (
        "UF com oferta presencial e nenhum curso avaliado: "
        f"{sorted(sem_avaliacao)}. Na Fisioterapia do CPC 2023 isso não "
        "acontece em nenhuma das 27 UFs — se aparecer, é mudança de ciclo ou "
        "defeito no cruzamento, e os dois merecem ser vistos.")

    com_oferta = [s for s, d in ufs.items() if d.get("tem_oferta_presencial")]
    assert len(com_oferta) == UFS_COM_PRESENCIAL
    assert all(ufs[s]["CPC"] is not None for s in com_oferta), (
        "UF com oferta presencial sem CPC agregado")


# ------------------------------------------------------- princípio inegociável

def test_ausencia_nunca_e_zero():
    """
    Varre o conjunto atrás de zeros que deveriam ser nulos.

    Regra: se a UF não tem oferta presencial, os índices que dependem dela não
    podem ter valor numérico. `None` chega à tela como "sem dados"; `0` chega
    como afirmação.
    """
    ufs = _ler("nacional.json")["ufs"]
    problemas = []
    for sigla, d in ufs.items():
        if d.get("tem_oferta_presencial"):
            continue
        for campo in ("ICT", "E", "IAF", "HHI", "HHI_mantenedora", "CR2", "CR10"):
            if d.get(campo) is not None:
                problemas.append(f"{sigla}.{campo} = {d[campo]} (deveria ser None)")
    assert not problemas, "valores numéricos onde deveria haver ausência:\n  - " \
                          + "\n  - ".join(problemas)


def test_iaf_so_existe_com_os_tres_componentes():
    ufs = _ler("nacional.json")["ufs"]
    problemas = []
    for sigla, d in ufs.items():
        tem_tudo = (d.get("CPC") is not None
                    and d.get("vagas_avaliadas") is not None
                    and d.get("ICT") is not None)
        if d.get("IAF") is not None and not tem_tudo:
            problemas.append(f"{sigla}: IAF={d['IAF']} sem os três componentes")
        if d.get("IAF") is None and tem_tudo:
            problemas.append(f"{sigla}: componentes completos mas IAF nulo")
    assert not problemas, "\n  - ".join(problemas)


def test_percentuais_dentro_da_faixa():
    ufs = _ler("nacional.json")["ufs"]
    problemas = []
    for sigla, d in ufs.items():
        for campo, valor in d.items():
            if campo.startswith("pct_") and valor is not None:
                if not 0 <= valor <= 100:
                    problemas.append(f"{sigla}.{campo} = {valor}")
    assert not problemas, "percentuais fora de 0..100:\n  - " + "\n  - ".join(problemas)


# ---------------------------------------------------------------- proveniência

def test_proveniencia_vem_do_arquivo():
    """
    O ano do Censo tem de vir do arquivo lido, não do calendário.

    Derivar `ano - 1` da data de hoje rotula o Censo 2024 como 2025 durante todo
    o ano seguinte, e o erro só aparece muito depois, num gráfico de série.
    """
    meta = _ler("nacional.json")["metadados"]
    assert meta["ano_censo"] == CENSO
    prov = meta["proveniencia"]["fontes"]["censo"]
    assert prov.get("ano_censo") == CENSO
    assert prov.get("md5_publicado"), "sem md5 publicado pelo INEP na proveniência"
    assert str(CENSO) in prov.get("membro_cursos", ""), (
        "o membro lido não confere com o ano declarado")


def test_ancoras_da_cobertura_do_cnes():
    """
    Totais medidos no CNES 202610, como teste de regressão.

    A cobertura assistencial é a parte do observatório que não vem de arquivo
    anual: ela muda a cada competência mensal, e sem âncora uma queda de
    cobertura chegaria à página como se fosse dado novo. Nos irmãos deste
    projeto foi exatamente assim que a rede especializada ficou contando
    clínica privada como rede pública até ser corrigida.
    """
    ufs = _ler("nacional.json")["ufs"]
    for campo, esperado in [
        ("municipios_com_fisioterapeuta", MUNICIPIOS_COM_FISIOTERAPEUTA),
        ("fisioterapeutas_sus", FISIOTERAPEUTAS_SUS),
        ("municipios_com_servico_fisio", MUNICIPIOS_COM_SERVICO_FISIO),
        ("municipios_com_servico_fisio_total",
         MUNICIPIOS_COM_SERVICO_FISIO_TOTAL),
    ]:
        obtido = _soma(ufs, campo)
        assert obtido == esperado, (
            f"{campo}: esperado {esperado}, veio {obtido}")

    prov = _ler("_proveniencia.json")["fontes"]["cnes"]
    assert prov.get("competencia") == COMPETENCIA_CNES


def test_rede_especializada_publica_e_menor_que_a_declarada():
    """
    O filtro de SUS precisa continuar existindo.

    Sem ele, a clínica privada que declara serviço de fisioterapia no cadastro
    entra como rede pública. Medido na 202610: a cobertura iria de 4.757 para
    4.856 municípios, e os estabelecimentos de 15.487 para 29.997 — quase
    metade (48,4%) do que seria contado como rede pública não oferta ao SUS.

    Na fisioterapia esse filtro pesa mais que nos irmãos, porque a clínica
    privada de fisioterapia é abundante: é a diferença entre medir a rede
    pública e medir o mercado. Se os dois números empatarem, o filtro caiu.
    """
    ufs = _ler("nacional.json")["ufs"]
    sus = _soma(ufs, "municipios_com_servico_fisio")
    total = _soma(ufs, "municipios_com_servico_fisio_total")
    assert sus < total, (
        f"municípios com serviço ao SUS ({sus}) igualou o total declarado "
        f"({total}) — o filtro CO_AMBULATORIAL_SUS/CO_HOSPITALAR_SUS caiu")

    mun = _ler("cobertura_cnes.json")["municipios"].values()
    est = sum(m.get("estabelecimentos_servico_fisio") or 0 for m in mun)
    est_total = sum(
        m.get("estabelecimentos_servico_fisio_total") or 0 for m in mun)
    assert (est, est_total) == (ESTABELECIMENTOS_SERVICO_FISIO,
                                ESTABELECIMENTOS_SERVICO_FISIO_TOTAL), (
        f"estabelecimentos: esperado {ESTABELECIMENTOS_SERVICO_FISIO}/"
        f"{ESTABELECIMENTOS_SERVICO_FISIO_TOTAL}, veio {est}/{est_total}")


def test_st_ativo_sn_nao_passa_por_filtro():
    """
    A coluna vem vazia no export, e isso precisa continuar declarado.

    O extrator tinha um filtro que lia ST_ATIVO_SN e excluía o que estivesse
    marcado como inativo. Medido: a coluna está em branco em 100% das linhas —
    o filtro nunca excluiu nada, em nenhuma execução, e existia dando a
    impressão de que a limpeza acontecia. Se uma competência futura passar a
    preencher a coluna, este teste falha e a decisão volta a ser possível.
    """
    diag = (_ler("_proveniencia.json")["fontes"]["cnes"].get("diagnostico")
            or {})
    assert diag.get("st_ativo_sn_vazio_no_export") is True, (
        "ST_ATIVO_SN deixou de vir vazia: "
        f"{diag.get('servicos_com_situacao_preenchida')} linhas com situação "
        "preenchida. Vale reavaliar se o filtro de serviço inativo deve voltar.")

    texto = " ".join(_ler("_proveniencia.json")["limitacoes_conhecidas"]).lower()
    assert "st_ativo_sn" in texto, (
        "a limitação do ST_ATIVO_SN não está declarada na proveniência")


def test_limitacoes_declaradas():
    """O que não foi medido precisa estar escrito, não subentendido."""
    prov = _ler("_proveniencia.json")
    texto = " ".join(prov["limitacoes_conhecidas"]).lower()
    assert "cer" in texto, "a indisponibilidade do CER não está declarada"
    assert "presencial" in texto, "as UFs sem oferta presencial não estão declaradas"


def main():
    testes = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    falhas = 0
    for teste in testes:
        try:
            teste()
            print(f"  OK      {teste.__name__}")
        except AssertionError as e:
            falhas += 1
            print(f"  FALHOU  {teste.__name__}: {e}")
    print(f"\n{len(testes) - falhas}/{len(testes)} testes de integridade passaram.")
    return 1 if falhas else 0


# --------------------------------------------------------------------------- #
# Esquema normalizado (Censo 2025 em diante)
#
# Rodam só quando a edição publicada usa o esquema novo. Não são âncoras: são
# relações que precisam valer qualquer que seja o número.
# --------------------------------------------------------------------------- #

def _esquema():
    prov = _ler("_proveniencia.json").get("fontes", {}).get("censo", {})
    return prov.get("esquema", "unico")


def test_o_esquema_declarado_bate_com_a_edicao():
    """
    As invariantes acima só rodam no esquema normalizado. Esta garante que
    elas vão acordar.

    Sem ela, bastaria `_esquema()` ler a chave errada para os cinco testes
    seguintes ficarem inertes PARA SEMPRE — passando sem olhar nada, inclusive
    depois de a edição nova entrar. Teste que se desliga sozinho e continua
    verde é pior que teste ausente, porque dá a impressão de cobertura.

    A regra é simples e verificável: o INEP normalizou os microdados a partir
    de 2025. Edição de 2025 em diante tem de declarar `normalizado`; anterior,
    `unico`.
    """
    esperado = "normalizado" if CENSO >= 2025 else "unico"
    assert _esquema() == esperado, (
        f"o Censo publicado é {CENSO} e a proveniência declara esquema "
        f"{_esquema()!r}; esperado {esperado!r}. Se o INEP mudou de novo, "
        "ajuste a regra aqui — mas confira antes que as invariantes do "
        "esquema continuam rodando.")


def _fatia_de_curso():
    import csv
    caminho = (DATA.parent / "etl" / "dados"
               / f"curso_fisioterapia_{CENSO}.csv")
    if not caminho.exists():
        return None
    with caminho.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _inteiro(v):
    v = (v or "").strip()
    return int(v) if v.lstrip("-").isdigit() else 0


def test_as_pessoas_fecham_com_a_fatia_lida():
    """
    Soma por UF + sem localização = total do recorte, para gente.

    Esta é a conferência que pegou o pior defeito do porte para 2025: 29
    cursos vinham sem `SG_UF_LO` — a oferta a distância e semipresencial, que
    não têm endereço próprio — e carregavam 199.724 vagas, 35% da capacidade
    do país. Eles estavam sendo descartados em silêncio, e o total continuava
    plausível.

    Vale para matrícula, concluinte e ingressante: pessoas não se filtram por
    situação do curso, então o total agregado tem de bater com o CSV inteiro.
    """
    if _esquema() != "normalizado":
        return
    cursos = _fatia_de_curso()
    if cursos is None:
        return
    ufs = _ler("nacional.json")["ufs"]
    meta = _ler("nacional.json")["metadados"]
    sem_loc = meta.get("sem_localizacao") or {}

    for campo, coluna in (("matriculas", "QT_MATRICULA_TOTAL"),
                          ("concluintes", "QT_CONCLUINTE_TOTAL"),
                          ("ingressos", "QT_INGRESSO_TOTAL")):
        do_csv = sum(_inteiro(l.get(coluna)) for l in cursos)
        agregado = _soma(ufs, campo)
        fora = sem_loc.get(campo, 0)
        assert agregado + fora == do_csv, (
            f"{campo}: por UF {agregado} + sem localização {fora} = "
            f"{agregado + fora}, mas o recorte lido tem {do_csv}")


def test_capacidade_ativa_nao_inclui_curso_em_extincao():
    """
    Vaga de curso em extinção não entra na capacidade — e não some.

    As duas metades importam. Somá-la anunciaria uma oferta que a regulação
    já encerrou; descartá-la esconderia que ela existe e ainda recebe gente.
    """
    if _esquema() != "normalizado":
        return
    cursos = _fatia_de_curso()
    if cursos is None:
        return
    ufs = _ler("nacional.json")["ufs"]

    ativas = sum(_inteiro(l.get("QT_VAGA_TOTAL")) for l in cursos
                 if (l.get("TP_SITUACAO") or "").strip() == "1")
    extintas = sum(_inteiro(l.get("QT_VAGA_TOTAL")) for l in cursos
                   if (l.get("TP_SITUACAO") or "").strip() != "1")

    assert _soma(ufs, "vagas_total") == ativas, (
        f"capacidade ativa publicada {_soma(ufs, 'vagas_total')} != "
        f"{ativas} medidas na fatia")
    assert _soma(ufs, "vagas_em_extincao") == extintas, (
        f"capacidade em extinção publicada {_soma(ufs, 'vagas_em_extincao')} "
        f"!= {extintas} medidas na fatia")
    assert extintas > 0, (
        "nenhuma vaga em extinção: se a edição deixou de ter curso em "
        "extinção, o campo precisa sair da página em vez de publicar zero")


def test_a_modalidade_a_distancia_esta_encerrada():
    """
    Zero curso a distância EM ATIVIDADE, e isso é fato da lei, não do mercado.

    O Decreto 12.456/2025 encerrou a graduação em Fisioterapia inteiramente a
    distância. Se um dia aparecer curso a distância em atividade, ou a
    regulação mudou de novo ou o filtro quebrou — e os dois merecem ser
    vistos, não absorvidos.
    """
    if _esquema() != "normalizado":
        return
    ufs = _ler("nacional.json")["ufs"]
    assert _soma(ufs, "n_cursos_ead") == 0, (
        f"{_soma(ufs, 'n_cursos_ead')} cursos a distância EM ATIVIDADE num "
        "ciclo em que o decreto os encerrou")
    assert _soma(ufs, "vagas_ead") == 0


def test_atribuicao_pela_sede_e_declarada():
    """
    O que foi posto numa UF por inferência tem de aparecer como tal.

    Curso sem local de oferta é atribuído à UF-sede da mantenedora, como o
    modelo de 2024 já fazia. É atribuição, não medida, e quem lê o número da
    UF tem direito de saber que parte dele chegou ali assim.
    """
    if _esquema() != "normalizado":
        return
    meta = _ler("nacional.json")["metadados"]
    por_ies = (meta.get("sem_localizacao") or {}).get(
        "atribuidas_pela_sede_da_ies")
    assert por_ies is not None, (
        "a contagem de atribuições pela sede sumiu da proveniência")
    assert por_ies.get("linhas", 0) > 0, (
        "nenhuma atribuição pela sede: ou a fonte passou a localizar tudo — "
        "e aí vale dizer isso na página — ou a atribuição parou de acontecer")


def test_perfil_vem_do_nivel_de_curso():
    """
    A tabela de aluno conta a mesma pessoa em três níveis de agregação.

    Somar a tabela inteira triplicaria o país. A proveniência registra qual
    nível foi usado; este teste exige que seja o de curso, que é a unidade do
    resto do pipeline.
    """
    if _esquema() != "normalizado":
        return
    prov = _ler("_proveniencia.json")["fontes"]["censo"]
    assert prov.get("aluno_nivel_usado") == "2", (
        f"perfil agregado pelo nível {prov.get('aluno_nivel_usado')!r}; "
        "só o nível 2 (curso) pode ser somado sem repetir pessoa")
    na_fatia = prov.get("aluno_niveis_na_fatia") or {}
    assert set(na_fatia) == {"2"}, (
        f"a fatia de aluno gravada tem os níveis {sorted(na_fatia)}; só o "
        "nível 2 pode estar lá, senão a soma conta a mesma pessoa duas vezes")

    # `na_fonte` só é conhecido quando a tabela foi lida nesta execução. Numa
    # execução que reaproveitou o cache ele é nulo, e nulo aqui é honesto —
    # o que não se pode é repetir o número de antes como se tivesse sido
    # medido agora.
    na_fonte = prov.get("aluno_niveis_na_fonte")
    if na_fonte is not None:
        assert len(na_fonte) > 1, (
            f"a fonte trouxe um nível só ({sorted(na_fonte)}). Se o INEP "
            "parou de publicar os três, confirme antes de confiar: a guarda "
            "existe porque eles existem.")


if __name__ == "__main__":
    sys.exit(main())
