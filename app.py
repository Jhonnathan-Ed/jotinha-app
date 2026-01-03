import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# 1. Configuração da Página
st.set_page_config(page_title="Jotinha", layout="wide", page_icon="🤠")

# --- CONEXÃO INTELIGENTE (LOCAL + NUVEM) ---
@st.cache_resource
def conectar_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # ESTRATÉGIA 1: Tenta pegar do Cofre Digital (Nuvem)
    if "CREDENTIALS_JSON_CONTENT" in st.secrets:
        # Lê o texto JSON que guardamos no cofre e converte para dicionário
        info_dict = json.loads(st.secrets["CREDENTIALS_JSON_CONTENT"])
        credentials = Credentials.from_service_account_info(info_dict, scopes=scopes)
    
    # ESTRATÉGIA 2: Tenta pegar do arquivo físico (Local no seu PC)
    else:
        try:
            credentials = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        except FileNotFoundError:
            st.error("❌ Erro: Não achei 'credentials.json' (Local) nem o Segredo na Nuvem.")
            st.stop()
            
    client = gspread.authorize(credentials)
    return client

try:
    client = conectar_google_sheets()
    # SEU LINK
    URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1DZQu6vw34jFL6Mj1qYZDLANUKSR66yMa8tM6eoO3x7U/edit"
    
    sh = client.open_by_url(URL_PLANILHA)
    worksheet_colunas = sh.worksheet("Colunas")
    worksheet_cards = sh.worksheet("Cards")
    
except Exception as e:
    st.error(f"Erro na conexão: {e}")
    st.stop()

# --- CARREGAR DADOS ---
dados_colunas = worksheet_colunas.get_all_records()
dados_cards = worksheet_cards.get_all_records()

df_colunas = pd.DataFrame(dados_colunas)
df_cards = pd.DataFrame(dados_cards)

if not df_colunas.empty:
    lista_nomes_colunas = [str(c["Lista"]) for c in dados_colunas if str(c["Lista"]) != ""]
else:
    lista_nomes_colunas = []

# --- BARRA LATERAL ---
with st.sidebar:
    st.title("⚙️ Configurações")
    st.markdown("Gerencie a estrutura do seu Jotinha aqui.")
    st.divider()
    
    st.subheader("Nova Coluna")
    nova_coluna_nome = st.text_input("Nome da coluna", placeholder="Ex: Viagens")
    if st.button("Criar Coluna"):
        if nova_coluna_nome and nova_coluna_nome not in lista_nomes_colunas:
            worksheet_colunas.append_row([nova_coluna_nome])
            st.success(f"Coluna '{nova_coluna_nome}' criada!")
            st.rerun()
        elif nova_coluna_nome in lista_nomes_colunas:
            st.warning("Essa coluna já existe!")
    
    st.divider()
    
    st.subheader("Excluir Coluna")
    if lista_nomes_colunas:
        coluna_para_apagar = st.selectbox("Selecione para apagar", options=lista_nomes_colunas)
        if st.button("🗑️ Apagar Coluna Selecionada", type="primary"):
            cell = worksheet_colunas.find(coluna_para_apagar)
            worksheet_colunas.delete_rows(cell.row)
            st.success(f"Coluna '{coluna_para_apagar}' removida!")
            st.rerun()

# --- ÁREA PRINCIPAL ---
st.title("🤠 Jotinha")

# --- POP-UPS ---
@st.dialog("Novo Card")
def popup_novo_card(coluna_destino):
    st.write(f"Criando em: **{coluna_destino}**")
    titulo = st.text_input("Título")
    conteudo = st.text_area("Detalhes")
    if st.button("Salvar Card 💾"):
        if not titulo:
            st.warning("Título é obrigatório")
        else:
            worksheet_cards.append_row([titulo, conteudo, coluna_destino])
            st.success("Criado!")
            st.rerun()

@st.dialog("Editar Card")
def popup_editar_card(id_linha, titulo_atual, conteudo_atual, coluna_atual, todas_colunas):
    novo_titulo = st.text_input("Título", value=titulo_atual)
    novo_conteudo = st.text_area("Detalhes", value=conteudo_atual)
    index_col = 0
    if coluna_atual in todas_colunas:
        index_col = todas_colunas.index(coluna_atual)
    nova_coluna = st.selectbox("Coluna", options=todas_colunas, index=index_col)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("💾 Salvar", type="primary"):
            linha_real = id_linha + 2
            worksheet_cards.update_cell(linha_real, 1, novo_titulo)
            worksheet_cards.update_cell(linha_real, 2, novo_conteudo)
            worksheet_cards.update_cell(linha_real, 3, nova_coluna)
            st.rerun()
    with col2:
        if st.button("🗑️ Excluir"):
            linha_real = id_linha + 2
            worksheet_cards.delete_rows(linha_real)
            st.rerun()

# --- DESENHO DO QUADRO ---
if not lista_nomes_colunas:
    st.info("👈 Nenhuma coluna encontrada! Use a barra lateral para criar a primeira.")
else:
    cols = st.columns(len(lista_nomes_colunas))
    for i, nome_coluna in enumerate(lista_nomes_colunas):
        with cols[i]:
            st.markdown(f"### {nome_coluna}")
            st.divider()
            if not df_cards.empty and "Coluna" in df_cards.columns:
                cards_da_coluna = df_cards[df_cards["Coluna"] == nome_coluna]
                for index_original, row in cards_da_coluna.iterrows():
                    with st.container(border=True):
                        st.markdown(f"**{row['Titulo']}**")
                        preview_texto = row['Conteudo'][:100] + "..." if len(row['Conteudo']) > 100 else row['Conteudo']
                        st.caption(preview_texto)
                        if st.button("✏️", key=f"edit_{index_original}"):
                            popup_editar_card(index_original, row['Titulo'], row['Conteudo'], row['Coluna'], lista_nomes_colunas)
            if st.button("➕", key=f"add_{nome_coluna}"):
                popup_novo_card(nome_coluna)