import os
import socket
import struct
from flags import Flags
from binascii import crc_hqx


#def print_text_dialog():
#def print_file_dialog():
#def print_end_text_dialog():
#def print_end_file_dialog():


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


def create_header(seq_num, crc16, flags):
    return struct.pack('!IHB', seq_num, crc16, flags)


def unpack_received_data(whole_data : bytes) -> dict:
    header = whole_data[:7]
    seq_num, crc16, flag = struct.unpack("!IHB", header)
    return_dict = {
        "header" : header,
        "seq_num" : seq_num,
        "crc" : crc16,
        "flag" : flag,
        "data" : whole_data[7:]
    }
    return return_dict


def send_system_message(src_socket : socket.socket, dest : tuple, seq_num : int, crc16 : int, flag : int) -> None:
    temp_header = create_header(seq_num, crc16, flag)
    crc16 = crc_hqx(temp_header, 0xFFFF)        
    src_socket.sendto(create_header(seq_num,crc16,flag), dest)


def fragment_text(text : str, fragment_size : int) -> list:
    fragment_list : list = []
    for i in range(0, len(text), fragment_size):
        fragment_list.append( text[ i:i + fragment_size ] )
    return fragment_list


def fragment_file(file_path : str, fragment_size : int) -> list:
    fragment_list = []
    with open(file_path, 'rb') as file:
        while True:
            fragment = file.read(fragment_size)
            if not fragment:
                break
            fragment_list.append(fragment)
    return fragment_list

def send_text_fragments(src_socket : socket.socket, dest : tuple, fragment_list : list) -> None:
    for seq_num, fragment in enumerate(fragment_list, start = 0):
        if seq_num == len(fragment_list) - 1:
            crc16 = crc_hqx(create_header(seq_num,0,Flags.LAST_TEXT_FRAGMENT) + fragment.encode('utf-8'), 0xFFFF)
            header = create_header(seq_num, crc16, Flags.LAST_TEXT_FRAGMENT)
        else:
            crc16 = crc_hqx(create_header(seq_num,0,Flags.SENDING_TEXT) + fragment.encode('utf-8'), 0xFFFF)
            header = create_header(seq_num, crc16, Flags.SENDING_TEXT)
        
        segment = header + fragment.encode('utf-8')
        src_socket.sendto(segment, dest)


def send_file_fragments(src_socket : socket.socket, dest : tuple, fragment_list : list) -> None:
    for seq_num, fragment in enumerate(fragment_list, start=0):  
        if seq_num == len(fragment_list) - 1:
            crc16 = crc_hqx(create_header(seq_num,0,Flags.LAST_FILE_FRAGMENT) + fragment, 0xFFFF)
            header = create_header(seq_num, crc16, Flags.LAST_FILE_FRAGMENT)
        else:
            crc16 = crc_hqx(create_header(seq_num,0,Flags.SENDING_FILE) + fragment, 0xFFFF)
            header = create_header(seq_num, crc16, Flags.SENDING_FILE)
        
        segment = header + fragment
        src_socket.sendto(segment, dest)


def save_received_file(save_folder_path : str, file_fragments : list, file_name : str, file_extension : str) -> None:
    file_size : int = 0 
    complete_file_name : str = f"{file_name}.{file_extension}"
    save_path : str = os.path.join(save_folder_path, complete_file_name)
    
    with open(save_path, 'wb') as file:
        for fragment in file_fragments:
            file_size += len(fragment)
            file.write(fragment)
    
    print(f"File {complete_file_name} ( {file_size}B ) successfully saved to {save_path}")