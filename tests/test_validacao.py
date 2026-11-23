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

CENSO = 2024
CICLO_CPC = "2023"
COMPETENCIA_CNES = "202610"

# -------------------------------------------------- âncoras: Censo 2024
REGISTROS_CENSO = 5870
UFS_COM_PRESENCIAL = 27
UFS_SEM_PRESENCIAL = []          # nenhuma, e isso é incomum na família
MUNICIPIOS_COM_OFERTA = 380
VAGAS_PRESENCIAL = 164661
VAGAS_EAD = 272000
POLOS_REGISTROS = 4837
POLOS_MUNICIPIOS = 1561

# Matrículas SOMADAS POR UF. O total nacional é 227.223: a diferença de 2 é a
# linha de TP_DIMENSAO = 4, que tem aluno e não tem UF. Ela não é perdida —
# está em `metadados.sem_localizacao` e é conferida por
# `test_matriculas_fecham_com_a_camada_sem_localizacao`.
MATRICULAS = 227221
CONCLUINTES = 24425

# A camada sem localização, medida: uma linha, duas matrículas.
REGISTROS_SEM_LOCALIZACAO = 1
REGISTROS_SEM_LOCALIZACAO_MATRICULAS = 2
MATRICULAS_NO_RECORTE = 227223        # = MATRICULAS + as 2 sem UF

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

def test_vagas_presenciais_e_ead():
    """
    As duas camadas da EaD somadas separadamente.

    Somar QT_VG_TOTAL por SG_UF sem separar sede de polo devolve vagas EaD
    zeradas — e o resultado parece plausível, que é o que torna o erro caro.
    """
    ufs = _ler("nacional.json")["ufs"]
    presencial = _soma(ufs, "vagas_presencial")
    ead = _soma(ufs, "vagas_ead")
    assert presencial == VAGAS_PRESENCIAL, (
        f"vagas presenciais: esperado {VAGAS_PRESENCIAL}, veio {presencial}")
    assert ead == VAGAS_EAD, f"vagas EaD: esperado {VAGAS_EAD}, veio {ead}"
    assert ead > 0, ("vagas EaD zeradas — sintoma clássico de somar as linhas "
                     "de polo em vez das de sede")


def test_polos_ead():
    ufs = _ler("nacional.json")["ufs"]
    assert _soma(ufs, "ead_polos_registros") == POLOS_REGISTROS
    assert _soma(ufs, "ead_polos_municipios") == POLOS_MUNICIPIOS


def test_fluxo():
    ufs = _ler("nacional.json")["ufs"]
    assert _soma(ufs, "matriculas") == MATRICULAS, (
        f"matrículas: esperado {MATRICULAS}, veio {_soma(ufs, 'matriculas')}")
    assert _soma(ufs, "concluintes") == CONCLUINTES


def test_matriculas_fecham_com_a_camada_sem_localizacao():
    """
    A soma das UFs mais o que não tem UF é o total do recorte. Sem sobra.

    Esta é a invariante que o observatório de origem violava em silêncio. Lá, a
    linha com aluno e sem UF caía num `continue` sem contador: o total nacional
    deixava de fechar com a soma dos estados e nada dizia por quê. Na
    Fonoaudiologia não havia linha assim, então nunca apareceu; na Fisioterapia
    há uma, com 2 matrículas.

    Duas matrículas não movem indicador nenhum. O que elas movem é a
    possibilidade de confiar no resto: um conjunto em que o total não fecha com
    as partes não permite distinguir "a fonte não localizou" de "o pipeline
    perdeu". Enquanto este teste passa, a diferença entre os dois números é
    exatamente o que está declarado — e não uma perda que ninguém mediu.
    """
    bruto = _ler("bruto.json")
    perdidas = bruto["metadados"]["sem_localizacao"]
    por_uf = _soma(bruto["ufs"], "matriculas")

    assert por_uf == MATRICULAS, (
        f"matrículas por UF: esperado {MATRICULAS}, veio {por_uf}")
    assert perdidas["matriculas"] == REGISTROS_SEM_LOCALIZACAO_MATRICULAS, (
        f"matrículas sem localização: esperado "
        f"{REGISTROS_SEM_LOCALIZACAO_MATRICULAS}, veio {perdidas['matriculas']}")
    assert perdidas["linhas"] == REGISTROS_SEM_LOCALIZACAO, (
        f"linhas sem localização: esperado {REGISTROS_SEM_LOCALIZACAO}, "
        f"veio {perdidas['linhas']}")
    assert por_uf + perdidas["matriculas"] == MATRICULAS_NO_RECORTE, (
        f"a soma das UFs ({por_uf}) mais o sem localização "
        f"({perdidas['matriculas']}) deu "
        f"{por_uf + perdidas['matriculas']}, e o recorte tem "
        f"{MATRICULAS_NO_RECORTE} — há matrícula entrando ou saindo sem "
        "declaração")


def test_a_camada_sem_localizacao_nao_virou_uf():
    """
    O que não tem UF não pode ter sido atribuído a nenhuma.

    O conserto errado para a invariante acima é distribuir as linhas sem
    localização — pela UF da mantenedora, pela maior UF, por rateio. Qualquer
    um desses faz o total fechar e inventa dado: a fonte não diz onde aquele
    aluno está, e o observatório que decide por ela deixa de ser verificável.
    """
    meta = _ler("bruto.json")["metadados"]
    assert meta["sem_localizacao"]["linhas"] > 0, (
        "não há linha sem localização no recorte — se a edição nova do Censo "
        "deixou de trazê-las, apague estes dois testes e as constantes, em vez "
        "de afrouxá-los")
    # A dimensão é a 4, e nomeá-la aqui faz o teste falhar se aparecer uma
    # quinta natureza de linha — que é informação, não detalhe.
    assert set(meta["sem_localizacao"]["dimensoes"]) == {"4"}, (
        "apareceu linha sem localização em dimensão diferente da 4: "
        f"{meta['sem_localizacao']['dimensoes']}. Veja o que a camada nova "
        "significa antes de somá-la à que já existe.")


def test_concentracao_inclui_ead():
    """
    HHI de mantenedora precisa refletir a capacidade total.

    Calculado só sobre o presencial, SP dá 0,07 — como se o estado tivesse um
    mercado pulverizado. Com a EaD atribuída à UF-sede, dá 0,18. A concentração
    mora justamente nos grandes grupos de EaD.
    """
    ufs = _ler("nacional.json")["ufs"]
    sp = ufs["SP"]
    assert sp["HHI_mantenedora"] is not None
    assert sp["HHI_mantenedora"] > 0.12, (
        f"HHI_mantenedora de SP = {sp['HHI_mantenedora']}; abaixo de 0,12 "
        "indica cálculo feito só sobre o presencial")
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


if __name__ == "__main__":
    sys.exit(main())
