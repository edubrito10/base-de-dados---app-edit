import tkinter as tk
from tkinter import messagebox, simpledialog
# Importar funções e variáveis do seu ficheiro principal (main.py)
# NOTA: Certifique-se que o seu ficheiro principal não executa código ao ser importado.
try:
    from main import (
        NIVEL_ISOLAMENTO_ATUAL, 
        conectar_db, 
        definir_isolamento, 
        editar_encomenda,
        SERVER_NAME # Necessário para exibir o status
    )
except ImportError:
    # Se a importação falhar (e.g., está a desenvolver num ambiente diferente)
    # Use uma função Mock (Simulação) para testar a interface sem a BD.
    def conectar_db(): return True
    def definir_isolamento(conn, nivel): return True
    def editar_encomenda(enc_id, morada, produtos, pausar): 
        messagebox.showinfo("MOCK", f"Simulação de Edição Concluída para ENCOMENDA {enc_id}.")
        print(f"MOCK: Morada: {morada}, Produtos: {produtos}")
    print("Aviso: Modo de simulação (MOCK) ativo. A BD real não será contactada.")


class AppEdit(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("MEI - Aplicação Edit | Controlo de Transações")
        self.geometry("900x650")
        
        # Variáveis de Estado
        self.conn = None
        self.isolation_var = tk.StringVar(value=NIVEL_ISOLAMENTO_ATUAL)
        self.is_connected = False
        
        # Variáveis de Edição
        self.enc_id_var = tk.StringVar()
        self.morada_var = tk.StringVar()
        self.produtos_alterados = [] # Lista para armazenar {'produto_id', 'nova_qtd'}
        
        # ----------------------------------------------------
        self._criar_frame_configuracao()
        self._criar_frame_edicao()
        self._criar_frame_produtos()
        
    # --- Secção 1: Configuração e Conexão ---
    def _criar_frame_configuracao(self):
        frame = tk.LabelFrame(self, text="1. Conexão & Nível de Isolamento", padx=10, pady=10)
        frame.pack(padx=10, pady=10, fill="x")

        # Nível de Isolamento
        tk.Label(frame, text="Nível de Isolamento:").pack(side="left", padx=5)
        opcoes_isolamento = [
            "READ UNCOMMITTED", "READ COMMITTED", 
            "REPEATABLE READ", "SERIALIZABLE", "SNAPSHOT"
        ]
        isolamento_menu = tk.OptionMenu(frame, self.isolation_var, *opcoes_isolamento)
        isolamento_menu.pack(side="left", padx=10)
        
        # Botão Conectar
        tk.Button(frame, text="Conectar & Aplicar Isolamento", command=self.conectar_e_configurar).pack(side="left", padx=20)

        # Status
        self.status_conn = tk.Label(frame, text="Estado: Desconectado", fg="red")
        self.status_conn.pack(side="right", padx=10)

    def conectar_e_configurar(self):
        """ Tenta conectar e aplica o nível de isolamento. """
        
        # Tenta conectar usando a função do main.py
        temp_conn = conectar_db() # Liga a BD
        
        if temp_conn:
            if definir_isolamento(temp_conn, self.isolation_var.get()): # Aplica o nível
                self.conn = temp_conn
                self.is_connected = True
                self.status_conn.config(text=f"Estado: CONECTADO | {self.isolation_var.get()}", fg="green")
                messagebox.showinfo("Sucesso", f"Conectado a {SERVER_NAME} com Isolamento {self.isolation_var.get()}")
            else:
                self.status_conn.config(text="Estado: Erro ao definir Isolamento", fg="orange")
                temp_conn.close()
        else:
            self.status_conn.config(text="Estado: FALHA NA CONEXÃO", fg="red")


    # --- Secção 2: Edição ---
    def _criar_frame_edicao(self):
        frame = tk.LabelFrame(self, text="2. Cabeçalho da Encomenda", padx=10, pady=10)
        frame.pack(padx=10, pady=10, fill="x")

        # ID da Encomenda
        tk.Label(frame, text="ID da Encomenda:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.enc_id_entry = tk.Entry(frame, textvariable=self.enc_id_var)
        self.enc_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Botão para carregar dados (SELECT)
        tk.Button(frame, text="Carregar Dados (SELECT)", command=self.carregar_dados).grid(row=0, column=2, padx=5, pady=5)
        
        # Morada (Permitir Edição)
        tk.Label(frame, text="Nova Morada:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.morada_entry = tk.Entry(frame, textvariable=self.morada_var)
        self.morada_var.set("Morada Original...")
        self.morada_entry.grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")

    def carregar_dados(self):
        """ Simula a leitura dos dados (SELECT - Passo 4). """
        if not self.is_connected:
            messagebox.showerror("Erro", "Primeiro deve conectar à base de dados.")
            return

        try:
            enc_id = int(self.enc_id_var.get())
            # *** Na aplicação REAL, este código SELECT seria executado aqui para preencher a UI ***
            
            # Simulação:
            self.morada_var.set(f"[Dados da BD] Morada da Enc. {enc_id}")
            self.produtos_alterados = [] # Limpa a lista
            self.atualizar_lista_produtos()
            messagebox.showinfo("Carregado", f"Encomenda {enc_id} carregada. Atualize a morada e os produtos.")
            
        except ValueError:
            messagebox.showerror("Erro", "ID da Encomenda deve ser um número inteiro.")
        
    
    # --- Secção 3: Linhas da Encomenda ---
    def _criar_frame_produtos(self):
        frame = tk.LabelFrame(self, text="3. Linhas da Encomenda (Alterar Qtd)", padx=10, pady=10)
        frame.pack(padx=10, pady=10, fill="both", expand=True)

        # Lista de Produtos
        self.lista_produtos_listbox = tk.Listbox(frame, height=10)
        self.lista_produtos_listbox.pack(padx=5, pady=5, fill="x")
        
        # Botão para adicionar/alterar produto
        tk.Button(frame, text="Adicionar/Alterar Produto", command=self.adicionar_produto_ui).pack(pady=5)
        
        # Botões de Transação
        tk.Button(frame, text="GUARDAR (COMMIT) - Passo 6", bg="green", fg="white", 
                  command=lambda: self.iniciar_transacao(pausar=False)).pack(side="left", padx=10, pady=20)
        
        tk.Button(frame, text="PAUSAR para Teste (ROLLBACK Manual)", bg="red", fg="white", 
                  command=lambda: self.iniciar_transacao(pausar=True)).pack(side="left", padx=10, pady=20)

    def adicionar_produto_ui(self):
        """ Abre uma caixa de diálogo para introduzir o ID e a nova Qtd. """
        try:
            prod_id = simpledialog.askinteger("Produto", "Introduza o ID do Produto:")
            if prod_id is None: return
            
            nova_qtd = simpledialog.askinteger("Quantidade", f"Introduza a NOVA Quantidade para o Produto {prod_id}:")
            if nova_qtd is None: return

            # Adicionar/Atualizar na lista interna
            self.produtos_alterados = [p for p in self.produtos_alterados if p['produto_id'] != prod_id]
            self.produtos_alterados.append({'produto_id': prod_id, 'nova_qtd': nova_qtd})
            
            self.atualizar_lista_produtos()
            
        except TypeError:
            pass # Cancelado

    def atualizar_lista_produtos(self):
        """ Atualiza o Listbox com os produtos que serão alterados. """
        self.lista_produtos_listbox.delete(0, tk.END)
        self.lista_produtos_listbox.insert(tk.END, "PRODUTOS A ALTERAR (UPDATE EncLinha):")
        for p in self.produtos_alterados:
            self.lista_produtos_listbox.insert(tk.END, f"  ID: {p['produto_id']} -> Nova Qtd: {p['nova_qtd']}")
            
    def iniciar_transacao(self, pausar=False):
        """ Função principal que chama editar_encomenda (Passos 2, 3, 5, 6, 7). """
        if not self.is_connected:
             messagebox.showerror("Erro", "Primeiro deve conectar e aplicar o nível de isolamento.")
             return
             
        try:
            enc_id = int(self.enc_id_var.get())
            nova_morada = self.morada_var.get()
            
            if not nova_morada and not self.produtos_alterados:
                 messagebox.showwarning("Aviso", "Não foram especificadas alterações (Morada ou Produtos).")

            # Chama a função principal do motor de BD (main.py)
            editar_encomenda(
                enc_id, 
                nova_morada, 
                self.produtos_alterados, 
                pausar_para_teste=pausar
            )
            
        except ValueError:
            messagebox.showerror("Erro", "ID da Encomenda inválido.")
        except Exception as e:
            messagebox.showerror("Erro", f"Ocorreu um erro: {e}")


if __name__ == '__main__':
    app = AppEdit()
    app.mainloop()