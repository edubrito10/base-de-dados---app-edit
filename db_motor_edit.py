import pyodbc
from datetime import datetime
import uuid
import time
from tkinter import messagebox

class DbConnectionEdit:
    """
    Motor da Base de Dados para a Aplicação Edit.
    Gere a conexão e todas as transações de escrita.
    """
    def __init__(self):
        self.conn = None
        self.DRIVER = '{ODBC Driver 17 for SQL Server}' 
        self.DATABASE_NAME = 'SGBD_PL1_02' 
        self.NIVEL_ISOLAMENTO_ATUAL = 'READ COMMITTED'
        self.SERVER_NAME = '' # Será definido no connect

    def connect(self, server, database, username, password):
        """
        Tenta estabelecer e guardar a conexão principal.
        """
        self.SERVER_NAME = server
        self.DATABASE_NAME = database
        
        conn_str = (
            f"DRIVER={self.DRIVER};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;" 
        )
        
        try:
            # autocommit=False é crucial
            self.conn = pyodbc.connect(conn_str, autocommit=False)
            print("✅ Conexão (DbConnectionEdit) estabelecida com sucesso!")
            return self.conn
        except pyodbc.Error as ex:
            print(f"❌ ERRO DE CONEXÃO (DbConnectionEdit): {ex}")
            self.conn = None
            return None

    def set_isolation(self, isolation_level: str):
        """ Define o nível de isolamento para a conexão guardada. """
        if not self.conn:
            print("Erro: Sem conexão para definir isolamento.")
            return False
            
        try:
            with self.conn.cursor() as cursor:
                isolation_sql = f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                cursor.execute(isolation_sql)
            self.NIVEL_ISOLAMENTO_ATUAL = isolation_level
            print(f"✅ Nível de isolamento (DbConnectionEdit) definido para: {isolation_level}")
            return True
        except pyodbc.Error as ex:
            print(f"❌ ERRO ao definir nível de isolamento: {ex}")
            return False

    def fetch_encomenda_data(self, enc_id: int):
        """ 
        Função de LEITURA (SELECT) - Passo 4. 
        """
        if not self.conn:
             raise Exception("Sem conexão.")
             
        try:
            with self.conn.cursor() as cursor:
                # 1. Ler Cabeçalho
                select_enc_sql = "SELECT Nome, Morada FROM Encomenda WHERE EncId = ?"
                cursor.execute(select_enc_sql, enc_id)
                header = cursor.fetchone()
                
                if not header:
                    raise Exception(f"Encomenda {enc_id} não encontrada.")
                
                # 2. Ler Linhas
                select_linhas_sql = "SELECT Produtold, Designacao, Preco, Qtd FROM EncLinha WHERE EncId = ? ORDER BY Produtold"
                cursor.execute(select_linhas_sql, enc_id)
                linhas = cursor.fetchall()
                
                return header, linhas
                
        except pyodbc.Error as ex:
            print(f"ERRO no fetch_encomenda_data: {ex}")
            raise # Lança o erro para a UI
            

    def editar_encomenda(self, enc_id: int, nova_morada: str, produtos_alterados: list, pausar_para_teste: bool = False):
        """
        Executa o fluxo completo de edição.
        """
        if not self.conn:
            messagebox.showerror("Erro de Transação", "A conexão com a BD foi perdida.")
            return

        # 2.4. Gerar Referência Única
        user_reference = f"G1-{datetime.now().strftime('%Y%m%d%H%M%S%f')}-{uuid.uuid4().hex[:6]}"
        cursor = None 

        try:
            cursor = self.conn.cursor()
            
            # 2.5. LOG INICIAL
            log_start_sql = "INSERT INTO LogOperations (EventType, Objecto, Valor, Referencia, DCriacao) VALUES ('O', ?, ?, ?, GETDATE())"
            cursor.execute(log_start_sql, enc_id, datetime.now(), user_reference)
            print(f"\n[LOG] Registo inicial 'O' inserido. Referência: {user_reference}")
            
            # --- INÍCIO DA TRANSAÇÃO (implícito) ---

            # --- 3.2 & 3.3. ATUALIZAÇÃO (UPDATE) ---
            print("\n--- INÍCIO DA ATUALIZAÇÃO (UPDATE) ---")

            # 1. Atualizar Encomenda (Morada)
            update_enc_sql = "UPDATE Encomenda SET Morada = ? WHERE EncId = ?"
            cursor.execute(update_enc_sql, nova_morada, enc_id)
            print(f"✅ UPDATE Encomenda (Morada) executado.")

            # 2. Atualizar EncLinha (Quantidade)
            for produto in produtos_alterados:
                update_linha_sql = "UPDATE EncLinha SET Qtd = ? WHERE EncId = ? AND Produtold = ?"
                cursor.execute(update_linha_sql, produto['nova_qtd'], enc_id, produto['produto_id'])
                print(f"  > Produto {produto['produto_id']} atualizado para Qtd={produto['nova_qtd']}.")

            # 3.4. PAUSA PARA TESTES
            if pausar_para_teste:
                print("\n*** PAUSA PARA TESTE DE CONCORRÊNCIA ***")
                messagebox.showinfo("Transação em Pausa", 
                                    "A transação está ATIVA com dados não confirmados (UPDATEs executados).\n"
                                    "Verifique no Browser/SSMS (deve estar bloqueado).\n\n"
                                    "Clique OK para executar o COMMIT.")
            
            # 2.10. COMMIT DA TRANSAÇÃO
            self.conn.commit()
            print("\n✅ COMMIT EXECUTADO. Alterações permanentes.")
            
            # 2.6. LOG FINAL
            log_end_sql = "INSERT INTO LogOperations (EventType, Objecto, Valor, Referencia, DCriacao) VALUES ('O', ?, ?, ?, GETDATE())"
            cursor.execute(log_end_sql, enc_id, datetime.now(), user_reference)
            self.conn.commit() # Commit separado do log final
            print("[LOG] Registo final 'O' inserido.")
            
            messagebox.showinfo("Sucesso", f"Encomenda {enc_id} atualizada com sucesso.")

        except pyodbc.Error as ex:
            print(f"❌ FALHA CRÍTICA NA TRANSAÇÃO: {ex}")
            if self.conn:
                self.conn.rollback() 
                print("ROLLBACK EXECUTADO.")
                messagebox.showerror("Falha na Transação", f"Ocorreu um erro e a transação foi revertida (ROLLBACK).\n\n{ex}")
                
        finally:
            # NÃO fechamos a conexão, mas fechamos o cursor
            if cursor:
                cursor.close()