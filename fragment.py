import socket
import struct
from flags import Flags
from binascii import crc_hqx

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


def send_system_message(src_socket : socket.socket, dest : tuple, seq_num : int, crc16 : int, flag : int):
    temp_header = create_header(seq_num, crc16, flag)
    crc16 = crc_hqx(temp_header, 0xFFFF)        
    src_socket.sendto(create_header(seq_num,crc16,flag), dest)


def fragment_text(text : str, fragment_size : int):
    fragment_list : list = []
    for i in range(0, len(text), fragment_size):
        fragment_list.append( text[ i:i + fragment_size ] )
    return fragment_list


def send_text_fragments(src_socket : socket.socket, dest : tuple, fragment_list : list):
    for seq_num, fragment in enumerate(fragment_list, start = 0):
        if seq_num == len(fragment_list) - 1:
            crc16 = crc_hqx(create_header(seq_num,0,Flags.LAST_TEXT_FRAGMENT), 0xFFFF)
            header = create_header(seq_num, crc16, Flags.LAST_TEXT_FRAGMENT)
        else:
            crc16 = crc_hqx(create_header(seq_num,0,Flags.SENDING_TEXT), 0xFFFF)
            header = create_header(seq_num, crc16, Flags.SENDING_TEXT)
        segment = header + fragment.encode('utf-8')
        src_socket.sendto(segment, dest)
    return seq_num