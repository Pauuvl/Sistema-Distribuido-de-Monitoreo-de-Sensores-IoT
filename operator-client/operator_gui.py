import socket
import threading
import tkinter as tk
from tkinter import scrolledtext

# ==============================
# CONFIGURACIÓN
# ==============================
HOST = "iot-monitoring.com"  # Cambia por tu dominio (NO IP fija en entrega final)
PORT = 9090

# ==============================
# SOCKET CLIENTE
# ==============================
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# ==============================
# INTERFAZ
# ==============================
root = tk.Tk()
root.title("IoT Monitoring Operator")
root.geometry("800x600")

# ====== FRAME SUPERIOR ======
frame_top = tk.Frame(root)
frame_top.pack(pady=10)

btn_connect = tk.Button(frame_top, text="Conectar", width=15)
btn_connect.grid(row=0, column=0, padx=5)

btn_get_sensors = tk.Button(frame_top, text="Obtener Sensores", width=20)
btn_get_sensors.grid(row=0, column=1, padx=5)

# ====== SENSORES ======
label_sensors = tk.Label(root, text="Sensores Activos")
label_sensors.pack()

list_sensors = tk.Listbox(root, height=8)
list_sensors.pack(fill=tk.X, padx=20)

# ====== MEDICIONES ======
label_data = tk.Label(root, text="Mediciones en Tiempo Real")
label_data.pack()

text_data = scrolledtext.ScrolledText(root, height=10)
text_data.pack(fill=tk.BOTH, padx=20, pady=5)

# ====== ALERTAS ======
label_alerts = tk.Label(root, text="Alertas")
label_alerts.pack()

text_alerts = scrolledtext.ScrolledText(root, height=10, fg="red")
text_alerts.pack(fill=tk.BOTH, padx=20, pady=5)

# ==============================
# FUNCIONES
# ==============================

def connect_to_server():
    try:
        client.connect((HOST, PORT))
        client.send("REGISTER OPERATOR op1\n".encode())
        text_data.insert(tk.END, "Conectado al servidor\n")
        threading.Thread(target=receive_messages, daemon=True).start()
    except Exception as e:
        text_data.insert(tk.END, f"Error: {e}\n")


def get_sensors():
    try:
        client.send("GET SENSORS\n".encode())
    except:
        text_data.insert(tk.END, "No conectado\n")


def receive_messages():
    while True:
        try:
            message = client.recv(1024).decode()
            if not message:
                break

            process_message(message)

        except:
            break


def process_message(msg):
    lines = msg.strip().split("\n")

    for line in lines:
        if line.startswith("ALERT"):
            text_alerts.insert(tk.END, line + "\n")
            text_alerts.see(tk.END)

        elif line.startswith("DATA"):
            text_data.insert(tk.END, line + "\n")
            text_data.see(tk.END)

        elif line.startswith("SENSOR"):
            list_sensors.insert(tk.END, line)

        else:
            text_data.insert(tk.END, line + "\n")

connected = False

def connect_to_server():
    global connected
    if connected:
        text_data.insert(tk.END, "Ya estás conectado\n")
        return

    try:
        client.connect((HOST, PORT))
        client.send("REGISTER OPERATOR op1\n".encode())
        connected = True
        text_data.insert(tk.END, "Conectado al servidor\n")
        threading.Thread(target=receive_messages, daemon=True).start()
    except Exception as e:
        text_data.insert(tk.END, f"Error: {e}\n")
# ==============================
# EVENTOS BOTONES
# ==============================

btn_connect.config(command=connect_to_server)
btn_get_sensors.config(command=get_sensors)

# ==============================
# EJECUCIÓN
# ==============================
root.mainloop()