import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# 1. Configuração da Página
st.set_page_config(page_title="Jotinha", layout="wide", page_icon="🤠")

# --- CSS AGRESSIVO PARA ROLAGEM ---
st.markdown("""
<style>
    /* 1. O container horizontal principal (onde estão as colunas do Kanban) */
    div[data-testid="stHorizontalBlock"] {
        overflow-x: auto !important; /* Habilita rolagem lateral */
        flex-wrap: nowrap !important; /* PROÍBE quebrar para linha de baixo */
        padding-bottom: 15px; /* Espaço para a barra de rolagem aparecer */
    }

    /* 2. As colunas PRINCIPAIS (Kanban) */
    div[data-testid="column"] {
        flex: 0 0 350px !important; /* NÃO ENCOLHER! Manter 350px fixo */
        min-width: 350px !important;
        width: 350px !important;
        margin-right: 15px; /* Espaço entre colunas */
    }

    /* 3. A VACINA (EXCEÇÃO): */
    /* Se a coluna estiver dentro de um card (stVerticalBlockBorderWrapper), 
       ela DEVE voltar ao normal (automático) para não estragar os ícones */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="column"] {
        flex: 1 1 auto !important; /* Volta a ser flexível */
        min-width: 1px !important; /* Pode ficar pequena se precisar */
        width: auto !important;
        margin-right: 0px !important;
    }
    
    /* 4. Previne que a barra de rolagem apareça DENTRO dos cards */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stHorizontalBlock"] {
        overflow-x: visible !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SISTEMA DE LOGIN ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False

if not st.session_state["logado"]:
    st.title("🔒 Acesso Restrito")
    col1, col2 = st.columns([2, 1])
    with col1:
        senha_digitada = st.text_input("Digite a senha:", type="password")
    if st.button("Entrar"):
        senha_correta = st.secrets.get("SENHA_ACESSO", "Jotinha@2000")
        if senha_digitada == senha_correta:
            st.session_state["logado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()

# --- CONEXÃO ---
@st.cache_resource
def conectar_google_sheets():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if "CREDENTIALS_JSON_CONTENT" in st.secrets:
        info_dict = json.loads(st.secrets["CREDENTIALS_JSON_CONTENT"])
        credentials = Credentials.from_service_account_info(info_dict, scopes=scopes)
    else:
        try:
            credentials = Credentials.from_service_account_file("credentials.json", scopes=scopes)
        except FileNotFoundError:
            st.error("❌ Erro de conexão.")
            st.stop()
    client = gspread.authorize(credentials)
    return client

try:
    client = conectar_google_sheets()
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
    if st.button("🔒 Sair"):
        st.session_state["logado"] = False
        st.rerun()
    st.divider()
    
    with st.expander("Nova Coluna", expanded=False):
        nova_coluna_nome = st.text_input("Nome:", placeholder="Ex: Viagens")
        if st.button("Criar"):
            if nova_coluna_nome and nova_coluna_nome not in lista_nomes_colunas:
                worksheet_colunas.append_row([nova_coluna_nome])
                st.success("Criada!")
                st.rerun()
            elif nova_coluna_nome in lista_nomes_colunas:
                st.warning("Já existe!")

    with st.expander("Reordenar Colunas", expanded=False):
        if lista_nomes_colunas:
            coluna_mover = st.selectbox("Mover:", options=lista_nomes_colunas)
            posicoes = list(range(1, len(lista_nomes_colunas) + 1))
            index_atual = lista_nomes_colunas.index(coluna_mover)
            nova_posicao = st.selectbox("Para a posição:", options=posicoes, index=index_atual)
            
            if st.button("Trocar Ordem"):
                nova_lista = lista_nomes_colunas.copy()
                nova_lista.pop(index_atual) 
                nova_lista.insert(nova_posicao - 1, coluna_mover) 
                
                worksheet_colunas.clear()
                worksheet_colunas.append_row(["Lista"])
                for nome in nova_lista:
                    worksheet_colunas.append_row([nome])
                st.success("Ordem atualizada!")
                st.rerun()

    with st.expander("Excluir Coluna", expanded=False):
        if lista_nomes_colunas:
            coluna_para_apagar = st.selectbox("Apagar:", options=lista_nomes_colunas, index=None, placeholder="Selecione...")
            if coluna_para_apagar:
                if st.button("🗑️ Confirmar Exclusão", type="primary"):
                    cell = worksheet_colunas.find(coluna_para_apagar)
                    worksheet_colunas.delete_rows(cell.row)
                    st.success("Removida!")
                    st.rerun()

# --- ÁREA PRINCIPAL ---
st.title("JOTINHA")

# --- POP-UPS (DIALOGS) ---
@st.dialog("Novo Card")
def popup_novo_card(coluna_destino):
    st.write(f"Em: **{coluna_destino}**")
    titulo = st.text_input("Título")
    conteudo = st.text_area("Detalhes", height=150)
    
    with st.expander("ℹ️ Formatação"):
        st.markdown("- **Negrito**: `**texto**`\n- Lista: `- item`\n- Check: `- [ ]`")

    if st.button("Salvar 💾"):
        if not titulo:
            st.warning("Título é obrigatório")
        else:
            worksheet_cards.append_row([titulo, conteudo, coluna_destino])
            st.rerun()

@st.dialog("Confirmar Exclusão")
def popup_confirmacao_exclusao(id_linha, titulo_card):
    st.write(f"Excluir **'{titulo_card}'**?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sim, Excluir", type="primary", use_container_width=True):
            linha_real = id_linha + 2
            worksheet_cards.delete_rows(linha_real)
            st.rerun()
    with col2:
        if st.button("Cancelar", use_container_width=True):
            st.rerun()

@st.dialog("Detalhes")
def popup_editar_card(id_linha, titulo_atual, conteudo_atual, coluna_atual, todas_colunas):
    novo_titulo = st.text_input("Título", value=titulo_atual)
    novo_conteudo = st.text_area("Conteúdo", value=conteudo_atual, height=300)

    with st.expander("ℹ️ Formatação"):
        st.markdown("- **Negrito**: `**texto**`\n- Lista: `- item`\n- Check: `- [ ]`")
    
    index_col = 0
    if coluna_atual in todas_colunas:
        index_col = todas_colunas.index(coluna_atual)
    nova_coluna = st.selectbox("Mover para", options=todas_colunas, index=index_col)
    
    st.markdown("---")
    
    if st.button("💾 Salvar Alterações", use_container_width=True):
        linha_real = id_linha + 2
        worksheet_cards.update_cell(linha_real, 1, novo_titulo)
        worksheet_cards.update_cell(linha_real, 2, novo_conteudo)
        worksheet_cards.update_cell(linha_real, 3, nova_coluna)
        st.success("Salvo!")
        st.rerun()

# --- DESENHO DO QUADRO ---
if not lista_nomes_colunas:
    st.info("👈 Crie sua primeira coluna na barra lateral.")
else:
    # AQUI ESTÁ A MÁGICA: st.columns cria o stHorizontalBlock que configuramos no CSS
    cols = st.columns(len(lista_nomes_colunas))

    for i, nome_coluna in enumerate(lista_nomes_colunas):
        with cols[i]:
            st.markdown(f"### {nome_coluna}")
            st.divider()
            
            if st.button(f"➕ Adicionar", key=f"add_{nome_coluna}", use_container_width=True):
                popup_novo_card(nome_coluna)
            
            if not df_cards.empty and "Coluna" in df_cards.columns:
                cards_da_coluna = df_cards[df_cards["Coluna"] == nome_coluna]
                
                for index_original, row in cards_da_coluna.iterrows():
                    with st.container(border=True):
                        
                        if st.button(f"**{row['Titulo']}**", key=f"open_{index_original}", use_container_width=True, type="tertiary"):
                            popup_editar_card(
                                index_original, 
                                row['Titulo'], 
                                row['Conteudo'], 
                                row['Coluna'],
                                lista_nomes_colunas
                            )
                        
                        conteudo_completo = str(row['Conteudo'])
                        linhas = conteudo_completo.split('\n')
                        if len(linhas) > 6:
                            preview_texto = "\n".join(linhas[:6]) + "\n\n*(...)*"
                        elif len(conteudo_completo) > 300:
                            preview_texto = conteudo_completo[:300] + "..."
                        else:
                            preview_texto = conteudo_completo
                        
                        st.markdown(preview_texto)
                        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

                        # AQUI: Coluna pequena dentro do card. O CSS (Regra 3) vai proteger isso.
                        c_lixo, _ = st.columns([1, 4])
                        with c_lixo:
                            if st.button("🗑️", key=f"del_{index_original}"):
                                popup_confirmacao_exclusao(index_original, row['Titulo'])