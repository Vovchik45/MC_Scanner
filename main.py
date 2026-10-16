import tkinter as tk
from modules.app import StringCollectorApp

if __name__ == "__main__":
    root = tk.Tk()
    app = StringCollectorApp(root)
    root.mainloop()