import socket
import threading
from datetime import datetime
from python_version.parser.parser import ParseError, Parser
from python_version.server.accounts import Accounts


class Server:
    encoding = 'utf-8'

    def __init__(self, config: tuple):
        self.ip, self.port = config
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(config)
        self.sock.listen(12)
        self.hosts = []
        self.parser = Parser(self.encoding)
        self.accounts = Accounts(db_name='users.db', encoding=self.encoding)
        self.accounts.create_tables()

    def remove_host(self, ip_addr: str):
        for idx, host in enumerate(self.hosts):
            if host['addr'] == ip_addr:
                del self.hosts[idx]
                break

    @staticmethod
    def print_msg(message: dict):
        print(f'\033[1;33m{message["author"]}: {message["datetime"]}\n{message["content"]["text"]}\033[0m')

    def read_handler(self, conn: socket.socket, addr: str, user_id: int):
        while True:
            buff = conn.recv(1024)
            if buff:
                try:
                    decoded_msg = self.parser.decode(buff)
                except ParseError:
                    print('parse error')
                    break
                if decoded_msg['type'] == 'message':
                    encoded_msg = self.parser.encode(
                        author=addr,
                        msg_type='message',
                        datetime=datetime.now().strftime("%H:%M:%S %d-%m-%y"),
                        content=decoded_msg['content']
                        )
                    self.print_msg(decoded_msg)
                    for host in self.hosts:
                        host['conn'].send(encoded_msg)
                elif decoded_msg['type'] == 'disconnect':
                    self.remove_host(addr)
                    print(f'({addr}) has disconnected')
                    break

    def log_user(self, conn):
        tries_left = 3
        while tries_left > 0:
            buff = conn.recv(1024)
            if buff:
                buff = self.parser.decode(buff)
                if buff['type'] == 'login':
                    nick = buff['content']['nick']
                    password = buff['content']['password']
                    user_id = self.accounts.log_in(nick=nick, password=password)
                    if user_id:
                        return int(user_id)
                    else:
                        tries_left -= 1
                        self.send_server_message(conn, f'Wrong password\n{tries_left} tries left')
                elif buff['type'] == 'disconnect':
                    return None
                else:
                    self.send_server_message(conn, f'You have to authorize before sending messages')
        return None

    def register_user(self, conn):
        pass
        # if not self.accounts.add_user():
        #     print()

    def handle_connection(self, conn, host_addr):
        user_id = self.log_user(conn)
        if user_id:
            conn.send(self.parser.encode(
                author='server',
                msg_type='authorized',
                datetime=datetime.now().strftime("%H:%M:%S %d-%m-%y")
            ))
            self.hosts.append({'conn': conn, 'addr': host_addr})
            self.read_handler(conn, host_addr, user_id)
        else:
            self.send_server_message(conn, f'Disconnected from server')
        print(f'({host_addr}) has disconnected')

    def run(self):
        while True:
            conn, host_addr = self.sock.accept()
            host_addr = f'{host_addr[0]}:{host_addr[1]}'
            print(f'({host_addr}) has connected')

            reader = threading.Thread(target=self.handle_connection, args=(conn, host_addr), daemon=True)
            reader.start()

    def send_server_message(self, conn, msg):
        curr_time = datetime.now().strftime("%H:%M:%S %d-%m-%y")
        # self.print_msg({'author': 'server', 'datetime': curr_time, 'text': msg})

        encoded_msg = self.parser.encode(
            author='server',
            msg_type='message',
            datetime=curr_time,
            content={'text': msg}
        )
        conn.send(encoded_msg)


if __name__ == '__main__':

    config = ('0.0.0.0', 1111)
    server = Server(config)
    server.run()
