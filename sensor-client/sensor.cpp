/*
 * sensor.cpp — Cliente sensor IoT (C++)
 * Sistema Distribuido de Monitoreo de Sensores IoT
 *
 * Equivalente en C++ de sensor.py.
 * Lanza 5 sensores en hilos separados. Cada sensor:
 *   - Resuelve el servidor por nombre de dominio (NO IP fija)
 *   - Se registra con REGISTER SENSOR <tipo> <id>
 *   - Envía mediciones periódicas con DATA
 *   - Mantiene la conexión activa con PING
 *   - Reconecta automáticamente si pierde la conexión
 *
 * Compilar:
 *   g++ -std=c++17 -pthread -o sensor sensor.cpp
 *
 * Ejecutar:
 *   ./sensor
 */

#include <iostream>
#include <string>
#include <vector>
#include <thread>
#include <chrono>
#include <random>
#include <sstream>
#include <iomanip>
#include <ctime>
#include <cstring>

#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <unistd.h>

// ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
const std::string SERVER_HOST = "localhost";  // CAMBIAR por dominio DNS cuando Juan lo configure
                                              // Ejemplo: "iot.midominio.com"
const int         SERVER_PORT = 9090;         // CAMBIAR a 8080 cuando esté en AWS
const int         SEND_INTERVAL  = 5;         // segundos entre mediciones
const int         PING_INTERVAL  = 20;        // segundos entre PINGs
const int         RECONNECT_WAIT = 5;         // segundos antes de reintentar conexión
// ──────────────────────────────────────────────────────────────────────────────

struct SensorConfig {
    std::string id;
    std::string tipo;
};

const std::vector<SensorConfig> SENSORS = {
    {"sensor-cpp-001", "temp"},
    {"sensor-cpp-002", "temp"},
    {"sensor-cpp-003", "vibr"},
    {"sensor-cpp-004", "vibr"},
    {"sensor-cpp-005", "energy"},
};

// ─── GENERADOR DE VALORES SIMULADOS ──────────────────────────────────────────
double generate_value(const std::string& tipo, std::mt19937& rng) {
    std::uniform_real_distribution<double> dist01(0.0, 1.0);

    if (tipo == "temp") {
        std::uniform_real_distribution<double> base(20.0, 40.0);
        std::uniform_real_distribution<double> anomaly(76.0, 100.0);
        return (dist01(rng) < 0.15) ? anomaly(rng) : base(rng);
    }
    if (tipo == "vibr") {
        std::uniform_real_distribution<double> base(0.5, 2.5);
        std::uniform_real_distribution<double> anomaly(3.1, 8.0);
        return (dist01(rng) < 0.10) ? anomaly(rng) : base(rng);
    }
    if (tipo == "energy") {
        std::uniform_real_distribution<double> base(100.0, 350.0);
        std::uniform_real_distribution<double> anomaly(401.0, 650.0);
        return (dist01(rng) < 0.10) ? anomaly(rng) : base(rng);
    }
    return 0.0;
}

// ─── TIMESTAMP ISO 8601 ───────────────────────────────────────────────────────
std::string timestamp_now() {
    std::time_t now = std::time(nullptr);
    std::tm* tm_info = std::localtime(&now);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", tm_info);
    return std::string(buf);
}

// ─── CLASE SENSOR ─────────────────────────────────────────────────────────────
class Sensor {
public:
    Sensor(const std::string& id, const std::string& tipo)
        : id_(id), tipo_(tipo), sockfd_(-1), connected_(false), running_(true),
          rng_(std::random_device{}()) {}

    void run() {
        int ping_counter = 0;

        while (running_) {
            if (!connect()) break;
            if (!register_sensor()) {
                disconnect_socket();
                std::this_thread::sleep_for(std::chrono::seconds(RECONNECT_WAIT));
                continue;
            }

            while (running_ && connected_) {
                if (!send_data()) {
                    log("Conexión perdida. Reconectando...");
                    break;
                }

                ping_counter += SEND_INTERVAL;
                if (ping_counter >= PING_INTERVAL) {
                    if (!send_ping()) break;
                    ping_counter = 0;
                }

                std::this_thread::sleep_for(std::chrono::seconds(SEND_INTERVAL));
            }

            disconnect_socket();

            if (running_) {
                log("Reconectando en " + std::to_string(RECONNECT_WAIT) + "s...");
                std::this_thread::sleep_for(std::chrono::seconds(RECONNECT_WAIT));
            }
        }
    }

    void stop() { running_ = false; }

private:
    std::string id_;
    std::string tipo_;
    int sockfd_;
    bool connected_;
    bool running_;
    std::mt19937 rng_;

    void log(const std::string& msg) {
        std::cout << "[" << id_ << "] " << msg << "\n";
    }

    // Resuelve el hostname por DNS y conecta — NO usa IPs fijas
    bool connect() {
        while (running_) {
            struct addrinfo hints{}, *res = nullptr;
            hints.ai_family   = AF_INET;
            hints.ai_socktype = SOCK_STREAM;

            std::string port_str = std::to_string(SERVER_PORT);
            int err = getaddrinfo(SERVER_HOST.c_str(), port_str.c_str(), &hints, &res);

            if (err != 0) {
                // Error de resolución DNS — manejar sin terminar
                log("Error DNS al resolver '" + SERVER_HOST + "': " +
                    std::string(gai_strerror(err)));
                log("Reintentando en " + std::to_string(RECONNECT_WAIT) + "s...");
                std::this_thread::sleep_for(std::chrono::seconds(RECONNECT_WAIT));
                continue;
            }

            sockfd_ = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
            if (sockfd_ < 0) {
                log("Error al crear socket.");
                freeaddrinfo(res);
                std::this_thread::sleep_for(std::chrono::seconds(RECONNECT_WAIT));
                continue;
            }

            if (::connect(sockfd_, res->ai_addr, res->ai_addrlen) < 0) {
                log("Error de conexión: " + std::string(strerror(errno)));
                log("Reintentando en " + std::to_string(RECONNECT_WAIT) + "s...");
                ::close(sockfd_);
                sockfd_ = -1;
                freeaddrinfo(res);
                std::this_thread::sleep_for(std::chrono::seconds(RECONNECT_WAIT));
                continue;
            }

            freeaddrinfo(res);
            connected_ = true;
            log("Conectado a " + SERVER_HOST + ":" + std::to_string(SERVER_PORT));
            return true;
        }
        return false;
    }

    // Envía una línea terminada en \n
    bool send_line(const std::string& msg) {
        std::string line = msg + "\n";
        ssize_t sent = send(sockfd_, line.c_str(), line.size(), 0);
        if (sent < 0) {
            log("Error al enviar: " + std::string(strerror(errno)));
            connected_ = false;
            return false;
        }
        return true;
    }

    // Lee una línea del socket (hasta \n)
    std::string recv_line() {
        std::string result;
        char c;
        while (true) {
            ssize_t r = recv(sockfd_, &c, 1, 0);
            if (r <= 0) return "";
            if (c == '\n') break;
            result += c;
        }
        return result;
    }

    bool register_sensor() {
        std::string msg = "REGISTER SENSOR " + tipo_ + " " + id_;
        if (!send_line(msg)) return false;

        std::string resp = recv_line();
        if (resp.rfind("OK REGISTERED", 0) == 0) {
            log("Registrado correctamente");
            return true;
        }
        log("Fallo al registrar: " + resp);
        return false;
    }

    bool send_data() {
        double valor = generate_value(tipo_, rng_);
        std::ostringstream oss;
        oss << std::fixed << std::setprecision(2) << valor;

        std::string msg = "DATA " + id_ + " " + tipo_ + " " + oss.str() +
                          " " + timestamp_now();
        if (!send_line(msg)) return false;

        std::string resp = recv_line();
        if (!resp.empty()) {
            log("Enviado " + tipo_ + "=" + oss.str() + " → " + resp);
        }
        return true;
    }

    bool send_ping() {
        if (!send_line("PING")) return false;
        std::string resp = recv_line();
        if (resp == "PONG") log("PING → PONG ✓");
        return true;
    }

    void disconnect_socket() {
        if (sockfd_ >= 0) {
            send_line("DISCONNECT");
            ::close(sockfd_);
            sockfd_ = -1;
        }
        connected_ = false;
        log("Desconectado");
    }
};

// ─── MAIN ─────────────────────────────────────────────────────────────────────
int main() {
    std::cout << "=== Sistema de Sensores IoT (C++) ===\n";
    std::cout << "Servidor: " << SERVER_HOST << ":" << SERVER_PORT << "\n";
    std::cout << "Sensores configurados: " << SENSORS.size() << "\n";
    std::cout << "=====================================\n";

    std::vector<Sensor*> sensors;
    std::vector<std::thread> threads;

    for (const auto& cfg : SENSORS) {
        auto* s = new Sensor(cfg.id, cfg.tipo);
        sensors.push_back(s);
        threads.emplace_back(&Sensor::run, s);
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
    }

    // Esperar Ctrl+C
    std::cout << "\nPresiona Ctrl+C para detener los sensores.\n";
    for (auto& t : threads) t.join();

    for (auto* s : sensors) delete s;
    return 0;
}