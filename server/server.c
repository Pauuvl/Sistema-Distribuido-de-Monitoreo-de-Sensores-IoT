#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <time.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define MAX_CLIENTS 64
#define BUFFER_SIZE 512

#define TYPE_UNKNOWN 0
#define TYPE_SENSOR 1
#define TYPE_OPERATOR 2

typedef struct {
    int sockfd;
    int active;
    int registered;
    int client_type;
    char id[64];
    char sensor_type[16];
    double last_value;
    time_t last_ping;
} Client;

Client clients[MAX_CLIENTS];
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
FILE *log_file;

/* ---------- LOG ---------- */
void log_event(const char *msg) {
    time_t now = time(NULL);
    char buffer[64];
    strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", localtime(&now));

    printf("[%s] %s\n", buffer, msg);

    if (log_file) {
        fprintf(log_file, "[%s] %s\n", buffer, msg);
        fflush(log_file);
    }
}

/* ---------- SOCKET HELPERS ---------- */
int read_line(int sock, char *buffer) {
    int i = 0;
    char c;
    while (i < BUFFER_SIZE - 1) {
        int r = recv(sock, &c, 1, 0);
        if (r <= 0) return -1;
        if (c == '\n') break;
        buffer[i++] = c;
    }
    buffer[i] = '\0';
    return i;
}

void send_line(int sock, const char *msg) {
    char buffer[BUFFER_SIZE];
    sprintf(buffer, "%s\n", msg);
    send(sock, buffer, strlen(buffer), 0);
}

/* ---------- ALERT ---------- */
void broadcast_alert(const char *msg) {
    pthread_mutex_lock(&mutex);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].active && clients[i].client_type == TYPE_OPERATOR) {
            send_line(clients[i].sockfd, msg);
        }
    }
    pthread_mutex_unlock(&mutex);
}

/* ---------- CLIENT HANDLER ---------- */
void *handle_client(void *arg) {
    int idx = *(int *)arg;
    free(arg);

    int sock = clients[idx].sockfd;
    char buffer[BUFFER_SIZE];

    log_event("Nueva conexión");

    while (1) {
        int n = read_line(sock, buffer);
        if (n <= 0) break;

        char cmd[32];
        sscanf(buffer, "%s", cmd);

        /* REGISTER */
        if (strcmp(cmd, "REGISTER") == 0) {
            char type[16], id[64];

            if (sscanf(buffer, "%*s %s %s", type, id) >= 2) {
                clients[idx].registered = 1;
                strcpy(clients[idx].id, id);

                if (strcmp(type, "SENSOR") == 0)
                    clients[idx].client_type = TYPE_SENSOR;
                else
                    clients[idx].client_type = TYPE_OPERATOR;

                char response[BUFFER_SIZE];
                sprintf(response, "OK REGISTERED %s", id);
                send_line(sock, response);

                char logmsg[128];
                sprintf(logmsg, "REGISTER %s", id);
                log_event(logmsg);
            }
        }

        /* DATA */
        else if (strcmp(cmd, "DATA") == 0) {
            char id[64], tipo[16], ts[32];
            double valor;

            if (sscanf(buffer, "%*s %s %s %lf %s", id, tipo, &valor, ts) == 4) {
                clients[idx].last_value = valor;

                send_line(sock, "OK DATA_RECEIVED");

                char logmsg[128];
                sprintf(logmsg, "DATA %s %s %.2f", id, tipo, valor);
                log_event(logmsg);

                if (valor > 75) {
                    char alert[BUFFER_SIZE];
                    sprintf(alert, "ALERT %s %s HIGH %.2f %s", id, tipo, valor, ts);

                    broadcast_alert(alert);
                    log_event(alert);
                }
            }
        }

        /* GET SENSORS */
        else if (strcmp(cmd, "GET") == 0) {
            char resp[BUFFER_SIZE] = "SENSORS";
            int found = 0;

            pthread_mutex_lock(&mutex);
            for (int i = 0; i < MAX_CLIENTS; i++) {
                if (clients[i].active && clients[i].client_type == TYPE_SENSOR) {
                    char tmp[128];
                    sprintf(tmp, " %s:%.2f", clients[i].id, clients[i].last_value);
                    strcat(resp, tmp);
                    found = 1;
                }
            }
            pthread_mutex_unlock(&mutex);

            if (!found) strcpy(resp, "SENSORS NONE");

            send_line(sock, resp);
            log_event("GET SENSORS");
        }

        /* PING */
        else if (strcmp(cmd, "PING") == 0) {
            send_line(sock, "PONG");
            log_event("PING recibido");
        }

        /* DISCONNECT */
        else if (strcmp(cmd, "DISCONNECT") == 0) {
            send_line(sock, "OK BYE");
            log_event("Cliente desconectado");
            break;
        }

        else {
            send_line(sock, "ERROR UNKNOWN_COMMAND");
            log_event("ERROR comando desconocido");
        }
    }

    close(sock);

    pthread_mutex_lock(&mutex);
    clients[idx].active = 0;
    pthread_mutex_unlock(&mutex);

    return NULL;
}

/* ---------- MAIN ---------- */
int main(int argc, char *argv[]) {
    if (argc != 3) {
        printf("Uso: %s <puerto> <log>\n", argv[0]);
        return 1;
    }

    int port = atoi(argv[1]);
    log_file = fopen(argv[2], "a");

    int server_fd = socket(AF_INET, SOCK_STREAM, 0);

    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    addr.sin_addr.s_addr = INADDR_ANY;

    bind(server_fd, (struct sockaddr *)&addr, sizeof(addr));
    listen(server_fd, 10);

    printf("Servidor escuchando en puerto %d\n", port);

    while (1) {
        int client_fd = accept(server_fd, NULL, NULL);

        pthread_mutex_lock(&mutex);
        int idx = -1;
        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (!clients[i].active) {
                idx = i;
                clients[i].active = 1;
                clients[i].sockfd = client_fd;
                break;
            }
        }
        pthread_mutex_unlock(&mutex);

        if (idx >= 0) {
            pthread_t tid;
            int *arg = malloc(sizeof(int));
            *arg = idx;
            pthread_create(&tid, NULL, handle_client, arg);
            pthread_detach(tid);
        }
    }

    return 0;
}