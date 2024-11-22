class Flags:
    SYN =                0b00000001
    ACK =                0b00000010
    NACK =               0b00000100
    KILL =               0b00001000
    KEEP_ALIVE =         0b00010000
    SENDING_TEXT =       0b00100000
    SENDING_FILE =       0b00100001
    LAST_TEXT =          0b10000000
    LAST_FILE =          0b10000001