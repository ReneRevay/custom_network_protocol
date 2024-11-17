import os
import socket
import struct
import random
from flags import Flags
from binascii import crc_hqx


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


def print_initial_dialog():
    print("\nDo you want to send something?\n-yes/y : continue to specify your sending parameters \n-exit/e : quit this application")

def print_sender_info(transfered_file : bool, fragment_list : list):
    data_size = 0
    if transfered_file :
        for f in fragment_list[1:]: data_size += len(f)
    else:
        for f in fragment_list: data_size += len(f)
    if transfered_file : file_name = fragment_list[0].decode().split('/')[-1]
    fragment_count = len(fragment_list)-1 if transfered_file else len(fragment_list)
    
    print("------------------------------------------------")
    if transfered_file : print(f"Name of transfered file : {file_name}")
    print(f"Size of data to transfer : {data_size}B")
    print(f"Count of fragments to send : {fragment_count} fragmetns")
    print(f"Size of fragments : {len(fragment_list[1])}B")
    if len(fragment_list[1]) != len(fragment_list[-1]) : print(f"Size of last fragment : {len(fragment_list[-1])}B")
    print("------------------------------------------------")
    
def print_receiver_info(transfered_file : bool, time_to_transfer, fragment_list : list):
    received_text = ""
    data_size = 0
    if transfered_file :
        for f in fragment_list[1:]: data_size += len(f)
    else:
        for f in fragment_list: 
            data_size += len(f)
            received_text += f.decode()
    
    print("------------------------------------------------")
    print(f"File received successfully!") if transfered_file else print(f"Text received successfully!") 
    if transfered_file: print(f"Name of received file : {fragment_list[0].decode().split('/')[-1]}")
    if transfered_file: print(f"Save location of file : downloads/{fragment_list[0].decode().split('/')[-1]}")
    if not transfered_file: print(f"Received text : {received_text}")
    print(f"Data received in : {time_to_transfer:.2f}s")
    print(f"Size of received data : {data_size}B")
    print("------------------------------------------------")
    


def create_header(seq_num, crc16, flags):
    return struct.pack('!IHB', seq_num, crc16, flags)


def unpack_received_data(whole_data : bytes) -> dict:
    header : bytes = whole_data[:7]
    seq_num, crc16, flag = struct.unpack("!IHB", header)
    return_dict : dict = {
        "seq_num" : seq_num,
        "crc" : crc16,
        "flag" : flag,
        "data" : whole_data[7:]
    }
    return return_dict


def send_system_message(src_socket : socket.socket, dest : tuple, seq_num : int, crc16 : int, flag : int) -> None:
    temp_header : bytes = create_header(seq_num, crc16, flag)
    crc16 : int = crc_hqx(temp_header, 0xFFFF)        
    src_socket.sendto(create_header(seq_num,crc16,flag), dest)


def fragment_text(text : str, fragment_size : int) -> list:
    fragment_list : list = []
    for i in range(0, len(text), fragment_size):
        fragment_list.append( text[ i:i + fragment_size ] )
    return fragment_list


def fragment_file(file_path : str, fragment_size : int) -> list:
    fragment_list : list = []
    fragment_list.append(file_path.encode('utf-8'))

    with open(file_path, 'rb') as file:
        while True:
            fragment = file.read(fragment_size)
            if not fragment:
                break
            fragment_list.append(fragment)
    return fragment_list


def send_fragments(src_socket : socket.socket, dest : tuple, fragment_list : list, flag : int, implement_error : bool) -> None:
    nack_count : int = 0
    sent_fragment_counter : int = 0
    random_message_to_corrupt : int = random.randint(0,len(fragment_list))
    error_occured : bool = False

    while sent_fragment_counter < len(fragment_list):
        fragment = fragment_list[sent_fragment_counter]

        if sent_fragment_counter == len(fragment_list) - 1:
            if flag == Flags.SENDING_FILE:
                crc16 = crc_hqx(create_header(sent_fragment_counter,0,Flags.LAST_FILE_FRAGMENT) + fragment, 0xFFFF)
                if random_message_to_corrupt == sent_fragment_counter and implement_error and not error_occured:
                    crc16 = crc16 - 123 # to cause a missmatch, thus error will occur
                    error_occured = True
                header = create_header(sent_fragment_counter, crc16, Flags.LAST_FILE_FRAGMENT)
            else:
                crc16 = crc_hqx(create_header(sent_fragment_counter,0,Flags.LAST_TEXT_FRAGMENT) + fragment.encode('utf-8'), 0xFFFF)
                if random_message_to_corrupt == sent_fragment_counter and implement_error and not error_occured:
                    crc16 = crc16 - 123 # to cause a missmatch, thus error will occur
                    error_occured = True
                header = create_header(sent_fragment_counter, crc16, Flags.LAST_TEXT_FRAGMENT)
        else:
            if flag == Flags.SENDING_FILE:
                crc16 = crc_hqx(create_header(sent_fragment_counter,0,flag) + fragment, 0xFFFF)
            else: 
                crc16 = crc_hqx(create_header(sent_fragment_counter,0,flag) + fragment.encode('utf-8'), 0xFFFF)
            
            if random_message_to_corrupt == sent_fragment_counter and implement_error and not error_occured:
                crc16 = crc16 - 123 # to cause a missmatch, thus error will occur
                error_occured = True
            header = create_header(sent_fragment_counter, crc16, flag)
        
        if flag == Flags.SENDING_FILE:
            segment = header + fragment
        else:
            segment = header + fragment.encode('utf-8')

        src_socket.sendto(segment, dest)
        
        try:
            src_socket.settimeout(5)
            whole_data, _ = src_socket.recvfrom(1465)
            data = unpack_received_data(whole_data)
            if data["flag"] == Flags.ACK:
                sent_fragment_counter += 1
                nack_count = 0
            if data['flag'] == Flags.NACK:
                continue
        except Exception:
            nack_count += 1
            if nack_count == 3:
                print("Host responding. Connection dead!")
                os._exit(0)
        finally:
            src_socket.settimeout(None)


def save_received_file(file_fragments : list) -> None:
    file_name : str = file_fragments[0].decode().split('/')[-1]
    file_fragments : list = file_fragments[1:]

    if not os.path.exists("downloads"): 
        os.makedirs("downloads")

    save_path : str = os.path.join("downloads", file_name)

    with open(save_path, 'wb') as file:
        for fragment in file_fragments:
            file.write(fragment)

    
    