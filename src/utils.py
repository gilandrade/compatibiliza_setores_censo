"""Constantes e funções compartilhadas pelo pipeline de compatibilização de setores censitários."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

# ============================================================
# Caminhos
# ============================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = REPO_ROOT / "input"
OUTPUT_DIR = REPO_ROOT / "output"

# ============================================================
# Cidades e códigos municipais (IBGE, 7 dígitos)
# ============================================================

CIDADES = {
    "Anápolis": {"prefixo": "AN", "cod_municipio": "5201108", "uf": "GO", "slug": "anapolis"},
    "Montes Claros": {"prefixo": "MC", "cod_municipio": "3143302", "uf": "MG", "slug": "montes_claros"},
    "Passo Fundo": {"prefixo": "PF", "cod_municipio": "4314100", "uf": "RS", "slug": "passo_fundo"},
    "Santarém": {"prefixo": "SA", "cod_municipio": "1506807", "uf": "PA", "slug": "santarem"},
    "Vitória da Conquista": {"prefixo": "VC", "cod_municipio": "2933307", "uf": "BA", "slug": "vitoria_da_conquista"},
}

ANOS = [2000, 2010, 2022]

# ============================================================
# CRS
# ============================================================

CRS_WGS84 = 4674  # SIRGAS 2000 geográfico — CRS de 2010 e 2022, e da entrega final

# .prj de 2000-urbano declara zona UTM Norte (WGS84), mas as coordenadas são do
# hemisfério Sul (northing ~6-9 milhões). Correção = reatribuir o
# CRS para a zona Sul equivalente, SEM reprojetar coordenadas.
CRS_2000_URBANO = {
    "Anápolis": "EPSG:32722",
    "Passo Fundo": "EPSG:32722",
    "Montes Claros": "EPSG:32723",
    "Santarém": "EPSG:32721",
    "Vitória da Conquista": "EPSG:32724",
}

# CRS métrico de trabalho (SIRGAS 2000 / UTM, zona sul) para cálculo de área e overlay
CRS_METRICO = {
    "Anápolis": "EPSG:31982",
    "Passo Fundo": "EPSG:31982",
    "Montes Claros": "EPSG:31983",
    "Santarém": "EPSG:31981",
    "Vitória da Conquista": "EPSG:31984",
}

# Datums candidatos para testar a hipótese do CRS de 2000 (achado do notebook 02)
CANDIDATOS_DATUM_2000 = {
    "WGS84": "EPSG:4326",
    "SIRGAS2000": "EPSG:4674",
    "SAD69": "EPSG:4618",
}

# ============================================================
# Variáveis
# ============================================================

# Variáveis de contagem (extensivas) presentes nos 20 shapefiles de origem.
# Os nomes de coluna dos shapefiles já coincidem com a numeração do dicionário de variáveis
# — não há rename a fazer (ver notebook 01, seção 4).
VARS_POPULACAO = ["V1", "V3", "V5", "V7", "V9", "V11", "V13", "V15", "V17", "V19", "V21", "V22"]
VARS_DOMICILIO = [
    "V25", "V26", "V27",
    "V28", "V30", "V32", "V34", "V36", "V38", "V40", "V42", "V44", "V46", "V48", "V50", "V52", "V54",
]
VARS_EXTENSIVAS = VARS_POPULACAO + VARS_DOMICILIO

# V24 é intensiva (média), ponderada por V26 (universo de responsáveis com rendimento) — decisão do projeto.
VAR_RENDA = "V24"
VAR_RENDA_MEDIANA = "V24A"  # só existe em 2022, não é interpolada
PESO_RENDA = "V26"

# Variáveis que não existem em 2000 (devem ficar nulas, nunca zero)
VARS_AUSENTES_2000 = ["V9", "V11", "V13", "V15", "V17", "V19", "V32", "V34"]

# Colunas-chave de identificação por ano/fonte
CHAVE_POR_FONTE = {
    "2000_rural": "GEOCODIGO",
    "2000_urbano": "ID_",
    2010: "CD_GEOCODI",
    2022: "CD_SETOR",
}

ENCODING_POR_ANO = {2000: "utf-8", 2010: "latin1", 2022: "utf-8"}


def caminho_shapefile(cidade: str, ano: int, tipo: str | None = None) -> Path:
    """Retorna o caminho de um shapefile de origem.

    Args:
        cidade: Nome da cidade, chave de CIDADES.
        ano: 2000, 2010 ou 2022.
        tipo: Para 2000, "urbano" ou "rural". Ignorado para outros anos.

    Returns:
        Caminho absoluto do .shp.

    Raises:
        ValueError: Se ano=2000 e tipo não for informado.
    """
    prefixo = CIDADES[cidade]["prefixo"]
    pasta = INPUT_DIR / cidade / str(ano)
    if ano == 2000:
        if tipo not in ("urbano", "rural"):
            raise ValueError("Para ano=2000, informe tipo='urbano' ou 'rural'.")
        return pasta / f"{prefixo}_variaveis censo {tipo}_2000.shp"
    return pasta / f"{prefixo}_variaveis censo_{ano}.shp"


def normaliza_texto(s: str) -> str:
    """Remove acentos e caixa para comparações robustas de string (ex.: nomes de cidade)."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.strip().upper()


# ============================================================
# Fórmulas das variáveis derivadas (lidas da planilha corrigida, ver notebook 01/05)
# ============================================================

_FORMULA_RE = re.compile(
    r"^\s*(?:\(?\s*(?P<termo1>V\d+A?)\s*(?:\+\s*(?P<termo2>V\d+A?)\s*)?\)?\s*)"
    r"[Xx*]\s*100\s*/\s*(?P<denominador>V\d+A?)\s*$"
)


def parse_formula_percentual(formula: str) -> dict:
    """Interpreta uma fórmula do tipo 'V3 X 100 / V1' ou '(V11 + V15) X 100 / V1'.

    Args:
        formula: Texto da célula da coluna "FÓRMULA / DENOMINADOR (corrigida)".

    Returns:
        Dict com "numerador" (lista de 1 ou 2 variáveis a somar) e "denominador".

    Raises:
        ValueError: Se a fórmula não casar com o padrão esperado.
    """
    m = _FORMULA_RE.match(formula.replace(" ", " "))
    if not m:
        raise ValueError(f"Fórmula fora do padrão esperado: {formula!r}")
    numerador = [m.group("termo1")]
    if m.group("termo2"):
        numerador.append(m.group("termo2"))
    return {"numerador": numerador, "denominador": m.group("denominador")}


def calcula_percentual(df: pd.DataFrame, numerador: list[str], denominador: str) -> pd.Series:
    """Calcula `100 * soma(numerador) / denominador`, com nulo quando o denominador é nulo ou zero.

    Nunca retorna zero por divisão por denominador ausente — retorna NaN, para distinguir
    "setor sem essa característica" de "dado indisponível".
    """
    denom = df[denominador]
    num = df[numerador].sum(axis=1, min_count=1)
    resultado = (num * 100 / denom).where((denom.notna()) & (denom != 0))
    return resultado
