import socket
import threading
import os
import curses
import time

# Define server address and port
SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12345

class ChatApp:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.sockets = []
        self.messages = []
        self.input_buffer = ""
        self.running = True
        
    def send_message_to_clients(self, message: str):
        for client in self.sockets:
            try:
                client.send(message.encode('utf-8'))
            except socket.error:
                self.sockets.remove(client)  # Remove disconnected clients
                
    def send_file_to_clients(self, filename: str):
        if os.path.isfile(filename):
            for client in self.sockets:
                try:
                    client.send(f"(FILE){filename}".encode('utf-8'))
                    with open(filename, 'rb') as f:
                        client.sendall(f.read())
                except socket.error:
                    self.sockets.remove(client)
                    
            self.messages.append("-File sent successfully-")
        else:
            self.messages.append("-File not found-")
            
    def get_username(self, client_socket: socket) -> str:
        client_socket.send("SERVER: What Is Your Username?".encode('utf-8'))
        username = client_socket.recv(1024).decode('utf-8')
        self.messages.append(f"{username} has joined the chat")
        self.send_message_to_clients(f"{username} has joined the chat")
        return username
    
    def acquire_sockets(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((SERVER_HOST, SERVER_PORT))
        server.listen(5)
        self.messages.append(f"Server listening on {SERVER_HOST}:{SERVER_PORT}")
    
        while self.running:
            client_socket, addr = server.accept()
            self.sockets.append(client_socket)
            threading.Thread(target=self.listen_to_client, args=(client_socket,), daemon=True).start()
            
        server.close()
            
    def listen_to_client(self, client_socket: socket):
        username = self.get_username(client_socket)
    
        while self.running:
            try:
                message = client_socket.recv(1024).decode('utf-8')
                if not message or message == "(EXIT)":
                    self.handle_disconnection(client_socket, username)
                    break
                    
                elif message.startswith("(FILE)"):
                    self.handle_file_transfer(client_socket, message)
                
                else:
                    self.messages.append(f"{username}: {message}")
                    self.send_message_to_clients(f"{username}: {message}")
                
            except socket.error:
                self.handle_disconnection(client_socket, username)
                break
                
        client_socket.close()
                
    def handle_disconnection(self, client_socket: socket, username: str):
        self.messages.append(f"{username} disconnected")
        self.send_message_to_clients(f"{username} disconnected")
        self.sockets.remove(client_socket)
        client_socket.close()
        
    def handle_file_transfer(self, client_socket: socket, message: str):
        filename = message.lstrip("(FILE)")
        file_data = client_socket.recv(1024)  # Assuming the file is sent in one chunk for simplicity
        
        with open(f"server-downloads/{filename}", 'wb') as f:
            f.write(file_data)
        self.messages.append(f"-{filename} file received successfully-")
        
    def send_to_clients(self):
        while self.running:
            self.draw()
            key = self.stdscr.getch()

            if key in (curses.KEY_BACKSPACE, 127):
                self.input_buffer = self.input_buffer[:-1]
            elif key in (curses.KEY_ENTER, 10, 13):
                self.handle_input()
            elif key != -1:
                self.input_buffer += chr(key)

            time.sleep(0.1)

    def handle_input(self):
        if self.input_buffer.startswith("(FILE)"):
            filename = self.input_buffer.lstrip("(FILE)")
            self.send_file_to_clients(filename)
        elif self.input_buffer == "(EXIT)":
            self.running = False
        elif self.input_buffer == "(CLEAR)":
            self.messages = []
        elif self.input_buffer:
            self.messages.append(f"SERVER: {self.input_buffer}")
            self.send_message_to_clients(f"SERVER: {self.input_buffer}")
        
        self.input_buffer = ""
                    
    def draw(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # Draw messages
        for i, msg in enumerate(self.messages[-(h - 2):]):
            try:
                self.stdscr.addstr(i, 0, msg)
            except curses.error:
                pass  # Ignore any curses error for now

        # Draw input box
        self.stdscr.addstr(h - 1, 0, "> " + self.input_buffer)
        self.stdscr.refresh()

    def run(self):
        # Start thread to listen for incoming clients
        threading.Thread(target=self.acquire_sockets, daemon=True).start()
    
        self.stdscr.nodelay(1)
        self.stdscr.keypad(1)

        self.send_to_clients()

    def stop(self):
        self.running = False

# Main client function
def start_server(stdscr):
    app = ChatApp(stdscr)
    try:
        app.run()
    except KeyboardInterrupt:
        app.stop()

if __name__ == "__main__":
    curses.wrapper(start_server)
