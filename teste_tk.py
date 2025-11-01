import tkinter as tk

try:
    print("A tentar iniciar o Tkinter...")
    root = tk.Tk()
    root.title("Teste de UI")
    root.geometry("300x100")
    
    label = tk.Label(root, text="Se estás a ver isto, o Tkinter funciona!")
    label.pack(pady=20)
    
    print("Janela criada. A mostrar...")
    root.mainloop()
    
except Exception as e:
    print(f"ERRO: O Tkinter falhou ao iniciar: {e}")