import socket
import sys

# Настройки
HOST = '0.0.0.0'  # Слушать на всех интерфейсах
PORT = 444

def main():
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen(1)
        print(f"[*] Сервер запущен и слушает на {HOST}:{PORT}")

        conn, addr = server.accept()
        print(f"[+] Подключение от {addr}")

        while True:
            command = input("shell> ")  # Ввод команды
            if command.lower() == 'exit':
                conn.send(b'exit\n')
                break
            conn.send((command + '\n').encode('utf-8'))  # Отправка команды агенту

            # Получение вывода (читаем до 4096 байт, можно увеличить при необходимости)
            output = conn.recv(4096).decode('utf-8', errors='ignore')
            print(output.strip())

        conn.close()
        server.close()
    except Exception as e:
        print(f"[-] Ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()