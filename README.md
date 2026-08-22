# Compatibilização de setores censitários — 2000 / 2010 / 2022

Compatibilização das variáveis dos Censos Demográficos de 2000, 2010 e 2022 do IBGE para cinco municípios —
Anápolis (GO), Montes Claros (MG), Passo Fundo (RS), Santarém (PA) e Vitória da Conquista (BA) — fixando os dados
históricos na malha de setores censitários de **2022**.

## Como reproduzir

```powershell
py -3.13 -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\jupyter lab
```

Os dados de entrada (`input/`) não são versionados — coloque os shapefiles e a planilha de dicionário de
variáveis na estrutura `input/<Cidade>/<ano>/...`.

## Notebooks

Executar em ordem (`notebooks/01_...` a `notebooks/06_...`). Cada notebook abre com um cabeçalho markdown
descrevendo objetivo, entradas e saídas.

1. **Diagnóstico dos dados** — inventário dos 20 shapefiles, validação das identidades de fechamento das
   variáveis de domicílio, e geração da planilha `VARIAVEIS_..._CORRIGIDA.xlsx` (fórmulas de percentual
   corrigidas).
2. **Padronização geométrica** — correção do CRS de 2000, união urbano+rural, filtro por município, harmonização
   de tipos de coluna.
3. **Compatibilização areal** — interpolação por ponderação de área das contagens de 2000 e 2010 para a malha de
   2022, com normalização para preservar os totais municipais.
4. **IPCA** — deflacionamento da variável de renda (V24) para reais de julho/2022.
5. **Variáveis derivadas** — cálculo de densidade demográfica e de todos os percentuais, a partir das fórmulas da
   planilha corrigida.
6. **Exportação** — geração dos 5 GeoPackages finais (um por cidade) e do dicionário de colunas de saída.

## Limitações conhecidas

- A interpolação por ponderação de área assume densidade uniforme dentro do setor de origem; o erro é maior em
  setores rurais extensos (caso mais crítico: Santarém).
- V26/V27 mudam de definição entre censos ("particular permanente" em 2000/2010 vs. "particular permanente
  ocupado" em 2022) — tratados como a mesma variável por decisão do projeto.
- Cor/raça (V9–V19) não existe no Censo 2000.
- A ponderação de V24 (renda média) usa V26 como proxy do universo de responsáveis com rendimento, por falta de
  variável mais específica.
- Santarém teve uma redução territorial real em 2012; a série histórica (2000/2010) é compatibilizada apenas
  para o território de 2022 (ver notebook 02, seção 5).
