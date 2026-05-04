import json
import time
import pandas as pd
import requests
from typing import List, Dict, Optional
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, XSD



BASE_URL = "https://dadosabertos.capes.gov.br"
DATASTORE_SEARCH = f"{BASE_URL}/api/3/action/datastore_search"

# Datasets conhecidos
DATASET_PPG_AVALIADOS = "tabela-cursos-avaliados"
DATASET_PRODUCAO = "tabela-producao-intelectual"

# Intervalo corrigido: 2017 a 2024
ANOS = list(range(2017, 2025))  # [2017, 2018, ..., 2024]


PRODUCAO_RESOURCE_IDS = {
    2017: "902bd63b-137f-4090-89e9-cab94f12c41d",  # Ano 2017
    2018: "638668a6-07da-4c7e-8aab-9044ae3cc753",  # Ano 2018
    2019: "8f4f2bce-2744-460a-8f14-f1648c7a16df",  # Ano 2019
    2020: "e37df31a-f250-4405-8b21-ca7e5c7c1696",  # Ano 2020
    2021: "068003e4-196c-41f4-8c35-1f7c94b4e55c",  # Ano 2021
    2022: "78f73608-6f5e-463c-ba79-0bff4f8a578d",  # Ano 2022
    2023: "b69baf26-8d02-4c10-ba39-7e9ab799e6ed",  # Ano 2023
    2024: "87133ba7-ac99-4d87-966e-8f580bc96231",  # Ano 2024
}

# Filtro geográfico
UF_FILTER = "PE"
LIMIT = 100

# Namespace do vocabulário OML
CTI = Namespace("http://gic.ufrpe.br/cti/vocabulary/cti#")
RDFS = Namespace("http://www.w3.org/2000/01/rdf-schema#")


def discover_resource_ids(dataset_id: str) -> Dict[int, str]:
    """
    Descobre todos os resources CSV ativos de um dataset e tenta inferir o ano a partir do nome.
    Retorna dicionário {ano: resource_id}.
    """
    url = f"{BASE_URL}/api/3/action/package_show?id={dataset_id}"
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Erro ao acessar dataset {dataset_id}: {resp.status_code}")
        return {}
    data = resp.json()
    if not data.get("success"):
        print(f"Falha na API: {data.get('error', {}).get('message')}")
        return {}
    
    resources = data["result"]["resources"]
    mapping = {}
    for r in resources:
        if r.get("format") == "CSV" and r.get("datastore_active"):
            name = r.get("name", "").lower()
            # Tenta extrair ano do nome (ex: "producao-intelectual-2017")
            for ano in ANOS:
                if str(ano) in name:
                    mapping[ano] = r["id"]
                    break
            # Se não encontrou ano, mas é o único recurso, pode ser geral
    return mapping

def fetch_all_records(resource_id: str, filters: Dict = None) -> List[Dict]:
    """Busca todos os registros de um recurso CKAN com paginação."""
    records = []
    offset = 0
    while True:
        params = {
            "resource_id": resource_id,
            "limit": LIMIT,
            "offset": offset
        }
        if filters:
            params["filters"] = json.dumps(filters)
        
        try:
            resp = requests.get(DATASTORE_SEARCH, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                print(f"Erro API: {data.get('error', {}).get('message')}")
                break
            page = data["result"]["records"]
            if not page:
                break
            records.extend(page)
            print(f"    → {len(page)} registros (total: {len(records)})")
            if len(page) < LIMIT:
                break
            offset += LIMIT
            time.sleep(0.5)
        except Exception as e:
            print(f"    Erro na requisição: {e}")
            break
    return records



def get_ppg_conceitos() -> pd.DataFrame:
    """
    Busca os conceitos CAPES dos programas de pós-graduação das ICTs com UF = 'PE'.
    Retorna DataFrame com pelo menos: cd_programa_ies, nm_programa_ies, cd_conceito_programa, an_base_conceito.
    """
    # Primeiro, descobre o resource dos conceitos
    conceitos_resources = discover_resource_ids(DATASET_PPG_AVALIADOS)
    if not conceitos_resources:
        print("⚠️ Não foi possível encontrar resource de conceitos PPG.")
        return pd.DataFrame()
    # Normalmente o dataset tem um único resource com todos os anos
    resource_id = list(conceitos_resources.values())[0]
    print(f"Usando resource de conceitos: {resource_id}")
    
    filters = {"SG_UF_IES": UF_FILTER}
    records = fetch_all_records(resource_id, filters=filters)
    if not records:
        return pd.DataFrame()
    
    df = pd.DataFrame(records)
    # Identifica colunas de ano e conceito
    ano_col = "AN_BASE" if "AN_BASE" in df.columns else "ANO_AVALIACAO"
    if ano_col not in df.columns:
        print("⚠️ Coluna de ano não encontrada. Mantendo todos os registros.")
    else:
        # Filtra pelos anos de interesse (opcional, mas pode incluir avaliações anteriores a 2017)
        df = df[df[ano_col].isin(ANOS)]
    
    # Renomeia colunas
    rename_map = {
        "CD_PROGRAMA_IES": "cd_programa_ies",
        "NM_PROGRAMA_IES": "nm_programa_ies",
        "CD_CONCEITO_PROGRAMA": "cd_conceito_programa",
        ano_col: "an_base_conceito",
        "SG_UF_IES": "sg_uf"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    # Garante que as colunas essenciais existam
    required = ["cd_programa_ies", "nm_programa_ies", "cd_conceito_programa"]
    for col in required:
        if col not in df.columns:
            print(f"⚠️ Coluna essencial '{col}' não encontrada nos conceitos.")
            return pd.DataFrame()
    print(f"✅ Conceitos obtidos: {len(df)} registros")
    return df

def get_producao_cientifica() -> pd.DataFrame:
    """
    Busca produção científica para cada ano entre 2017 e 2024, filtrando UF=PE.
    """
    # Descobre os resources de produção (um por ano, normalmente)
    producao_resources = discover_resource_ids(DATASET_PRODUCAO)
    if not producao_resources:
        print("⚠️ Nenhum resource de produção encontrado. Tentando fallback manual...")
        # Fallback: tenta usar IDs conhecidos (você pode preencher se souber)
        producao_resources = PRODUCAO_RESOURCE_IDS.copy()
        for ano, rid in producao_resources.items():
            if rid is None:
                # Tenta construir nome comum
                possible_name = f"producao-intelectual-{ano}"
                # Não podemos magicamente adivinhar, então pulamos
                pass
    
    all_records = []
    for ano in ANOS:
        resource_id = producao_resources.get(ano)
        if not resource_id:
            print(f"  ⚠️ Resource ID para {ano} não encontrado. Pulando...")
            continue
        print(f"Buscando produções de {ano}...")
        filters = {"SG_UF_IES": UF_FILTER}
        records = fetch_all_records(resource_id, filters=filters)
        for rec in records:
            rec["ano_referencia"] = ano
        all_records.extend(records)
    
    if not all_records:
        return pd.DataFrame()
    
    df = pd.DataFrame(all_records)
    # Renomeia colunas para o padrão esperado
    rename_map = {
        "NM_PROGRAMA": "nm_programa_ies",
        "CD_PROGRAMA_IES": "cd_programa_ies",
        "NM_ENTIDADE_ENSINO": "nm_entidade_ensino",
        "SG_UF_IES": "sg_uf",
        "NM_DISCENTE": "nm_discente",
        "NM_ORIENTADOR": "nm_orientador",
        "NM_PRODUCAO": "nm_titulo",
        "DT_TITULACAO": "dt_titulacao",
        "AN_BASE": "an_base_producao",
        "NM_SUBTIPO_PRODUCAO": "ds_natureza",
        "DS_ABSTRACT": "ds_resumo",
        "DS_DOI": "ds_doi"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    # Adiciona coluna ano_producao (já tem ano_referencia)
    print(f"✅ Produções obtidas: {len(df)} registros para os anos {ANOS[0]}–{ANOS[-1]}")
    return df



def create_rdf_graph(conceitos_df: pd.DataFrame, producao_df: pd.DataFrame) -> Graph:
    g = Graph()
    g.bind("cti", CTI)
    g.bind("rdfs", RDFS)
    
    # Cache
    ppg_uris = {}
    ict_uris = {}
    autor_uris = {}
    
    # 1. Instituições (ICT)
    icts = producao_df["nm_entidade_ensino"].dropna().unique()
    for ict_nome in icts:
        uri = CTI[f"ict/{ict_nome.replace(' ', '_')}"]
        g.add((uri, RDF.type, CTI.ICT))
        g.add((uri, CTI.nm_entidade_ensino, Literal(ict_nome, lang="pt")))
        g.add((uri, CTI.sg_uf, Literal(UF_FILTER)))
        ict_uris[ict_nome] = uri
    
    # 2. PPG e Conceitos
    for _, row in conceitos_df.iterrows():
        prog_id = row["cd_programa_ies"]
        prog_nome = row["nm_programa_ies"]
        conceito = row["cd_conceito_programa"]
        ano = row.get("an_base_conceito", None)
        
        ppg_uri = CTI[f"ppg/{prog_id}"]
        if ppg_uri not in ppg_uris.values():
            g.add((ppg_uri, RDF.type, CTI.PPG))
            g.add((ppg_uri, CTI.cd_programa_ies, Literal(prog_id)))
            g.add((ppg_uri, CTI.nm_programa_ies, Literal(prog_nome, lang="pt")))
            ppg_uris[prog_id] = ppg_uri
        
        # Conceito PPG (cada ano de avaliação pode ter um conceito diferente)
        conceito_uri = CTI[f"conceito/{prog_id}_{ano}"]
        g.add((conceito_uri, RDF.type, CTI.Conceito_PPG))
        if pd.notna(ano):
            g.add((conceito_uri, CTI.an_base_conceito, Literal(int(ano), datatype=XSD.integer)))
        g.add((conceito_uri, CTI.cd_conceito_programa, Literal(str(conceito))))
        g.add((ppg_uri, CTI.avaliado, conceito_uri))
    
    # 3. Vincular PPG às ICTs (sediado) com base na produção
    prog_to_ict = producao_df.dropna(subset=["nm_programa_ies", "nm_entidade_ensino"]) \
                              .groupby("nm_programa_ies")["nm_entidade_ensino"].first().to_dict()
    for prog_nome, ict_nome in prog_to_ict.items():
        # Encontrar o prog_id a partir do nome
        prog_row = conceitos_df[conceitos_df["nm_programa_ies"] == prog_nome]
        if prog_row.empty:
            continue
        prog_id = prog_row.iloc[0]["cd_programa_ies"]
        ppg_uri = ppg_uris.get(prog_id)
        if ppg_uri and ict_nome in ict_uris:
            g.add((ppg_uri, CTI.sediado, ict_uris[ict_nome]))
    
    # 4. Produção científica, autores e relações
    for _, row in producao_df.iterrows():
        prog_nome = row.get("nm_programa_ies")
        if pd.isna(prog_nome):
            continue
        prog_row = conceitos_df[conceitos_df["nm_programa_ies"] == prog_nome]
        if prog_row.empty:
            continue
        prog_id = prog_row.iloc[0]["cd_programa_ies"]
        ppg_uri = ppg_uris.get(prog_id)
        if not ppg_uri:
            continue
        
        # URI da produção
        prod_id = row.get("_id", f"prod_{row.name}")
        prod_uri = CTI[f"producao/{prod_id}"]
        g.add((prod_uri, RDF.type, CTI.Producao_Cientifica))
        if pd.notna(row.get("nm_titulo")):
            g.add((prod_uri, CTI.nm_titulo, Literal(row["nm_titulo"], lang="pt")))
        if pd.notna(row.get("an_base_producao")):
            g.add((prod_uri, CTI.an_base_producao, Literal(int(row["an_base_producao"]), datatype=XSD.integer)))
        elif "ano_referencia" in row and pd.notna(row["ano_referencia"]):
            g.add((prod_uri, CTI.an_base_producao, Literal(int(row["ano_referencia"]), datatype=XSD.integer)))
        if pd.notna(row.get("ds_natureza")):
            g.add((prod_uri, CTI.ds_natureza, Literal(row["ds_natureza"])))
        if pd.notna(row.get("ds_doi")):
            g.add((prod_uri, CTI.ds_doi, Literal(row["ds_doi"])))
        
        # Autor (discente)
        autor_nome = row.get("nm_discente")
        if pd.notna(autor_nome):
            autor_uri = CTI[f"autor/{autor_nome.replace(' ', '_')}"]
            if autor_uri not in autor_uris.values():
                g.add((autor_uri, RDF.type, CTI.Discente))
                g.add((autor_uri, CTI.nm_pessoa, Literal(autor_nome, lang="pt")))
                g.add((autor_uri, CTI.vinculado, ppg_uri))
                autor_uris[autor_nome] = autor_uri
            g.add((autor_uri, CTI.autoria, prod_uri))
        
        # Orientador (docente)
        orientador_nome = row.get("nm_orientador")
        if pd.notna(orientador_nome) and orientador_nome != autor_nome:
            orientador_uri = CTI[f"docente/{orientador_nome.replace(' ', '_')}"]
            g.add((orientador_uri, RDF.type, CTI.Docente))
            g.add((orientador_uri, CTI.nm_pessoa, Literal(orientador_nome, lang="pt")))
            g.add((orientador_uri, CTI.membro, ppg_uri))
            if autor_uri:
                g.add((autor_uri, CTI.orientador, orientador_uri))
    
    return g


if __name__ == "__main__":
    print("=== Integração CAPES → OML (2017-2024) ===\n")
    
    # 1. Buscar conceitos PPG
    print("🔍 Buscando conceitos CAPES dos PPGs em Pernambuco...")
    df_conceitos = get_ppg_conceitos()
    
    # 2. Buscar produção científica 2017-2024
    print("\n🔍 Buscando produção científica (teses/dissertações) 2017-2024 em PE...")
    df_producao = get_producao_cientifica()
    
    if df_conceitos.empty or df_producao.empty:
        print("❌ Dados insuficientes. Verifique a conexão com a API e os resource IDs.")
        print("   Tente executar o script novamente. Se persistir, pode ser necessário ajustar os nomes dos datasets.")
        exit()
    
    # 3. Construir grafo RDF
    print("\n🧠 Construindo grafo RDF/Turtle conforme vocabulário OML...")
    rdf_graph = create_rdf_graph(df_conceitos, df_producao)
    
    # 4. Salvar arquivo RDF
    output_rdf = "capes_pe_2017_2024.ttl"
    rdf_graph.serialize(destination=output_rdf, format="turtle")
    print(f"\n✅ Arquivo RDF gerado: {output_rdf}")
    
    # 5. Gerar CSV para análise de correlação (conceito x quantidade de produção)
    # Agrupa produção por programa e ano
    producao_agg = df_producao.groupby(["nm_programa_ies", "ano_referencia"]).size().reset_index(name="qtde_producoes")
    analise = df_conceitos.merge(producao_agg, left_on="nm_programa_ies", right_on="nm_programa_ies", how="left")
    analise.to_csv("analise_ppg_producao_2017_2024.csv", index=False, encoding="utf-8-sig")
    print("📁 CSV de análise salvo: analise_ppg_producao_2017_2024.csv")
    
    print("\n✨ Pronto! Agora você pode carregar 'capes_pe_2017_2024.ttl' no openCAESAR e executar consultas SPARQL.")
    print("Exemplo de consulta para responder à sua pergunta de pesquisa:\n")
    print("""
    PREFIX cti: <http://gic.ufrpe.br/cti/vocabulary/cti#>
    SELECT ?ppgNome ?conceito (COUNT(DISTINCT ?producao) AS ?quantidade) WHERE {
      ?ppg a cti:PPG ;
           cti:nm_programa_ies ?ppgNome ;
           cti:avaliado ?conceitoInst .
      ?conceitoInst cti:cd_conceito_programa ?conceito .
      ?autor cti:vinculado ?ppg ;
             cti:autoria ?producao .
      ?producao cti:an_base_producao ?ano .
      FILTER(?ano >= 2017 && ?ano <= 2024)
    }
    GROUP BY ?ppgNome ?conceito
    ORDER BY ?conceito
    """)