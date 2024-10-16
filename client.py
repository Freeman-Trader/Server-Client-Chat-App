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
        self.messages = []
        self.input_buffer = ""
        self.running = True

    def draw(self):
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()

        # Draw messages
        for i, msg in enumerate(self.messages[-(h - 2):]):
            try:
                self.stdscr.addstr(i, 0, msg)
            except curses.error:
                pass  # Ignore curses errors

        # Draw input box
        self.stdscr.addstr(h - 1, 0, "> " + self.input_buffer)
        self.stdscr.refresh()
        
    def listen_to_server(self, server: socket):
        while self.running:
            try:
                message = server.recv(1024).decode('utf-8')
                if not message:
                    break  # Connection closed by server

                if message.startswith("(FILE)"):
                    self.handle_file_receive(server, message)
                else:
                    self.messages.append(message)
                
            except socket.error:
                break  # Handle socket errors
            
        server.close()  # Close the server socket

    def handle_file_receive(self, server: socket, message: str):
        filename = message.lstrip("(FILE)")
        with open(f"client-downloads/{filename}", 'wb') as f:
            file_data = server.recv(1024)  # Read the file data
            f.write(file_data)
        self.messages.append(f"-{filename} file received successfully-")

    def send_to_server(self, server: socket):
        while self.running:
            self.draw()
            key = self.stdscr.getch()

            if key in (curses.KEY_BACKSPACE, 127):
                self.input_buffer = self.input_buffer[:-1]
                
            elif key in (curses.KEY_ENTER, 10, 13):
                self.process_input(server)
                    
            elif key != -1:
                self.input_buffer += chr(key)

            time.sleep(0.1)

    def process_input(self, server: socket):
        if self.input_buffer.startswith("(FILE)"):
            self.send_file_to_server(server)
        elif self.input_buffer == "(EXIT)":
            server.send(self.input_buffer.encode('utf-8'))
            self.stop(server)
        elif self.input_buffer == "(CLEAR)":
            self.messages = []
        elif self.input_buffer:
            server.send(self.input_buffer.encode('utf-8'))
        
        self.input_buffer = ""

    def send_file_to_server(self, server: socket):
        filename = self.input_buffer.lstrip("(FILE)")
        if os.path.isfile(filename):
            server.send(f"(FILE){filename}".encode('utf-8'))
            with open(filename, 'rb') as f:
                server.sendall(f.read())
            self.messages.append("-File sent successfully-")
        else:
            self.messages.append("-File not found-")

    def run(self, server: socket):
        # Start thread to listen for incoming messages
        threading.Thread(target=self.listen_to_server, args=(server,), daemon=True).start()
    
        self.stdscr.nodelay(1)
        self.stdscr.keypad(1)

        self.send_to_server(server)

    def stop(self, server: socket):
        self.running = False
        server.close()

# Main client function
def start_client(stdscr):
    # Connect to the designated server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.connect((SERVER_HOST, SERVER_PORT))
    
    # Create the chat application
    app = ChatApp(stdscr)
    
    # Start the chat application
    try:
        app.run(server)
    except KeyboardInterrupt:
        app.stop(server)

if __name__ == "__main__":
    curses.wrapper(start_client)
