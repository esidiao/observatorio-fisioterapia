"""
tests/test_sem_vazamento.py
Nenhum observatório irmão pode aparecer neste repositório por descuido.

POR QUE ESTE TESTE EXISTE
-------------------------
Este projeto nasceu de uma cópia do Observatório da Fonoaudiologia, e cópia é
exatamente o que não se vê. O risco foi medido num irmão: a Odontologia, que
nasceu da Psicologia, se apresentava a INEP e DATASUS com o `User-Agent`
`observatorio-psicologia/1.0` — a linha veio na cópia e sobreviveu à revisão,
porque parecer idêntica ao original é o que uma cópia faz quando ninguém olha.
Só foi encontrada meses depois, por uma ferramenta que comparava os módulos de
rede dos irmãos.

O defeito não era cosmético. O User-Agent é o canal por onde o operador de um
servidor público reclama de tráfego indevido ou avisa de mudança: apontando
para o projeto errado, o aviso chega a quem não pode agir. E a proveniência,
que estes projetos publicam para que a origem de cada número seja verificável,
afirmava uma origem que não era a verdadeira.

Na construção deste repositório a passada mecânica de renomeação deixou sete
restos, dois deles CORROMPIDOS — comentários que, renomeados, passaram a
afirmar coisas falsas sobre a Fisioterapia com a mesma aparência de rigor do
original. Foram corrigidos à mão. Este teste existe para que o próximo resto
não sobreviva ao commit.

O QUE ELE NÃO FAZ
-----------------
Não proíbe mencionar os irmãos. Mencioná-los é correto e acontece de propósito
em vários lugares: o README aponta para a ferramenta compartilhada, o
`extrair_cnes.py` explica que a família de CBO aqui NÃO é homogênea como a
deles, o `indices.py` registra que o ICON de Farmácia não transfere. Menção
deliberada em prosa é conhecimento; nome de irmão em identificador, caminho,
URL ou rótulo de interface é resto de cópia.

A distinção é feita por ONDE o nome aparece, não por quanto.
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

IRMAOS = ("fonoaudiologia", "fonoaudiólogo", "fonoaudiologo", "psicologia",
          "psicólogo", "psicologo", "odontologia", "farmacia", "farmácia",
          "administracao", "administração", "fono", "odonto", "psico")

# Arquivos onde o nome do irmão só pode estar em prosa, nunca em código.
CODIGO = {".py", ".js", ".json", ".yml", ".yaml", ".j2", ".css", ".svg"}

PULAR_DIR = (".git/", "site/dist/", "etl/dados/", "site/static/vendor/",
             "site/static/fonts/", "site/static/geo/", "__pycache__/",
             "tests/test_sem_vazamento.py")

# O teste procura IDENTIFICADOR, não prosa.
#
# A primeira versão tentava classificar cada linha como prosa ou código, e
# errava nas duas direções: docstring de várias linhas tem só a primeira linha
# marcada, texto visível de página não tem marcação nenhuma, e o resultado
# acusava menções deliberadas aos irmãos — que são corretas e existem de
# propósito. O README aponta para o observatório de Farmácia e para a
# ferramenta compartilhada; a página de autoria lista as áreas que o autor
# avalia, Odontologia e Psicologia entre elas; o `extrair_cnes.py` explica que
# a família de CBO aqui NÃO é homogênea como a deles. Proibir isso trocaria um
# teste de vazamento por um teste de isolamento, que é outra coisa e é ruim.
#
# A distinção certa é mais simples e não precisa de heurística: prosa não tem
# `snake_case` nem CONSTANTE_EM_CAIXA_ALTA. Então o que se procura é a FORMA do
# identificador, em qualquer lugar do arquivo. "o observatório de Odontologia"
# passa; `municipios_com_fonoaudiologo` não.
#
# Este projeto se identificando como outro — o defeito real que aconteceu num
# irmão — não tem forma de identificador e é coberto separadamente por
# `test_identidade_deste_projeto`, que confere as cadeias pelo nome.
IRMAO = r"(?:fono|odonto|psico|farmacia|fonoaudiolog\w*|psicolog\w*|odontolog\w*)"
SUSPEITO = (
    re.compile(rf"\b\w+_{IRMAO}\b", re.I),        # municipios_com_servico_fono
    re.compile(rf"\b{IRMAO}_\w+", re.I),          # fonoaudiologos_sus
    re.compile(r"\b[A-Z][A-Z0-9_]*(?:FONO|PSICOLOG|ODONTOLOG|FARMACIA)"
               r"[A-Z0-9_]*\b"),                  # FONOAUDIOLOGOS_SUS
)


def _arquivos():
    for p in sorted(REPO.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(REPO).as_posix()
        if any(rel.startswith(d) or f"/{d}" in f"/{rel}" for d in PULAR_DIR):
            continue
        if p.suffix.lower() not in CODIGO and p.suffix.lower() not in {".md", ".txt"}:
            continue
        try:
            yield rel, p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


def test_nenhum_irmao_em_identificador():
    """
    Nome de irmão com forma de identificador é resto de cópia.

    Se este teste falhar num caso que você julga legítimo, a correção não é
    afrouxar o padrão: é perguntar por que um identificador DESTE projeto
    carrega o nome de outro. Em prosa, mencione à vontade.
    """
    achados = []
    for rel, texto in _arquivos():
        for n, linha in enumerate(texto.splitlines(), 1):
            for pad in SUSPEITO:
                if pad.search(linha):
                    achados.append(f"{rel}:{n}: {linha.strip()[:100]}")
                    break
    assert not achados, (
        "identificador com nome de observatório irmão:\n  "
        + "\n  ".join(achados))


def test_identidade_deste_projeto():
    """
    As cadeias por onde este projeto se apresenta, conferidas por nome.

    Padrão genérico não serve aqui: `UA = "observatorio-psicologia/1.0"` é
    sintaticamente impecável e foi exatamente o defeito real de um irmão. Um
    teste que procura forma não vê isso; um que procura o nome certo, sim.

    São poucas e são fechadas, então estão listadas uma a uma. Cada entrada diz
    onde a cadeia aparece e quem a lê — porque "identidade" aqui não é marca, é
    quem o servidor público registra, o que o navegador instala e o que o cache
    do service worker separa.
    """
    casos = [
        ("etl/rede.py", "UA = ",
         "observatorio-fisioterapia/",
         "User-Agent: é por ele que INEP e DATASUS sabem quem está lendo, e é "
         "ele que a proveniência afirma. Errado, manda o operador do servidor "
         "reclamar com o projeto errado."),
        ("site/build.py", '"short_name"',
         "Fisio",
         "nome curto do PWA: é o rótulo que fica embaixo do ícone na tela "
         "inicial de quem instala o sítio."),
        ("site/build.py", "versao = f\"",
         "fisio-",
         "chave do cache do service worker: compartilhá-la com outro "
         "observatório faria um servir CSS do outro."),
        (".claude/launch.json", '"name"',
         "fisio",
         "nome do servidor de desenvolvimento local."),
    ]
    falhas = []
    for arquivo, ancora, esperado, porque in casos:
        texto = (REPO / arquivo).read_text(encoding="utf-8")
        linhas = [l for l in texto.splitlines() if ancora in l]
        if not linhas:
            falhas.append(f"{arquivo}: não achei linha com {ancora!r} — "
                          f"o teste perdeu a âncora, conserte o teste")
            continue
        if not any(esperado in l for l in linhas):
            falhas.append(f"{arquivo}: nenhuma linha com {ancora!r} contém "
                          f"{esperado!r}. {porque}\n      achei: {linhas[:2]}")
    assert not falhas, "identidade do projeto:\n  " + "\n  ".join(falhas)


def test_nenhum_numero_da_fonoaudiologia_sobreviveu():
    """
    As âncoras herdadas da irmã, nomeadas uma a uma.

    A renomeação mecânica não toca em número, então todo valor medido da
    Fonoaudiologia que ficasse para trás continuaria aqui com aparência de
    medida desta profissão. Estes são os que o repositório de origem publicava.

    POR QUE SÓ O QUE FOI ESCRITO À MÃO
    ----------------------------------
    A primeira versão varria o repositório inteiro, `data/` incluído, e
    acusava dez linhas legítimas: `939` aparece dentro do código IBGE de
    Marabá (`1502939`), de códigos de curso do INEP, de um CR10 de 0,9394 e de
    hashes SHA-256 do registro autoral. Nenhuma é resto da Fonoaudiologia; são
    três dígitos consecutivos, que em 1,5 MB de JSON aparecem por aritmética.

    Afrouxar o padrão por causa disso seria o conserto errado. O certo é notar
    que `data/` é GERADO: nada ali é digitado, e um número da irmã só pode
    chegar lá se estiver cravado no código do pipeline — que este mesmo teste
    varre. Procurar no gerado não acrescenta alcance, só ruído que faria o
    teste ser ignorado, e teste ignorado não protege nada.
    """
    herdados = {
        "939": "registros do Censo (Fonoaudiologia)",
        "17028": "vagas presenciais (Fonoaudiologia)",
        "12876": "vagas EaD (Fonoaudiologia)",
        "4244": "municípios com fonoaudiólogo",
        "24124": "fonoaudiólogos no SUS",
        "2150": "municípios com serviço (Fonoaudiologia)",
        "2266": "municípios com serviço declarado (Fonoaudiologia)",
    }
    # Cada número nas duas formas em que uma pessoa o escreve: na prosa com
    # separador de milhar, no código sem.
    padroes = {}
    for nu, oque in herdados.items():
        pontuado = f"{int(nu):,}".replace(",", ".")
        padroes[re.compile(rf"(?<![\d.]){re.escape(pontuado)}(?![\d.])")] = (
            pontuado, oque)
        padroes[re.compile(rf"(?<![\d.]){nu}(?![\d.])")] = (nu, oque)

    achados = []
    for rel, texto in _arquivos():
        if rel.startswith("tests/") or rel.startswith("data/"):
            continue
        for n, linha in enumerate(texto.splitlines(), 1):
            for pad, (mostra, oque) in padroes.items():
                if pad.search(linha):
                    achados.append(f"{rel}:{n}: {mostra} ({oque}): "
                                   f"{linha.strip()[:80]}")
                    break
    assert not achados, (
        "número medido da Fonoaudiologia sobreviveu à adaptação:\n  "
        + "\n  ".join(achados))


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  OK      {nome}")
            except AssertionError as e:
                falhas += 1
                print(f"  FALHOU  {nome}: {e}")
    total = len([n for n in globals() if n.startswith("test_")])
    print(f"\n{total - falhas}/{total} testes de vazamento passaram.")
    sys.exit(1 if falhas else 0)
