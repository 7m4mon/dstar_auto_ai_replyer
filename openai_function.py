'''
Open AI 社のAPIアクセスプログラムです。API経由で 文字起こし、Chat、音声合成 を行います。
client を各関数に渡してください。
'''

from openai import OpenAI
import os, random

# client = OpenAI(api_key = os.environ['OPENAI_API_KEY'])

# 音声合成
def make_response_voice(client:OpenAI, tts_content:str, filename:str):
    voice_list = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]
    voice_choice = random.choice(voice_list)
    print("話者:" + voice_choice)
    with client.audio.speech.with_streaming_response.create(
        model='tts-1',        # tts-1 or tts-1-hd
        voice=voice_choice,
        input=tts_content
    )as response:
        response.stream_to_file(filename)
    return filename

# 応答作成
def chat_with_gpt(client:OpenAI, mycallsign:str, prompt:str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "あなたは" + mycallsign + "というアマチュア無線局です。アマチュア無線の交信相手として140字以内で応答しなさい。"},
                  {"role": "user", "content": prompt}],
    )
    r = response.choices[0].message.content
    if len(r) > 200 : r = r[:200]
    return r

# 文字起こし（引数：音声ファイルパス）
def speech_to_text(client:OpenAI, filepath:str):
    # ファイルサイズを確認 25MB以下
    if os.path.getsize(filepath) > 25000000:
        print("file size over")
        return
    audio_file= open(filepath, "rb")
    # Speech to Text変換
    response = client.audio.transcriptions.create(model="whisper-1", file=audio_file, response_format="text")
    # 変換後のテキスト出力
    return response
