import pyodbc
from datetime import datetime
import uuid
import time
import os # Para limpar a consola (opcional)

# --- 1. CONFIGURAÇÃO E VARIÁVEIS GLOBAIS (Parte 1.2) ---

# --- SUBSTITUA ESTES VALORES PELOS DADOS REAIS DO SEU SERVIDOR SQL ---
SERVER_NAME = '192.168.43.119' # <--- IP ou Hostname da Máquina SQL
DATABASE_NAME = 'MEI_TRAB' 
USER_ID = 'sa' 
PASSWORD = 'SUA_PASSWORD_AQUI' # <--- PASSWORD REAL DO SA

# Driver ODBC (Verifique se o nome está correto na sua máquina)
DRIVER = '{ODBC Driver 17 for SQL Server}' 

# String de conexão final
CONN_STR = f'DRIVER={DRIVER};SERVER={SERVER_NAME};DATABASE={DATABASE_NAME};UID={USER_ID};PWD={PASSWORD}'

# Variável de teste para o Nível de Isolamento (Mudar para testes)
NIVEL_ISOLAMENTO_ATUAL = 'READ COMMITTED' 

# ----------------------------------------------------------------------

# --- 2. FUNÇÕES DE CONEXÃO E CONFIGURAÇÃO (Parte 1.3 e 1.4) ---

def conectar_db():
    """ Tenta estabelecer a conexão com o SQL Server. """
    conn = None
    try:
        # autocommit=False é crucial para a gestão manual de transações
        conn = pyodbc.connect(CONN_STR, autocommit=False)
        print("✅ Conexão estabelecida com sucesso! Autocommit desligado.")
        return conn
    except pyodbc.Error as ex:
        # Captura erros de rede/instância
        print("\n❌ ERRO DE CONEXÃO. Verifique o serviço SQL, firewall e CONN_STR.")
        print(ex)
        return None

def definir_isolamento(conn, nivel_isolamento: str):
    """ Define o nível de isolamento para a sessão atual (requisito do trabalho). """
    if conn is None:
        return False
        
    try:
        cursor = conn.cursor()
        isolation_sql = f"SET TRANSACTION ISOLATION LEVEL {nivel_isolamento}"
        cursor.execute(isolation_sql)
        cursor.close()
        print(f"✅ Nível de isolamento definido para: {nivel_isolamento}")
        return True
    except pyodbc.Error as ex:
        print(f"❌ ERRO ao definir nível de isolamento: {ex}")
        return False

# ----------------------------------------------------------------------

# --- 3. FUNÇÃO PRINCIPAL DE EDIÇÃO (Partes 2 e 3) ---

def editar_encomenda(enc_id: int, nova_morada: str, produtos_alterados: list, pausar_para_teste: bool = False):
    """
    Executa o fluxo completo de edição dentro de uma transação.
    :param pausar_para_teste: Se True, a transação para após o UPDATE (simulando dados 'uncommitted').
    """
    conn = None
    cursor = None
    
    # 2.4. Gerar Referência Única (Para o LogOperations)
    user_reference = f"G1-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{uuid.uuid4().hex[:6]}"

    try:
        # 2.1. Iniciar Conexão e Isolamento
        conn = conectar_db()
        if conn is None:
            return

        definir_isolamento(conn, NIVEL_ISOLAMENTO_ATUAL)
        cursor = conn.cursor()
        
        # [cite_start]2.5. LOG INICIAL (EventType='O') - Marca o início da edição [cite: 98-102]
        # O 'Valor' é a hora de início da edição, usado depois pelo Log Tempo
        log_start_sql = "INSERT INTO LogOperations (EventType, Objecto, Valor, Referencia, DCriacao) VALUES ('O', ?, ?, ?, GETDATE())"
        cursor.execute(log_start_sql, enc_id, datetime.now(), user_reference)
        print(f"\n[LOG] Registo inicial 'O' inserido. Referência: {user_reference}")
        
        # ----------------------------------------------------------------------
        # INÍCIO DA TRANSAÇÃO
        # ----------------------------------------------------------------------

        # --- 3.1. Leitura de Dados (SELECT) ---
        print("\n--- INÍCIO DA LEITURA (SELECT) ---")
        
        # Leitura da Tabela Encomenda (cabeçalho)
        select_enc_sql = "SELECT Nome, Morada FROM Encomenda WHERE EncId = ?"
        cursor.execute(select_enc_sql, enc_id)
        encomenda_header = cursor.fetchone()
        
        if not encomenda_header:
            raise pyodbc.Error(f"Encomenda {enc_id} não existe. Abortando.")
            
        print(f"Dados lidos: {encomenda_header.Nome} - {encomenda_header.Morada}")

        # ----------------------------------------------------------------------
        
        # --- 3.2 & 3.3. Atualização de Dados (UPDATE) ---
        print("\n--- INÍCIO DA ATUALIZAÇÃO (UPDATE) ---")

        # 1. Atualizar Encomenda (Morada)
        update_enc_sql = "UPDATE Encomenda SET Morada = ? WHERE EncId = ?"
        cursor.execute(update_enc_sql, nova_morada, enc_id)
        print(f"✅ UPDATE Encomenda (Morada) executado. (Trigger U ativo)")

        # 2. Atualizar EncLinha (Quantidade)
        for produto in produtos_alterados:
            update_linha_sql = "UPDATE EncLinha SET Qtd = ? WHERE EncId = ? AND Produtold = ?"
            cursor.execute(
                update_linha_sql, 
                produto['nova_qtd'], 
                enc_id, 
                produto['produto_id']
            )
            print(f"  > Produto {produto['produto_id']} atualizado para Qtd={produto['nova_qtd']}. (Trigger U ativo)")

        # 3.4. SIMULAÇÃO DE PAUSA PARA TESTES (Ponto crucial para testar locks)
        if pausar_para_teste:
            print("\n*** PAUSA PARA TESTE DE CONCORRÊNCIA ***")
            print("Transação ATIVA com dados não confirmados. Verifique no Browser/SSMS.")
            input("Pressione Enter para executar o COMMIT...")
        
        # 2.10. COMMIT DA TRANSAÇÃO
        conn.commit()
        print("\n✅ COMMIT EXECUTADO. Alterações permanentes.")
        
        # 2.6. [cite_start]LOG FINAL (EventType='O') - Marca o fim da edição [cite: 107-109]
        log_end_sql = "INSERT INTO LogOperations (EventType, Objecto, Valor, Referencia, DCriacao) VALUES ('O', ?, ?, ?, GETDATE())"
        cursor.execute(log_end_sql, enc_id, datetime.now(), user_reference)
        conn.commit() # Commit separado do log final (não faz parte da transação de negócio)

        print("[LOG] Registo final 'O' inserido.")

    except pyodbc.Error as ex:
        # 2.2. Captura de Erros e 2.3. ROLLBACK
        print("\n" + "="*50)
        print(f"❌ FALHA CRÍTICA NA TRANSAÇÃO.")
        print(f"ERRO: {ex}")
        
        if conn:
            conn.rollback() 
            print("ROLLBACK EXECUTADO. Nenhuma alteração de negócio foi guardada.")
        print("="*50)
            
    finally:
        # Fechar recursos
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ----------------------------------------------------------------------
# --- EXEMPLO DE EXECUÇÃO (BLOCO PRINCIPAL) ---
# ----------------------------------------------------------------------

if __name__ == '__main__':
    
    def ui_simples_editar():
        """ Simula a recolha de dados da UI para testes na consola. """
        
        print("\n" + "="*30)
        print(f"APLICAÇÃO EDIT - ISOLAMENTO: {NIVEL_ISOLAMENTO_ATUAL}")
        print("="*30)
        
        try:
            # 1. Entrada de Dados
            enc_id = int(input("Introduza o ID da encomenda a editar: "))
            nova_morada = input("Introduza a nova Morada (ou Enter para manter): ") or "Nova Morada de Teste"
            
            # 2. Simulação de Alteração de Produtos (Ajuste conforme seus dados iniciais)
            print("\nSimulação de alteração de produtos:")
            prod_id_1 = int(input("ID do 1º Produto a alterar (ex: 150): "))
            nova_qtd_1 = int(input("Nova Qtd para esse produto (ex: 5): "))
            
            produtos_a_alterar = [
                {'produto_id': prod_id_1, 'nova_qtd': nova_qtd_1}
            ]
            
            # 3. Simulação de Pausa para Testes de Concorrência
            pausar_input = input("\nPausar a transação após o UPDATE (Y/N)? ").strip().upper()
            pausar = True if pausar_input == 'Y' else False

            # 4. Chamada da Função Principal
            editar_encomenda(enc_id, nova_morada, produtos_a_alterar, pausar)

        except ValueError:
            print("\nERRO: Entrada inválida. IDs e Quantidades devem ser números inteiros.")
        except Exception as e:
            print(f"\nOcorreu um erro inesperado: {e}")

    # Chamar o simulador de UI para iniciar a aplicação
    ui_simples_editar()