import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import sys

# motor de BD
try:
    from db_motor_edit import DbConnectionEdit
except ImportError:
    print("AVISO: Ficheiro 'db_motor_edit.py' não encontrado. A usar MOCK.")
    class MockDbConnectionEdit:
        DRIVER = '{ODBC Driver 18 for SQL Server}'
        DATABASE_NAME = 'SGBD_PL1_02'
        NIVEL_ISOLAMENTO_ATUAL = 'READ COMMITTED'
        SERVER_NAME = 'MOCK_SERVER'
        
        def connect(self, server, database, username, password):
            messagebox.showinfo("MOCK", f"A simular conexão a {server}...")
            return True # Simula sucesso

        def set_isolation(self, isolation_level: str):
            self.NIVEL_ISOLAMENTO_ATUAL = isolation_level
            print(f"MOCK: Nível de isolamento definido para: {isolation_level}")
            return True

        def fetch_encomenda_data(self, enc_id: int):
            messagebox.showinfo("MOCK", f"A simular leitura (SELECT) da Encomenda {enc_id}.")
            # Simula dados de retorno (Nome, Morada)
            header = type('obj', (object,), {'Morada' : 'Rua de Teste (MOCK)'})
            # Simula linhas de retorno
            linhas = [
                type('obj', (object,), {'Produtold': 1, 'Designacao': 'Produto MOCK', 'Preco': 10.0, 'Qtd': 5}),
                type('obj', (object,), {'Produtold': 2, 'Designacao': 'Produto MOCK 2', 'Preco': 20.0, 'Qtd': 2})
            ]
            return header, linhas

        def editar_encomenda(self, enc_id: int, nova_morada: str, produtos_alterados: list, pausar_para_teste: bool = False):
            if pausar_para_teste:
                messagebox.showinfo("MOCK (PAUSA)", 
                                    "A transação MOCK está em pausa.\nClique OK para simular o COMMIT.")
            messagebox.showinfo("MOCK (Sucesso)", f"Encomenda {enc_id} atualizada (simulado).")

    DbConnectionEdit = MockDbConnectionEdit # Substitui a classe real pela MOCK


#JANELA DE LOGIN

class LoginDialog(tk.Toplevel):
    def __init__(self, master):
        super().__init__(master)
        self.transient(master)
        self.title("Conectar ao SQL Server")
        self.result = None 
        self.protocol("WM_DELETE_WINDOW", self.on_cancel) 

        # Centralizar
        width, height = 400, 200
        self.geometry(f"{width}x{height}")
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry('+%d+%d' % (x, y))


        self.server_var = tk.StringVar(value="192.168.100.14,1433") 
        self.db_var = tk.StringVar(value="SGBD_PL1_02")
        self.user_var = tk.StringVar(value="User_SGBD_PL1_02")
        self.password_var = tk.StringVar(value="diubi:2025!SGBD!PL1_02")


        self._criar_widgets()
        
        # --- CORREÇÃO DE FOCO ---
        self.grab_set() # Torna a janela modal
        self.lift() # Coloca no topo da stack de janelas da app
        self.focus_force() # Força o foco do teclado
        self.attributes('-topmost', True) # FORÇA a janela a ficar no topo do Windows/OS
        # ------------------------

    def _criar_widgets(self):
        frame = tk.Frame(self, padx=20, pady=10)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        form_layout = tk.Frame(frame)
        form_layout.pack(pady=5)

        tk.Label(form_layout, text="Servidor (IP/Nome):").grid(row=0, column=0, sticky="w", pady=5, padx=5)
        tk.Entry(form_layout, textvariable=self.server_var, width=30).grid(row=0, column=1, padx=5)

        tk.Label(form_layout, text="Base de dados:").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        tk.Entry(form_layout, textvariable=self.db_var, width=30).grid(row=1, column=1, padx=5)

        tk.Label(form_layout, text="Utilizador:").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        tk.Entry(form_layout, textvariable=self.user_var, width=30).grid(row=2, column=1, padx=5)

        tk.Label(form_layout, text="Password:").grid(row=3, column=0, sticky="w", pady=5, padx=5)
        tk.Entry(form_layout, textvariable=self.password_var, show="*", width=30).grid(row=3, column=1, padx=5)

        # Botões
        buttons_frame = tk.Frame(frame)
        buttons_frame.pack(pady=10)

        tk.Button(buttons_frame, text="Conectar", command=self.on_ok, bg="#0078d7", fg="white", width=10, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
        tk.Button(buttons_frame, text="Cancelar", command=self.on_cancel, bg="#d9534f", fg="white", width=10, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)

    def on_ok(self):
        # Guardar os valores num dicionário
        self.result = {
            "server": self.server_var.get(),
            "database": self.db_var.get(),
            "user": self.user_var.get(),
            "password": self.password_var.get()
        }
        self.attributes('-topmost', False) # Desativa o "sempre no topo"
        self.destroy() 

    def on_cancel(self):
        self.result = None 
        self.destroy()


# APLICAÇÃO PRINCIPAL
class AppEdit(tk.Tk):
    def __init__(self, db_connection):
        super().__init__()
        self.title("MEI - Aplicação Edit | Controlo de Transações")
        self.geometry("900x650")
        
        # Variáveis de Estado
        self.db = db_connection # USA A CONEXÃO GUARDADA
        self.isolation_var = tk.StringVar(value=self.db.NIVEL_ISOLAMENTO_ATUAL)
        self.is_connected = True 
        
        # Variáveis de Edição
        self.enc_id_var = tk.StringVar()
        self.morada_var = tk.StringVar()
        self.produtos_alterados = [] 
        
        self._criar_frame_configuracao()
        self._criar_frame_edicao()
        self._criar_frame_produtos()
        
    # --- Secção 1: Configuração e Conexão ---
    def _criar_frame_configuracao(self):
        frame = tk.LabelFrame(self, text="1. Nível de Isolamento", padx=10, pady=10)
        frame.pack(padx=10, pady=10, fill="x")

        tk.Label(frame, text="Nível de Isolamento:").pack(side="left", padx=5)
        opcoes_isolamento = [
            "READ UNCOMMITTED", "READ COMMITTED", 
            "REPEATABLE READ", "SERIALIZABLE", "SNAPSHOT"
        ]
        isolamento_menu = tk.OptionMenu(frame, self.isolation_var, *opcoes_isolamento)
        isolamento_menu.pack(side="left", padx=10)
        
        tk.Button(frame, text="Aplicar Nível", command=self.aplicar_isolamento).pack(side="left", padx=20)

        # Status
        self.status_conn = tk.Label(frame, text=f"Estado: CONECTADO ({self.db.SERVER_NAME})", fg="green")
        self.status_conn.pack(side="right", padx=10)

        # Aplicar o nível inicial
        self.aplicar_isolamento()

    def aplicar_isolamento(self):
        # Aplica o nível de isolamento escolhido usando o motor de BD.
        nivel = self.isolation_var.get()
        if self.db.set_isolation(nivel):
            self.status_conn.config(text=f"Estado: CONECTADO | {nivel}", fg="green")
        else:
            self.status_conn.config(text="Estado: Erro ao definir Isolamento", fg="orange")

    # --- Secção 2: Edição (Carregar Dados) ---
    def _criar_frame_edicao(self):
        frame = tk.LabelFrame(self, text="2. Cabeçalho da Encomenda", padx=10, pady=10)
        frame.pack(padx=10, pady=10, fill="x")

        tk.Label(frame, text="ID da Encomenda:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.enc_id_entry = tk.Entry(frame, textvariable=self.enc_id_var)
        self.enc_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        tk.Button(frame, text="Carregar Dados (SELECT)", command=self.carregar_dados).grid(row=0, column=2, padx=5, pady=5)
        
        tk.Label(frame, text="Nova Morada:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.morada_entry = tk.Entry(frame, textvariable=self.morada_var)
        self.morada_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

    def carregar_dados(self):
        """ LÊ os dados da BD (Passo 4) usando o motor. """
        if not self.is_connected:
            messagebox.showerror("Erro", "Perda de conexão.")
            return

        try:
            enc_id_text = self.enc_id_var.get()
            if not enc_id_text:
                messagebox.showwarning("Aviso", "Introduza um ID de Encomenda primeiro.")
                return
                
            enc_id = int(enc_id_text)
            
            # Chama o motor de BD para o SELECT
            header, linhas = self.db.fetch_encomenda_data(enc_id)
            
            # Preenche a UI
            self.morada_var.set(header.Morada)
            self.produtos_alterados = [] 
            self.atualizar_lista_produtos(linhas) # Passa as linhas lidas
            
            messagebox.showinfo("Carregado", f"Encomenda {enc_id} carregada. {len(linhas)} linhas encontradas.")
            
        except ValueError:
            messagebox.showerror("Erro", "ID da Encomenda deve ser um número inteiro.")
        except Exception as e:
            messagebox.showerror("Erro ao Carregar", f"Não foi possível ler os dados:\n{e}")
        
    
    # --- Secção 3: Linhas da Encomenda (e Controlo de Transação) ---
    def _criar_frame_produtos(self):
        frame = tk.LabelFrame(self, text="3. Linhas da Encomenda (Alterar Qtd)", padx=10, pady=10)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Usar uma Treeview
        self.tree = ttk.Treeview(frame, columns=("ID", "Designacao", "Preco", "Qtd"), show="headings")
        self.tree.heading("ID", text="ProdutoId")
        self.tree.heading("Designacao", text="Designacao")
        self.tree.heading("Preco", text="Preço")
        self.tree.heading("Qtd", text="Quantidade")
        self.tree.pack(padx=5, pady=5, fill="both", expand=True)
        
        tk.Button(frame, text="Adicionar/Alterar Produto (para o UPDATE)", command=self.adicionar_produto_ui).pack(pady=5)
        
        # Botões de Transação
        tk.Button(frame, text="GUARDAR (COMMIT) - Passo 6", bg="green", fg="white", 
                  font=("Segoe UI", 10, "bold"),
                  command=lambda: self.iniciar_transacao(pausar=False)).pack(side="left", padx=10, pady=20)
        
        tk.Button(frame, text="PAUSAR para Teste", bg="red", fg="white", 
                  font=("Segoe UI", 10, "bold"),
                  command=lambda: self.iniciar_transacao(pausar=True)).pack(side="left", padx=10, pady=20)

    def adicionar_produto_ui(self):
        """ Abre uma caixa de diálogo para introduzir o ID e a nova Qtd. """
        try:
            prod_id = simpledialog.askinteger("Produto", "Introduza o ID do Produto (da lista acima) a alterar:")
            if prod_id is None: return
            
            nova_qtd = simpledialog.askinteger("Quantidade", f"Introduza a NOVA Quantidade para o Produto {prod_id}:")
            if nova_qtd is None: return

            # Adicionar/Atualizar na lista interna
            self.produtos_alterados = [p for p in self.produtos_alterados if p['produto_id'] != prod_id]
            self.produtos_alterados.append({'produto_id': prod_id, 'nova_qtd': nova_qtd})
            
            messagebox.showinfo("Produto Adicionado", f"Produto {prod_id} será atualizado para {nova_qtd} no COMMIT.")
            
        except TypeError:
            pass # Cancelado

    def atualizar_lista_produtos(self, linhas_db):
        # Atualiza a Treeview com os dados lidos da BD. 
        # Limpa a árvore
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        # Insere os dados lidos da BD
        for linha in linhas_db:
            self.tree.insert("", "end", values=(linha.Produtold, linha.Designacao, linha.Preco, linha.Qtd))
            
    def iniciar_transacao(self, pausar=False):
        # Função principal que chama o motor de BD (Passos 2, 3, 5, 6, 7). 
        if not self.is_connected:
             messagebox.showerror("Erro", "Perda de conexão.")
             return
             
        try:
            enc_id_text = self.enc_id_var.get()
            if not enc_id_text:
                messagebox.showwarning("Aviso", "Carregue uma Encomenda primeiro.")
                return
                
            enc_id = int(enc_id_text)
            nova_morada = self.morada_var.get()
            
            # Validação simples para não submeter se nada mudou
            # (Isto pode ser melhorado se 'header' for guardado em self)
            # if nova_morada == self.morada_original and not self.produtos_alterados:
            #      messagebox.showwarning("Aviso", "Não foram especificadas alterações (Morada ou Produtos).")
            #      return

            # Chama a função principal do motor de BD
            self.db.editar_encomenda(
                enc_id, 
                nova_morada, 
                self.produtos_alterados, 
                pausar_para_teste=pausar
            )
            
            # Recarregar os dados após o commit
            self.carregar_dados()
            
        except ValueError:
            messagebox.showerror("Erro", "ID da Encomenda inválido.")
        except Exception as e:
            messagebox.showerror("Erro na Transação", f"Ocorreu um erro: {e}")


# CONTROLADOR PRINCIPAL (TESTE DIRETO SEM LOGIN) ---

if __name__ == '__main__':
    
    print("--- INICIANDO TESTE DE CONEXÃO DIRETA ---")

    # 1. Temos as credenciais (hardcoded do grupo)
    creds = {
        "server": "192.168.100.14,1433",
        "database": "SGBD_PL1_02",
        "user": "User_SGBD_PL1_02",
        "password": "diubi:2025!SGBD!PL1_02"
    }
    
    print(f"A tentar conectar a {creds['server']} como {creds['user']}...")

    # 2. Criar o motor de BD
    db_conn_edit = DbConnectionEdit() # Cria a instância do motor

    # 3. Tentar a conexão
    try:
        if not db_conn_edit.connect(creds['server'], creds['database'], creds['user'], creds['password']):
            # Se 'connect' retornar None (falha)
            print("--- CONEXÃO FALHOU (connect retornou None) ---")
            messagebox.showerror("Erro de Conexão", 
                                 f"Não foi possível conectar a {creds['server']}.\n"
                                 "Verifique a consola para o erro pyodbc.")
            sys.exit(1)
            
    except Exception as e:
        # Se 'connect' lançar uma exceção
        print(f"--- CONEXÃO FALHOU (Exceção: {e}) ---")
        messagebox.showerror("Erro Crítico de Conexão", 
                             f"Falha ao conectar: {e}\n"
                             "Verifique a rede, Firewall, TCP/IP e as credenciais.")
        sys.exit(1)

    
    # 4. SUCESSO
    print("--- CONEXÃO BEM-SUCEDIDA ---")
    print("A iniciar AppEdit...")
    
    app = AppEdit(db_conn_edit) # Passar a conexão para a App
    app.mainloop() # Iniciar a App Principal