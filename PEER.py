import socket
import threading
import struct
import os
from flags import Flags
from binascii import crc_hqx
"""
Flags:
SYN =                0b00000001
ACK =                0b00000010
NACK =               0b00000100
KILL =               0b00001000
KEEP_ALIVE =         0b00010000
SENDING_TEXT =       0b00100000
SENDING_FILE =       0b00100001
LAST_TEXT_FRAGMENT = 0b10000000
LAST_FILE_FRAGMENT = 0b10000001
"""

#----------------------INTERNET / AI GENERATED---------------------------------------------------

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))   # random IP just to send a packet
        IP = s.getsockname()[0]   # get our actual ip
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

#--------------------------------------------------------------------------------------------------

class PEER:
    def __init__(self, local_ip, local_port, dest_ip, dest_port):
        self.local_ip = local_ip
        self.local_port = local_port
        self.destination_ip = dest_ip
        self.destination_port = dest_port

        self.done_handshake = False
        self.MAX_FRAGMENT_SIZE = 1465

        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind((self.local_ip, self.local_port))


    def create_header(self, seq_num, crc16, flags):
        return struct.pack('!IHB', seq_num, crc16, flags)

    def send_message(self, seq_num, crc16, flags, data):
        header = self.create_header(seq_num, crc16, flags)
        if data == None: segment = header 
        else: segment = header + data.encode('utf-8')
        self.send_sock.sendto(segment, (self.destination_ip, self.destination_port))

    def send_response(self, seq_num, crc16, flag, client):
        header = self.create_header(seq_num, crc16, flag)
        self.recv_sock.sendto(header, client)

    def establish_connection(self):
        number_of_tries = 0
        while number_of_tries < 3:
            print("Establishing connection!\nStarting HandShake!\n")
            self.send_message(0, 0, Flags.SYN, None)
            try:
                self.send_sock.settimeout(1.0) # waiting one second for ack 
                whole_data, _ = self.send_sock.recvfrom(self.MAX_FRAGMENT_SIZE)
                header = whole_data[:7] 
                _, _, flag = struct.unpack("!IHB", header)
                if flag == Flags.ACK:
                    self.done_handshake = True
                    break
                
            except socket.timeout:
                number_of_tries += 1
                continue


    def receiver(self):
        print("Starting receiver")
        arrived = 0
        while True:
            whole_data, client = self.recv_sock.recvfrom(self.MAX_FRAGMENT_SIZE)
            header = whole_data[:7]
            seq_num, crc16, flag = struct.unpack("!IHB", header)
            data = whole_data[7:]
            
            if flag == Flags.SYN:
                arrived += 1
                if arrived == 2: 
                    self.send_response(0, 0, Flags.ACK, client)

            print(f"Received message: {data.decode()} from {client}")
            print(f"Header details : seq_num: {seq_num}, sum: {crc16}, flags: {flag}")


    def sender(self):
        print("Starting sender")
        
        seq_num = 0

        while True:
            user_input = input("\nDo you want to send something?\n-yes/y : continue to specify your sending parameters \n-exit/e : quit this application\n")
            if user_input == "exit" or user_input == 'e':
                break
            elif user_input == "yes" or user_input == 'y':
                if not self.done_handshake:
                    self.establish_connection()
                else:
                    user_input = input("Input the desired size of fragment: ")
                    if user_input.isnumeric() and  int(user_input) <= self.MAX_FRAGMENT_SIZE: 
                        fragment_size = user_input
                    else:
                        continue

                    user_input = input("Do you want to send a text or a file (t/f): ")
                    if user_input == 't':
                        message = input("Input you text that you want to send: ")
                        self.send_message(seq_num, 0, Flags.SENDING_TEXT, message)
                        seq_num += 1

                    elif user_input == 'f':
                        print("File functionality will be done later")
                    else: 
                        continue
            else: 
                continue
            
        os._exit(1)


    def begin(self):
        receiver = threading.Thread(target=self.receiver, daemon=True)
        receiver.start()

        sender = threading.Thread(target=self.sender, daemon=True)
        sender.start()

        sender.join()
        receiver.join()

if __name__ == "__main__":
    #local_ip = get_ip()
    local_ip = "127.0.0.1"
    local_port = int(input("Input the port you are listening on: "))
    destination_ip = input("Input the IP of the host: ") or "127.0.0.1"
    destination_port = int(input("Input the host's reciever port: "))
    peer = PEER(local_ip, local_port, destination_ip, destination_port)
    peer.begin()
