'''
D-STAR の自動応答局の中の人を生成AIにやってもらおう！
Title: dstar_auto_ai_replyer
Description: 

Author: 7M4MON
Date: 2024/10/1 初版
'''

import pyaudio, wave, serial, time, json, os, dstar_comm, openai_function, subprocess
from datetime import datetime
from pydub import AudioSegment
from pydub.playback import play
from openai import OpenAI

client = OpenAI(api_key = os.environ['OPENAI_API_KEY'])

# 設定ファイルの読み込み
settings_json = open('./settings.json' , 'r' , encoding="utf-8")
settings_dict = json.load(settings_json) 
data_path = "./data/"

# Wavファイルのフォーマット
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
audio = pyaudio.PyAudio()
RATE = 24000

# 受信状態をポーリングしつつ、受信音声を録音する。
def record_audio(input_device_idx:int, max_length:float, ser:serial, civ_addr:str = 'a4'):
    # 音の取込開始
    stream = audio.open(format = FORMAT,
        channels = CHANNELS,
        rate = RATE,
        input = True,
        frames_per_buffer = CHUNK,
        input_device_index = input_device_idx
        )
    frames = []
    record_length = 0
    while(dstar_comm.get_dvrx_state(ser, civ_addr) == True and record_length < max_length):
        # 音データの取得
        data = stream.read(CHUNK)
        frames.append(data)
        time.sleep(0.01)
        record_length += 0.01
    return frames, record_length

# waveファイルを保存する。
def save_wave_file(frames, file_name:str):
    wave_file_name = file_name + "_rx.wav"
    print(wave_file_name)
    wav = wave.open(wave_file_name, 'wb')
    wav.setnchannels(CHANNELS)
    wav.setsampwidth(audio.get_sample_size(FORMAT))
    wav.setframerate(RATE)
    wav.writeframes(b''.join(frames))
    wav.close()
    return wave_file_name

# スペースの前までを返す
def get_string_before_space(s):
    # スペースが含まれているか確認し、あればその位置までの文字列を返す
    if ' ' in s:
        return s.split(' ')[0]
    else:
        return s  # スペースがなければ元の文字列を返す

# 自動応答局本体
def auto_replyer():
    try :
        # 設定値のロード
        comport = settings_dict['comport']
        record_length_max = float(settings_dict['max_rec_sec'])
        record_length_min = float(settings_dict['min_rec_sec'])
        input_device_idx = settings_dict['input_device_idx']
        civ_addr = settings_dict['civ_addr']
        callsign_pronuc = settings_dict['callsign_pronuc']
        my_callsign = settings_dict['my_callsign']
        my_callsign_memo = settings_dict['my_callsign_memo']
        rpt1_callsign = settings_dict['rpt1_callsign']
        rpt2_callsign = settings_dict['rpt2_callsign']

        ser = serial.Serial(comport, 115200, timeout=None)
        dstar_comm.set_my_callsign(ser, my_callsign, my_callsign_memo, civ_addr)
        
        print("Initialized\n")
        while True:
            # 受信待ち
            while(dstar_comm.get_dvrx_state(ser, civ_addr) == False):
                time.sleep(0.01)
            print("Recording Start")
            frames, record_length = record_audio(input_device_idx, record_length_max, ser, civ_addr)
            print("Recording Stop")
      
            # 十分な長さがあり、タイムアウト以外の条件で録音データをファイルに保存
            if(record_length < record_length_max and record_length > record_length_min):
                now_string = datetime.now().strftime('%Y%m%d-%H%M%S')
                file_name = data_path + now_string
                wave_file_name = save_wave_file(frames, file_name)

                # wisperに渡して文字起こしする
                try:
                    what_rx = openai_function.speech_to_text(client, wave_file_name)
                    print("what_say:" + what_rx)
                    rxTxtFilename = file_name + "_rx.txt" # ログを記録
                    with open(rxTxtFilename, 'w') as f:
                        f.write(what_rx)

                    # 文字起こしした内容を ChatGPT に渡す
                    what_tx = openai_function.chat_with_gpt(client, mycallsign = callsign_pronuc, prompt = what_rx)
                    print("reply:" + what_tx)
                    txTxtFilename = file_name + "_tx.txt" # ログを記録
                    with open(txTxtFilename, 'w') as f:
                        f.write(what_tx)
                except Exception as e:
                    print("AIE" + str(e))
                    what_tx = "エラーが発生しました。"

                try:
                    # 無線機から直前に受信したコールサインを取得する
                    rx_callsign = dstar_comm.get_rx_callsign(ser, civ_addr)
                    dstar_comm.set_ur_callsign(ser, ur_callsign = rx_callsign, rpt1_callsign = rpt1_callsign, rpt2_callsign = rpt2_callsign, civ_addr = civ_addr)
            
                    # レスポンスの音声ファイルを作成
                    tx_mp3_filename = file_name + '_' + rx_callsign +"_tx.mp3"
                    reply = get_string_before_space(rx_callsign) + "局" + "、こんにちは。" + "こちらは " + callsign_pronuc + "です。" + what_tx
                    openai_function.make_response_voice(client, reply, tx_mp3_filename)

                    # 送信開始
                    dstar_comm.set_transmit(ser, tx = True,  civ_addr = civ_addr)
                    time.sleep(0.3)
                    # MP3ファイルを読み込んで再生
                    sound = AudioSegment.from_mp3(tx_mp3_filename)
                    play(sound)
                    # 送信停止
                    time.sleep(0.3)
                    dstar_comm.set_transmit(ser, tx = False,  civ_addr = civ_addr)
                except Exception as e:
                    print("TRE " + str(e))
                          
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        pass

    except Exception as e:
        print(e)

    finally:
        audio.terminate()
        ser.close()
        with open('log.txt', 'a') as f:
            print(datetime.now().strftime('%Y%m%d-%H%M%S'), file=f)
        subprocess.Popen("restart.bat")        # 10秒で再起動する。
        # end of receive()


auto_replyer()

