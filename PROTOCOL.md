# IoT Monitoring System — Especificación del Protocolo de Aplicación

**Versión:** 1.0  
**Curso:** Internet: Arquitectura y Protocolos  
**Proyecto:** Sistema Distribuido de Monitoreo de Sensores IoT

---

## 1. Descripción general

El protocolo de aplicación IoTMP (IoT Monitoring Protocol) define la comunicación entre tres entidades:

- **Sensores IoT simulados** — envían mediciones periódicas al servidor
- **Operadores del sistema** — consultan el estado y reciben alertas en tiempo real
- **Servidor central de monitoreo** — procesa mediciones, detecta anomalías y notifica operadores

---

## 2. Características del protocolo

| Característica | Valor |
|---|---|
| Capa | Aplicación (sobre TCP) |
| Tipo de transporte | TCP (SOCK_STREAM) |
| Codificación | Texto plano UTF-8 |
| Terminador de mensaje | Salto de línea `\n` |
| Puerto por defecto | 8080 (configurable por argumento) |

### Justificación del uso de TCP

Se utiliza `SOCK_STREAM` (TCP) en lugar de `SOCK_DGRAM` (UDP) porque:

- Las mediciones de sensores no pueden perderse sin detectarlo — una pérdida silenciosa de datos en un sistema industrial puede ocultar una falla crítica.
- Las alertas enviadas a operadores deben llegar en orden y de forma garantizada.
- La latencia no es un factor crítico en este sistema (los sensores envían datos cada varios segundos), por lo que el overhead de TCP es aceptable.

---

## 3. Formato general de mensajes

Todos los mensajes son texto plano en una sola línea, con campos separados por espacios y terminados en `\n`:

```
COMANDO [ARG1] [ARG2] ... [ARGN]\n
```

**Reglas:**
- Los comandos son en mayúsculas.
- Los argumentos no pueden contener espacios.
- Cada mensaje ocupa exactamente una línea.
- El servidor lee hasta encontrar `\n` para procesar un mensaje.

---

## 4. Mensajes del protocolo

### 4.1 REGISTER — Registro de cliente

Enviado por el cliente al conectarse. Identifica si es un sensor o un operador.

#### Registro de sensor

```
REGISTER SENSOR <tipo> <sensor-id>\n
```

| Campo | Descripción | Valores válidos |
|---|---|---|
| `tipo` | Tipo de sensor | `temp`, `vibr`, `energy` |
| `sensor-id` | Identificador único | Alfanumérico, sin espacios |

**Ejemplo:**
```
REGISTER SENSOR temp sensor-001\n
```

**Respuesta exitosa:**
```
OK REGISTERED <sensor-id>\n
```

**Ejemplo de respuesta:**
```
OK REGISTERED sensor-001\n
```

---

#### Registro de operador

```
REGISTER OPERATOR <operator-id>\n
```

**Ejemplo:**
```
REGISTER OPERATOR operador-001\n
```

**Respuesta exitosa:**
```
OK REGISTERED <operator-id>\n
```

---

### 4.2 DATA — Envío de medición

Enviado periódicamente por un sensor con su lectura actual.

```
DATA <sensor-id> <tipo> <valor> <timestamp>\n
```

| Campo | Descripción | Formato |
|---|---|---|
| `sensor-id` | ID del sensor registrado | Alfanumérico |
| `tipo` | Tipo de medición | `temp`, `vibr`, `energy` |
| `valor` | Valor numérico medido | Decimal con punto, ej: `36.5` |
| `timestamp` | Momento de la medición | ISO 8601: `YYYY-MM-DDTHH:MM:SS` |

**Ejemplo:**
```
DATA sensor-001 temp 36.5 2024-01-15T10:30:00\n
```

**Respuesta del servidor:**
```
OK DATA_RECEIVED\n
```

**Nota:** Si el valor supera un umbral de alerta (ver sección 6), el servidor adicionalmente enviará un mensaje `ALERT` a todos los operadores conectados.

---

### 4.3 GET SENSORS — Consulta de sensores activos

Enviado por un operador para obtener la lista de sensores activos y sus últimas mediciones.

```
GET SENSORS\n
```

**Respuesta del servidor:**
```
SENSORS <id>:<tipo>:<valor> <id>:<tipo>:<valor> ...\n
```

**Ejemplo de respuesta:**
```
SENSORS sensor-001:temp:36.5 sensor-002:vibr:0.02 sensor-003:energy:120.3\n
```

Si no hay sensores activos:
```
SENSORS NONE\n
```

---

### 4.4 ALERT — Notificación de anomalía

Enviado **espontáneamente por el servidor** a todos los operadores conectados cuando detecta un valor anómalo. El operador no lo solicita — el servidor lo envía en cuanto procesa un `DATA` que supera el umbral.

```
ALERT <sensor-id> <tipo> <nivel> <valor> <timestamp>\n
```

| Campo | Descripción | Valores |
|---|---|---|
| `nivel` | Severidad de la alerta | `HIGH`, `LOW`, `CRITICAL` |

**Ejemplo:**
```
ALERT sensor-001 temp HIGH 85.3 2024-01-15T10:31:00\n
```

---

### 4.5 PING / PONG — Heartbeat

Permite verificar que la conexión sigue activa. Cualquier cliente puede enviarlo.

```
PING\n
```

**Respuesta del servidor:**
```
PONG\n
```

Si el servidor no recibe `PING` de un sensor en más de 60 segundos, lo marca como inactivo.

---

### 4.6 DISCONNECT — Desconexión limpia

Enviado por el cliente para cerrar la conexión de forma ordenada.

```
DISCONNECT\n
```

**Respuesta del servidor:**
```
OK BYE\n
```

Tras enviar `OK BYE`, el servidor cierra el socket del cliente.

---

### 4.7 ERROR — Mensajes de error

Enviado por el servidor cuando ocurre un problema.

```
ERROR <código>\n
```

| Código | Descripción |
|---|---|
| `UNKNOWN_COMMAND` | El comando recibido no existe en el protocolo |
| `AUTH_FAILED` | El cliente no está registrado o la autenticación falló |
| `INVALID_FORMAT` | El mensaje no tiene el formato esperado |
| `SENSOR_NOT_FOUND` | Se referencia un sensor-id que no está registrado |

**Ejemplo:**
```
ERROR UNKNOWN_COMMAND\n
ERROR AUTH_FAILED\n
```

---

## 5. Diagrama de flujo — Ciclo de vida de un sensor

```
Sensor                        Servidor
  |                               |
  |--- REGISTER SENSOR temp s1 -->|
  |<-- OK REGISTERED s1 ---------|
  |                               |
  |--- DATA s1 temp 36.5 ... ---->|  (cada N segundos)
  |<-- OK DATA_RECEIVED ----------|
  |                               |
  |--- PING ---------------------->|
  |<-- PONG ----------------------|
  |                               |
  |--- DISCONNECT --------------->|
  |<-- OK BYE --------------------|
  |                               |
```

## 6. Diagrama de flujo — Alerta a operador

```
Sensor          Servidor              Operador
  |                 |                     |
  |-- DATA s1 ----->|                     |
  |                 | (valor > umbral)    |
  |<- OK DATA_REC.  |-- ALERT s1 HIGH --> |
  |                 |                     |
```

---

## 7. Umbrales de alerta

| Tipo | Unidad | Alerta HIGH | Alerta LOW | Alerta CRITICAL |
|---|---|---|---|---|
| `temp` | °C | > 75 | < -5 | > 95 |
| `vibr` | mm/s | > 3.0 | — | > 7.0 |
| `energy` | kW | > 400 | — | > 600 |

---

## 8. Consideraciones de implementación

### Lectura de mensajes en C

En el servidor implementado en C, se recomienda leer el socket byte a byte hasta encontrar `\n`:

```c
int read_line(int sockfd, char *buffer, int maxlen) {
    int n = 0;
    char c;
    while (n < maxlen - 1) {
        if (recv(sockfd, &c, 1, 0) <= 0) break;
        if (c == '\n') break;
        buffer[n++] = c;
    }
    buffer[n] = '\0';
    return n;
}
```

### Manejo de errores de red

Si ocurre un error al leer o escribir en el socket, el servidor debe:
1. Registrar el error en el archivo de logs con IP y puerto del cliente.
2. Liberar el hilo/recursos asociados al cliente.
3. Continuar ejecutándose sin finalizar el proceso.

### Clientes no registrados

Si un cliente envía cualquier comando distinto a `REGISTER` sin haberse registrado primero, el servidor responde:

```
ERROR AUTH_FAILED\n
```

---

## 9. Ejemplo de sesión completa — Sensor

```
C → S: REGISTER SENSOR temp sensor-001\n
S → C: OK REGISTERED sensor-001\n
C → S: DATA sensor-001 temp 22.4 2024-01-15T10:00:00\n
S → C: OK DATA_RECEIVED\n
C → S: DATA sensor-001 temp 88.1 2024-01-15T10:00:05\n
S → C: OK DATA_RECEIVED\n
       [servidor detecta 88.1 > 75 → envía ALERT a operadores]
C → S: PING\n
S → C: PONG\n
C → S: DISCONNECT\n
S → C: OK BYE\n
```

## 10. Ejemplo de sesión completa — Operador

```
C → S: REGISTER OPERATOR operador-001\n
S → C: OK REGISTERED operador-001\n
C → S: GET SENSORS\n
S → C: SENSORS sensor-001:temp:22.4 sensor-002:vibr:0.01\n
       [tiempo después, el servidor recibe un DATA anómalo]
S → C: ALERT sensor-001 temp HIGH 88.1 2024-01-15T10:00:05\n
C → S: DISCONNECT\n
S → C: OK BYE\n
```