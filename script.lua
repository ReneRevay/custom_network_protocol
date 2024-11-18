local RSSP = Proto("RSSP", "Rene Secret Service Protocol")

local seq_num = ProtoField.uint32("RSSP.seq_num", "Seq_num", base.DEC)
local crc = ProtoField.uint16("RSSP.crc", "crc16", base.DEC)
local flags = ProtoField.uint8("RSSP.flags", "Flags", base.DEC)
local data = ProtoField.bytes("RSSP.data", "Data")

RSSP.fields = { seq_num, crc, flags, data }

-- Coloring has been applied in wireshark 

function RSSP.dissector(buffer, pinfo, tree)
    pinfo.cols.protocol = RSSP.name

    local subtree = tree:add(RSSP, buffer(), "RSSP Protocol Data")

    local seq_num_val = buffer(0, 4)
    local crc_val = buffer(4, 2)
    local flags_val = buffer(6, 1):uint()
    local data_length = buffer:len() - 7

    subtree:add(seq_num, seq_num_val)
    subtree:add(crc, crc_val)

    -- GPT idea 
    local flag_to_string = {
        [1] = "SYN",
        [2] = "ACK",
        [4] = "NACK",
        [8] = "KILL",
        [16] = "KEEP_ALIVE",
        [32] = "SENDING_TEXT",
        [33] = "SENDING_FILE",
        [128] = "LAST_TEXT_FRAGMENT",
        [129] = "LAST_FILE_FRAGMENT",
    }

    local flags_str = flag_to_string[flags_val] or "Flags: UNKNOWN"
    subtree:add(flags, buffer(6, 1)):append_text(" (" .. flags_str .. ")")

    if data_length > 0 then
        local data_val = buffer(7, data_length)
        subtree:add(data, data_val)
    end
end

local udp_port_table = DissectorTable.get("udp.port")
udp_port_table:add(12341, RSSP)
udp_port_table:add(12342, RSSP)
