# Sistema Distribuido de Monitoreo de Sensores IoT

Proyecto Nro. 1 — Internet: Arquitectura y Protocolos  
Universidad EAFIT · 2026-1

---

## Integrantes

- Juan José Álvarez
- Helen Valentina Sanabria
- Paulina Velásquez

---

## ¿Qué es esto?

Un sistema distribuido de monitoreo IoT desplegado en AWS. Simula sensores industriales (temperatura, vibración y energía) que se conectan a un servidor central, el cual detecta anomalías y notifica a los operadores en tiempo real.

El servidor corre en C dentro de un contenedor Docker en una instancia EC2, y los clientes se conectan al dominio `iot-monitoring.com` configurado en Route 53.

---

## Estructura del proyecto

```
├── server/
│   ├── server.c          # servidor central en C
│   ├── dockerfile        # para construir la imagen Docker
│   └── logs.txt          # logs generados en ejecución
│
├── sensor-client/
│   ├── sensor.py         # 5 sensores simulados en Python
│   └── sensor.cpp        # 5 sensores simulados en C++
│
├── operator-client/
│   └── operator_gui.py   # interfaz gráfica del operador (tkinter)
│
├── web/
│   └── web_server.py     # servidor HTTP básico con login
│
├── auth_service/
│   └── auth_server.py    # servicio de autenticación externo
│
└── PROTOCOL.md           # especificación completa del protocolo
```

---

## Cómo correr el sistema localmente

### Servidor

```bash
cd server/
gcc -o server server.c -lpthread
./server 9090 logs.txt
```

### Sensores (Python)

```bash
cd sensor-client/
pip install -r requirements.txt
python sensor.py
```

### Sensores (C++)

```bash
cd sensor-client/
g++ -std=c++17 -pthread -o sensor sensor.cpp
./sensor
```

### Operador

```bash
cd operator-client/
python operator_gui.py
```

### Autenticación y web

```bash
# En terminales separadas:
python auth_service/auth_server.py
python web/web_server.py
# Abrir http://localhost:8000 — usuario: admin
```

### Prueba rápida con netcat

```bash
nc localhost 9090
REGISTER OPERATOR op1
GET SENSORS
```

---

## Protocolo de aplicación (IoTMP)

Protocolo de texto plano sobre TCP. Cada mensaje es una línea terminada en `\n`.

### Mensajes

**Registro:**
```
REGISTER SENSOR <tipo> <id>    # tipo: temp | vibr | energy
REGISTER OPERATOR <id>
→ OK REGISTERED <id>
```

**Envío de datos:**
```
DATA <id> <tipo> <valor> <timestamp>
→ OK DATA_RECEIVED
```

**Consulta de sensores:**
```
GET SENSORS
→ SENSORS sensor-001:temp:36.50 sensor-003:vibr:1.20 ...
```

**Heartbeat:**
```
PING → PONG
```

**Desconexión:**
```
DISCONNECT → OK BYE
```

**Alertas (el servidor las envía automáticamente):**
```
ALERT <id> <tipo> HIGH <valor> <timestamp>
```

Umbrales de alerta: temperatura > 75°C, vibración > 3.0 mm/s, energía > 400 kW.

**Errores:**
```
ERROR UNKNOWN_COMMAND
ERROR NOT_REGISTERED
ERROR DATA_FORMAT
ERROR REGISTER_FORMAT
```

---

## Docker

```bash
cd server/
docker build -t iot-server .
docker run -d -p 9090:9090 --name iot-server iot-server
docker logs iot-server
```

---

## Despliegue en AWS

La instancia EC2 corre en `54.221.60.253` (Ubuntu 24.04, t2.micro) con el puerto 9090 abierto. El dominio `iot-monitoring.com` está configurado en Route 53 apuntando a esa IP con un registro A.

### Pasos para desplegar desde cero

```bash
# 1. Conectarse
chmod 400 labsuser.pem
ssh -i labsuser.pem ubuntu@54.221.60.253

# 2. Instalar Docker
sudo apt-get update
sudo apt-get install -y docker.io
sudo systemctl start docker
sudo usermod -aG docker ubuntu
exit  # reconectar después

# 3. Clonar y buildear
git clone https://github.com/Pauuvl/Sistema-Distribuido-de-Monitoreo-de-Sensores-IoT.git
cd Sistema-Distribuido-de-Monitoreo-de-Sensores-IoT/server
docker build -t iot-server .
docker run -d -p 9090:9090 --name iot-server iot-server

# 4. Verificar
docker ps
nc iot-monitoring.com 9090
```

---

## Logging

El servidor registra cada petición en consola y en el archivo de logs:

```
[2026-04-05 21:00:00] IP:190.x.x.x PORT:54321
REQ: DATA sensor-001 temp 82.50 2026-04-05T21:00:05
RES: OK DATA_RECEIVED

[2026-04-05 21:00:00] IP:190.x.x.x PORT:54321
REQ: DATA sensor-001 temp 82.50 2026-04-05T21:00:05
RES: ALERT sensor-001 temp HIGH 82.50 2026-04-05T21:00:05
```
