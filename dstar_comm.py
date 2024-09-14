'''
D-STARの自動応答局で使用する無線機制御プログラムです。
dstar_auto_ai_replyer.py から呼び出されます。
IC-705とIC-9700で動作確認しています。
date: 2024.9
author: 7M4MON
'''

import serial, time


MY_CALLSIGN = "7M4MON P"
UR_CALLSIGN = "JM1ZLK"
RPT1_CALLSIGN = "7M4MON Z"
RPT2_CALLSIGN = "7M4MON G"

CIV_ADDR = 'a4'             # 'a4' = IC-705, 'a2' = IC-9700
CMD_PRE = "fefe"
CMD_PC_ADDR = "e0"
CMD_POST = "fd"
CMD_MYSET = "1f00"
CMD_URSET = "1f01"
CMD_LASTRX = "200002"
CMD_DVRX_STATE = "200202"
CMD_TX = "1c00"

CIV_WAIT_TIME = 0.02

DEBUG = False

# 文字列を 8文字 (or 任意数) に調整する
def pad_or_trim_string(s, length = 8):
    return s.ljust(length)[:length]

# 特定の文字列の次の文字列を文字数分返す
# USBエコーバック ON/OFF で バイトの位置が変わるため。
def find_next_chars(s:str, target:str, offset:int = 0, length:int = 2):
    # 対象文字列が存在する位置を探す
    index = s.find(target)
    if DEBUG:
        print('s:' +s)
        print('t:' +target)
        print('i:'+ str(index))
    # ヒットした場合、その次+オフセットの文字を指定文字だけ返す
    if index != -1 and (index + offset + length) < len(s):
        r = s[index + offset + len(target):index + len(target) + length + offset]
        # print('found ' + target + ' in ' + str(index) + ' : ' + r)
        return r
    else:
        print('fnc not found')
        return None

# hexの文字列からasciiの文字列に変換する
def convert_string_to_ascii(s:str):
    try:
        # ステップ1: 文字列 "3130" を byte 型に変換 (16進数の文字列として)
        byte_data = bytes.fromhex(s)
        # ステップ2: byteデータをデコードしてASCII表現にする
        ascii_rep = byte_data.decode('ascii')
        
        # 結果: ASCII文字列 "10" が得られる
        return ascii_rep
    except Exception as e: # ascii の範囲外があるのでcatchする
        print('s:' + s)
        print(f"ascii convert error : {e}")
        return None

# 自局のコールサイン MY + MEMO をセットする
def set_my_callsign(ser:serial, my_callsign = MY_CALLSIGN, my_callsign_memo = '    ', civ_addr = CIV_ADDR):
    set_callsign_str =  pad_or_trim_string(my_callsign)
    set_callsign_str += pad_or_trim_string(my_callsign_memo, 4)
    # ASCII文字列をバイト列に変換
    byte_data = set_callsign_str.encode('ascii')
    hex_string = ''.join(f'{b:02x}' for b in byte_data)
    send_cmd = CMD_PRE + civ_addr + CMD_PC_ADDR + CMD_MYSET + hex_string + CMD_POST
    print("MY_SET: " + my_callsign + '/' + my_callsign_memo + '\n')
    byte_cmd = bytes.fromhex(send_cmd)
    s = ser.write(byte_cmd)
    time.sleep(CIV_WAIT_TIME)
    # シリアルポートからデータを読み取って捨てる
    read_data = ser.read_all()
    return True

# 宛先のコールサイン UR をセットする
def set_ur_callsign(ser:serial, ur_callsign = UR_CALLSIGN, rpt1_callsign = RPT1_CALLSIGN, rpt2_callsign = RPT2_CALLSIGN, civ_addr = CIV_ADDR):
    set_callsign_str =  pad_or_trim_string(ur_callsign) + rpt1_callsign + rpt2_callsign
    # ASCII文字列をバイト列に変換
    byte_data = set_callsign_str.encode('ascii')
    hex_string = ''.join(f'{b:02x}' for b in byte_data)
    send_cmd = CMD_PRE + civ_addr + CMD_PC_ADDR + CMD_URSET + hex_string + CMD_POST
    print("UR_SET:" + ur_callsign + '\n')
    byte_cmd = bytes.fromhex(send_cmd)
    s = ser.write(byte_cmd)
    time.sleep(CIV_WAIT_TIME)
    # シリアルポートからデータを読み取って捨てる
    read_data = ser.read_all()
    return True

# 最後に受信したコールサインを読み込む
def get_rx_callsign(ser:serial, civ_addr = CIV_ADDR):
    cmd = CMD_PRE + civ_addr + CMD_PC_ADDR + CMD_LASTRX + CMD_POST
    #print('cmd:' + cmd)
    byte_cmd = bytes.fromhex(cmd)
    s = ser.write(byte_cmd)
    time.sleep(CIV_WAIT_TIME)
    # シリアルポートからデータを読み取る
    read_data = ser.read_all() 
    #print('rx:' + read_data.hex())
    rx_callsign = convert_string_to_ascii(find_next_chars(read_data.hex(), CMD_PC_ADDR + civ_addr + CMD_LASTRX, 4, 16))
    if rx_callsign != None:
        print ("RX_CALLSIGN:" + rx_callsign)
        return rx_callsign
    else:
        print ("RX_CALLSIGN is Nothing")
        return '        '

# DV受信ステータスデータを読み取る
def get_dvrx_state(ser:serial, civ_addr = CIV_ADDR):
    cmd = CMD_PRE + civ_addr + CMD_PC_ADDR + CMD_DVRX_STATE + CMD_POST
    #print('cmd:' + cmd)
    byte_cmd = bytes.fromhex(cmd)
    s = ser.write(byte_cmd)
    time.sleep(CIV_WAIT_TIME)
    # シリアルポートからデータを読み取る
    read_data = ser.read_all()
    # コマンドの次の文字を探す
    state_hex = find_next_chars(read_data.hex(), CMD_PC_ADDR + civ_addr + CMD_DVRX_STATE, length = 2)
    # バイト列を文字列にデコード
    # print ('dvrx_state : ' + state_hex + "\n")
    dvrx_state = True if state_hex == '50' else False
    return dvrx_state

# 送信状態にする
def set_transmit(ser:serial, civ_addr:str = CIV_ADDR, tx:bool = False):
    s = '00'
    if tx : s = '01'
    print("tx:" + s + '\n')
    cmd =  CMD_PRE + civ_addr + CMD_PC_ADDR + CMD_TX + s + CMD_POST
    byte_cmd = bytes.fromhex(cmd)
    s = ser.write(byte_cmd)
    time.sleep(CIV_WAIT_TIME)
    # シリアルポートからデータを読み取って捨てる
    read_data = ser.read_all()
    return True


# 単体テスト
def dstar_comm_test():
    ser = serial.Serial()
    ser.port = 'COM12'
    ser.baudrate = 115200
    ser.timeout = 1
    try:
        ser.open()      
        #set_my_callsign(ser, '7M4MON D', 'TEST')
        #set_ur_callsign(ser, '7M4MON E', 'JP1YIU A', 'JP1YIU G')
        #print(str(get_rx_callsign(ser)))
        #print(str(get_dvrx_state(ser)))
        #set_transmit(ser, tx = False)
        ser.close()
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")

#dstar_comm_test()