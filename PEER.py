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

class PEER:
    def __init__(self, local_ip, local_port, dest_ip, dest_port):
        self.local_ip = local_ip
        self.local_port = local_port
        self.destination_ip = dest_ip
        self.destination_port = dest_port

        self.MAX_FRAGMENT_SIZE = 1465
    
        self.save_folder = "downloads"
        self.done_handshake = False

        self.stop_keep_alive = threading.Event()
        self.reset_keep_alive = threading.Event()

        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock.bind((self.local_ip, self.local_port))


    def keep_alive(self):
        number_of_tries = 0
        time_between_heartbeats = 5
        while True:
            if not self.stop_keep_alive.is_set() and number_of_tries != 3:
                send_time = time.time() + time_between_heartbeats
                
                while time.time() < send_time:
                    time.sleep(2) # check every 2 seconds if the other side has sent a keep alive
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
                print("Host not responding. Ending application!")
                os._exit(0)


    def establish_connection(self):
        number_of_tries = 0
        while number_of_tries < 3:
            send_system_message(self.send_sock, (self.destination_ip, self.destination_port), 0, 0, Flags.SYN)
            try:
                self.send_sock.settimeout(5)
                whole_data, _ = self.send_sock.recvfrom(self.MAX_FRAGMENT_SIZE)
                data = unpack_received_data(whole_data)
                if data["flag"] == Flags.ACK:
                    self.done_handshake = True
                    break
                
            except Exception:
                number_of_tries += 1

        if number_of_tries == 3:
            print("Couldn't establish connection. Ending application!")
            os._exit(0)


    def receiver(self):
        received_fragments : bytes = []
        transfer_start_time = None
        last_received_seq_num = None

        while True:
            whole_data, client = self.recv_sock.recvfrom(1465)
            data = unpack_received_data(whole_data)

            if data['crc'] == crc_hqx(create_header(data['seq_num'],0,data['flag']) + data['data'], 0xFFFF):
                if last_received_seq_num == 0: last_received_seq_num = None

                if data['flag'] == Flags.SYN:
                    send_system_message(self.recv_sock, client, 0, 0, Flags.ACK)

                elif data['flag'] == Flags.KEEP_ALIVE:
                    self.reset_keep_alive.set()
                    send_system_message(self.recv_sock, client, 0, 0, Flags.ACK)

                elif data['flag'] == Flags.SENDING_TEXT:
                    if data['seq_num'] == last_received_seq_num: continue
                    last_received_seq_num = data['seq_num']
                    if data['seq_num'] == 0 : transfer_start_time = time.time()
                    received_fragments.append(data['data'])
                    send_system_message(self.recv_sock, client, 0, 0, Flags.ACK)
                    print(f"Received segment no.{data['seq_num']} correctly!")

                elif data['flag'] == Flags.LAST_TEXT_FRAGMENT:
                    if data['seq_num'] == last_received_seq_num: continue
                    last_received_seq_num = 0
                    received_fragments.append(data['data'])
                    send_system_message(self.recv_sock, client, 0, 0, Flags.ACK)
                    print(f"Received segment no.{data['seq_num']} correctly!")
                    if transfer_start_time == None: transfer_start_time = time.time()
                    print_receiver_info(False, time.time() - transfer_start_time, received_fragments, self.save_folder)
                    print_initial_dialog(self.save_folder)
                    transfer_start_time = None
                    received_fragments = []

                elif data['flag'] == Flags.SENDING_FILE:
                    if data['seq_num'] == last_received_seq_num: continue
                    last_received_seq_num = data['seq_num']
                    if data['seq_num'] == 0 : transfer_start_time = time.time()
                    received_fragments.append(data['data'])
                    send_system_message(self.recv_sock, client, 0, 0, Flags.ACK)
                    print(f"Received segment no.{data['seq_num']} correctly!")

                elif data['flag'] == Flags.LAST_FILE_FRAGMENT:
                    if data['seq_num'] == last_received_seq_num: continue
                    last_received_seq_num = 0
                    received_fragments.append(data['data'])
                    send_system_message(self.recv_sock, client, 0, 0, Flags.ACK)
                    print(f"Received segment no.{data['seq_num']} correctly!")
                    save_received_file(received_fragments, self.save_folder)
                    if transfer_start_time == None: transfer_start_time = time.time()
                    print_receiver_info(True, time.time() - transfer_start_time, received_fragments, self.save_folder)
                    print_initial_dialog(self.save_folder)
                    transfer_start_time = None
                    received_fragments = []

                elif data['flag'] == Flags.KILL:
                    send_system_message(self.recv_sock, (self.destination_ip, self.destination_port), 0, 0, Flags.ACK)
                    print("Host disconnected. Ending application!")
                    os._exit(0)

                elif data['flag'] == Flags.ACK:
                    print("Host disconnected. Ending application!")
                    os._exit(0)

            else:
                print(f"Received segment no.{data['seq_num']} with an error!")
                send_system_message(self.recv_sock, client, data['seq_num'], 0, Flags.NACK)


    def sender(self):
        keep_alive_thread = threading.Thread(target=self.keep_alive)

        while True:
            user_input = input(f"\nApp is ready. Make sure the other side is also up!\n-txt/t : send text\n-file/f : send file\n-s/d : change the path where would you like to store files you receive. Current is: {self.save_folder}\n-exit/e : quit this application\n")
            if user_input == "exit" or user_input == 'e':
                break

            elif user_input == "txt" or user_input == 't' or user_input == "file" or user_input == 'f':
                if not self.done_handshake:
                    self.establish_connection()
                    keep_alive_thread.start()

            elif user_input == 'd' or user_input == 's':
                save_folder = input("Please input new path where received files will be saved: ")
                while not os.path.exists(save_folder) or not os.path.isdir(save_folder):
                    print("Given path leads to nothing or a file!")
                    save_folder = input("Please input new path where received files will be saved: ")
                self.save_folder = save_folder


            if user_input == "txt" or user_input == 't':
                user_input = input("Input the desired size of fragment, whole number <1,1465>: ")
                while not user_input.isnumeric() or (int(user_input) > self.MAX_FRAGMENT_SIZE or int(user_input) <= 0): 
                    user_input = input("Input the desired size of fragment, whole number <1,1465>: ")
                fragment_size = int(user_input)

                user_input = input("Implement error into the sending process (y/n)? ")
                while user_input != 'y' and user_input != 'n':
                    user_input = input("Implement error into the sending process (y/n)? ")
                
                implement_error = 1 if user_input == 'y' else 0
                message = input("Input you text that you want to send: \n")
                fragment_list = fragment_text(message,fragment_size)
                print_sender_info(False,fragment_list)
                self.stop_keep_alive.set()
                send_fragments(self.send_sock, (self.destination_ip, self.destination_port), fragment_list, Flags.SENDING_TEXT, implement_error)
                self.stop_keep_alive.clear()
                

            elif user_input == "file" or user_input == 'f':
                user_input = input("Input the desired size of fragment, whole number <1,1465>: ")
                while not user_input.isnumeric() or (int(user_input) > self.MAX_FRAGMENT_SIZE or int(user_input) <= 0): 
                    user_input = input("Input the desired size of fragment, whole number <1,1465>: ")
                fragment_size = int(user_input)

                user_input = input("Implement error into the sending process (y/n)? ")
                while user_input != 'y' and user_input != 'n':
                    user_input = input("Implement error into the sending process (y/n)? ")
                implement_error = 1 if user_input == 'y' else 0
                
                file_path = input("Input path to file you want to send: ")
                while not os.path.exists(file_path) or not os.path.isfile(file_path):
                    print("Given path leads to nothing or a directory!")
                    file_path = input("Input path to file you want to send: ")
                fragment_list = fragment_file(file_path,fragment_size)
                self.stop_keep_alive.set()
                send_fragments(self.send_sock, (self.destination_ip, self.destination_port), fragment_list, Flags.SENDING_FILE, implement_error)
                print_sender_info(True,fragment_list)
                self.stop_keep_alive.clear()

        
        self.stop_keep_alive.set()
        send_system_message(self.send_sock, (self.destination_ip, self.destination_port), 0, 0, Flags.KILL)


    def begin(self):
        receiver = threading.Thread(target=self.receiver)
        receiver.start()

        sender = threading.Thread(target=self.sender)
        sender.start()

        sender.join()
        receiver.join()
        os._exit(0)

if __name__ == "__main__":
    """
    p1_testing_conn_string = 127.0.0.1::12341::127.0.0.1::12342
    p2_testing_conn_string = 127.0.0.1::12341::127.0.0.1::12342
    rene_testing = 169.254.153.150::12341::169.254.153.151::12342
    pedro_testing = 169.254.153.151::12342::169.254.153.152::12341

    """

    #connection_string = input("Please input the connection string in format (local_ip::local_port::dest_ip::dest_port):\n")
    connection_string = "169.254.153.150::12341::169.254.153.151::12342"
    connection_string = connection_string.split('::')
    peer = PEER(connection_string[0], int(connection_string[1]), connection_string[2], int(connection_string[3]))
    peer.begin()
