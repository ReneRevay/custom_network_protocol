import socket
import threading
import struct
import time
import random

# FLAGS:
# S - syn  -  handshake
# A - ack  -  handshake
# V - verify   -  keep-alive
# L - last fragment  -  recieve segments until this flag arrives
# K - kill connection  -  for ending and closing connections between peers
# C - corrupted  -  if file arrives damaged, respond with this flag and request that flag again
# F - sending file  -  data is to be interpreted as a file
# T - sending text  -  data is to be interpreted as text

# * Add full functionality of seq and ack nums
# TODO implement kill connection flag to cancel the program like normal human beeing and not killing it every time 
# TODO implement keep alive 
# TODO implement crc16


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))  # random IP just to send a packet
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class PEER:
    def __init__(self, local_ip, reciever_port, sender_port, dest_ip, dest_port):
        self.local_ip = local_ip
        self.reciever_port = reciever_port
        self.sender_port = sender_port
        self.destination_ip = dest_ip
        self.destination_port = dest_port

        self.SYN  =  0b10000000
        self.ACK  =  0b01000000
        self.VER  =  0b00100000
        self.LAST =  0b00010000
        self.KILL =  0b00001000
        self.COR  =  0b00000100
        self.FILE =  0b00000010
        self.TEXT =  0b00000001

        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_sock.bind((self.local_ip, self.sender_port))
        self.recv_sock.bind((self.local_ip, self.reciever_port))

    def create_header(self, seq_num, ack_num, batch, sum, flags):
        return struct.pack('!HHBHB', seq_num, ack_num, batch, sum, flags)

    def send_message(self, seq_num, ack_num, batch, sum, flags, data):
        header = self.create_header(seq_num, ack_num, batch, sum, flags)
        segment = header + data.encode('utf-8')
        self.send_sock.sendto(segment, (self.destination_ip, self.destination_port))

    def sender(self, data):
        print("starting sender")
        done_handshake = False

        seq_num = random.randint(0,128)
        ack_num = 0
        batch = 1
        crc16 = 0
        
        if not done_handshake:
            while True:
                print("HandShake not done, Let's do it! Sending SYN.")
                header = self.create_header(seq_num, ack_num, batch, crc16, self.SYN)
                self.send_sock.sendto(header, (self.destination_ip, self.destination_port))
                try:
                    self.send_sock.settimeout(1.0) # Waiting a specific amount of time to get ACK
                    whole_data, client = self.send_sock.recvfrom(1024)
                    header = whole_data[:8]
                    seq_num, ack_num, batch, crc16, self.flags = struct.unpack("!HHBHB", header)
                    seq_num = ack_num
                    ack_num = 0
                    if self.flags == self.ACK:
                        print("ACK arrived, it's done!")
                        self.done_handshake = True
                        break
                except socket.timeout:
                    print("ACK didn't arrive in time!")
                    continue

        while data != "end":
            self.send_message(seq_num,ack_num,batch,crc16,self.LAST,data) #for now there is LAST flag as a default
            # add a portion of code to recieve a ack response from sender and print out the content of header, this may be the fix for the not changing seq and ack nums
            data = input("Data to be sent: ")
        self.send_sock.close()
        self.recv_sock.close()

    def receiver(self):
        print("Starting receiver")

        seq_num = 0
        ack_num = 0
        batch = 1
        crc16 = 0

        while True:
            whole_data, client = self.recv_sock.recvfrom(1024)
            header = whole_data[:8]
            seq_num, ack_num, batch, crc16, self.flags = struct.unpack("!HHBHB", header)
            ack_num = seq_num + 1
            seq_num = 0
            data = whole_data[8:]

            if self.flags == self.SYN:
                print("SYN arrived for handshake, sending ACK")
                header = self.create_header(seq_num, ack_num, batch, crc16, self.ACK)
                self.recv_sock.sendto(header, client)

            print(f"Received message: {data.decode()} from {client}")
            print(f"Header details : seq_num: {seq_num}, ack_num: {ack_num}, batch: {batch}, sum: {crc16}, flags: {self.flags}")


    def begin(self):
        receiver = threading.Thread(target=self.receiver,daemon=True)
        receiver.start()
        
        data = input("Input data to be sent: ")
        if data:
            sender = threading.Thread(target=self.sender, args=(data,),daemon=True)
            sender.start()
            sender.join()
        
        receiver.join()

if __name__ == "__main__":
    #local_ip = get_ip()
    local_ip = "127.0.0.1"
    reciever_port = int(input("Input the port you are listening on: "))
    sender_port = int(input("Enter port, from which you will be sending: "))
    destination_ip = input("Input the IP of the host: ") or "127.0.0.1"
    destination_port = int(input("Input the host's reciever port: "))
    peer = PEER(local_ip, reciever_port, sender_port, destination_ip, destination_port)
    peer.begin()
