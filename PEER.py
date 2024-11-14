import socket
import threading
import time
import os
from flags import Flags
from helper import *
from binascii import crc_hqx

"""
Flags:
SYN =                0b00000001  = 1
ACK =                0b00000010  = 2
NACK =               0b00000100  = 4
KILL =               0b00001000  = 8
KEEP_ALIVE =         0b00010000  = 16
SENDING_TEXT =       0b00100000  = 32
SENDING_FILE =       0b00100001  = 33
LAST_TEXT_FRAGMENT = 0b10000000  = 128
LAST_FILE_FRAGMENT = 0b10000001  = 129
"""

#! make separate functions for printing 
#! implement proper way to end

class PEER:
    def __init__(self, local_ip, local_port, dest_ip, dest_port):
        self.local_ip = local_ip
        self.local_port = local_port
        self.destination_ip = dest_ip
        self.destination_port = dest_port

        self.save_folder_path = "downloads"
        self.save_file_name = "test01"
        self.save_file_extension = "txt"
        self.MAX_FRAGMENT_SIZE = 1465

        self.done_handshake = False

        self.stop_keep_alive = threading.Event()
        self.reset_keep_alive = threading.Event()

        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind((self.local_ip, self.local_port))


    def send_basic_keep_alive(self):
        number_of_tries = 0
        time_between_heartbeats = 5
        while True:
            if not self.stop_keep_alive.is_set() and number_of_tries != 3:
                send_time = time.time() + time_between_heartbeats
                
                while time.time() < send_time:
                    time.sleep(2)
                    if self.reset_keep_alive.is_set():
                        send_time = time.time() + time_between_heartbeats
                        self.reset_keep_alive.clear()

                send_system_message(self.send_sock, (self.destination_ip, self.destination_port), 0, 0, Flags.KEEP_ALIVE)
                try:
                    self.send_sock.settimeout(5.0)
                    whole_data, _ = self.send_sock.recvfrom(self.MAX_FRAGMENT_SIZE)
                    data = unpack_received_data(whole_data)
                    if data['flag'] == Flags.ACK:
                        number_of_tries = 0
            
                except Exception:
                    number_of_tries += 1
        
            if number_of_tries == 3:
                print("Keep alive didn't get through!")
                self.done_handshake = False
                break


    def establish_connection(self):
        number_of_tries = 0
        while number_of_tries < 3:
            send_system_message(self.send_sock, (self.destination_ip, self.destination_port), 0, 0, Flags.SYN)
            try:
                whole_data, _ = self.send_sock.recvfrom(self.MAX_FRAGMENT_SIZE)
                data = unpack_received_data(whole_data)
                if data["flag"] == Flags.ACK:
                    self.done_handshake = True
                    break
                
            except Exception:
                time.sleep(5) # pause for 5 seconds between each try, sleep is usable here because we cannot communicate withou handshake either way
                number_of_tries += 1
                continue

        if number_of_tries == 3:
            print("Couldn't establish connection. Exiting app!")
            os._exit(0)


    def receiver(self):
        recieved_text : str = ""
        received_file_fragments : bytes = []

        while True:
            whole_data, client = self.recv_sock.recvfrom(self.MAX_FRAGMENT_SIZE)
            data = unpack_received_data(whole_data)

            if data['crc'] == crc_hqx(create_header(data['seq_num'],0,data['flag']) + data['data'], 0xFFFF):
                if data['flag'] == Flags.SYN:
                    send_system_message(self.recv_sock, client, 0, 0, Flags.ACK)

                elif data['flag'] == Flags.KEEP_ALIVE:
                    self.reset_keep_alive.set()
                    send_system_message(self.recv_sock, client, 0, 0, Flags.ACK)

                elif data['flag'] == Flags.SENDING_TEXT:
                    recieved_text += data['data'].decode()
                    print(f"Received segment no.{data['seq_num']}")
                elif data['flag'] == Flags.LAST_TEXT_FRAGMENT:
                    recieved_text += data['data'].decode()
                    print(f"Received segment no.{data['seq_num']}")
                    print(f"Received text: \n{recieved_text}")
                    recieved_text = ""

                elif data['flag'] == Flags.SENDING_FILE:
                    received_file_fragments.append(data['data'])
                    print(f"Received segment no.{data['seq_num']}")
                elif data['flag'] == Flags.LAST_FILE_FRAGMENT:
                    received_file_fragments.append(data['data'])
                    print(f"Received segment no.{data['seq_num']}")
                    save_received_file(self.save_folder_path, received_file_fragments, self.save_file_name, self.save_file_extension)
                    received_file_fragments = []

            else:
                #!best to implement functions to receive said segments
                print("Message is corrupted, crc doesn't match") 


    def sender(self):
        keep_alive_thread = threading.Thread(target=self.send_basic_keep_alive)

        while True:
            user_input = input("\nDo you want to send something?\n-yes/y : continue to specify your sending parameters \n-exit/e : quit this application\n")
            if user_input == "exit" or user_input == 'e':
                break
            elif user_input == "yes" or user_input == 'y':
                if not self.done_handshake:
                    self.establish_connection()
                    keep_alive_thread.start() 

                user_input = input("Input the desired size of fragment: ")
                if user_input.isnumeric() and  int(user_input) <= self.MAX_FRAGMENT_SIZE: 
                    fragment_size = int(user_input)
                else:
                    continue

                user_input = input("Do you want to send a text or a file (t/f): ")
                if user_input == 't':
                    message = input("Input you text that you want to send: ")
                    self.stop_keep_alive.set()
                    send_text_fragments(self.send_sock, (self.destination_ip, self.destination_port), fragment_text(message,fragment_size))
                    self.stop_keep_alive.clear()

                elif user_input == 'f':
                    print("Defaults.....")
                    file_path = input("Input path to file you want to send: ")
                    if not os.path.exists(file_path) or not os.path.isfile(file_path):
                        print("Given path leads to nothing or a directory!")
                        continue
                    else:
                        self.stop_keep_alive.set()
                        send_file_fragments(self.send_sock, (self.destination_ip, self.destination_port), fragment_file(file_path,fragment_size))
                        self.stop_keep_alive.clear()
                else: 
                    continue
            else: 
                continue
        
        os._exit(0)


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
