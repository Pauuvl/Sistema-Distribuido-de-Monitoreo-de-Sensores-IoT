#  IoT Monitoring System — Servidor Central

##  Descripción

Este proyecto implementa un **Servidor Central de Monitoreo IoT** desarrollado en lenguaje C, que permite la comunicación entre sensores simulados y operadores mediante un protocolo de aplicación propio sobre TCP.

El servidor recibe mediciones de sensores, procesa los datos, detecta anomalías y notifica a los operadores en tiempo real.

---

## Integrantes del grupo

* Juan José Álvarez
* Helen Valentina Sanabria
* Paulina Velásquez

---

## Arquitectura del sistema

El sistema está compuesto por:

* **Sensores IoT** → envían datos periódicos
* **Servidor central (este proyecto)** → procesa datos y genera alertas
* **Operadores** → consultan información y reciben alertas

---

## Tecnologías utilizadas

* Lenguaje: C
* Comunicación: Sockets TCP (`SOCK_STREAM`)
* Concurrencia: Hilos (`pthread`)
* Sistema operativo: Linux / WSL

---

## Ejecución del servidor

### 1. Compilar

```bash
gcc -o server server.c -lpthread
```

### 2. Ejecutar

```bash
./server 9090 logs.txt
```

Parámetros:

* `9090` → Puerto del servidor
* `logs.txt` → Archivo donde se guardan los logs

---

## Protocolo de comunicación (IoTMP)

El servidor implementa un protocolo basado en texto plano.

### Registro de operador

```
REGISTER OPERATOR <id>
```

Ejemplo:

```
REGISTER OPERATOR op1
```

---

### Registro de sensor

```
REGISTER SENSOR <id>
```

Ejemplo:

```
REGISTER SENSOR s1
```

---

### Envío de datos

```
DATA <sensor-id> <tipo> <valor> <timestamp>
```

Ejemplo:

```
DATA s1 temp 80.0 2024-01-01T10:00:00
```

---

### Consulta de sensores

```
GET SENSORS
```

---

### Ping

```
PING
```

---

### Desconexión

```
DISCONNECT
```

---

## Sistema de alertas

El servidor genera alertas cuando un valor supera un umbral:

* Temperatura > 75 → `HIGH`
* Temperatura > 95 → `CRITICAL`

Ejemplo de alerta:

```
ALERT s1 temp HIGH 80.00 2024-01-01T10:00:00
```

Las alertas se envían automáticamente a todos los operadores conectados.

---

## Sistema de logs

El servidor registra eventos importantes en tiempo real en un archivo de logs:

* Conexión de clientes
* Registro de sensores y operadores
* Recepción de datos
* Generación de alertas
* Desconexiones

Ejemplo:

```
[2026-03-31 12:20:57] DATA s1 temp 80.00
[2026-03-31 12:20:57] ALERT s1 temp HIGH 80.00 2024-01-01T10:00:00
```

---

##  Pruebas del sistema

Se puede probar el servidor usando `netcat`:

### Operador

```bash
nc localhost 9090
```

```
REGISTER OPERATOR op1
GET SENSORS
```

---

### Sensor

```bash
nc localhost 9090
```

```
REGISTER SENSOR s1
DATA s1 temp 80.0 2024-01-01T10:00:00
```

---

##  Características principales

* Manejo de múltiples clientes simultáneos
* Comunicación en tiempo real
* Protocolo propio basado en texto
* Sistema de alertas automático
* Registro de eventos (logging)
* Arquitectura cliente-servidor

---

## Consideraciones

* El servidor es tolerante a múltiples conexiones
* Los datos se procesan en tiempo real
* Los logs permiten trazabilidad del sistema
* El diseño es escalable para integrar más sensores

---

##  Curso

Internet: Arquitectura y Protocolos
