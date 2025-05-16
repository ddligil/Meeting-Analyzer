import tkinter as tk
from tkinter import messagebox
import sounddevice as sd
import numpy as np
import wave
import os
import threading
from openai import OpenAI
from dotenv import load_dotenv
import tempfile
import json
from datetime import datetime

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

fs = 44100
recording = False
recorded_data = []
segment_folder = "segments"
os.makedirs(segment_folder, exist_ok=True)

def start_recording():
    global recording, recorded_data
    recording = True
    recorded_data = []

    def callback(indata, frames, time, status):
        if recording:
            recorded_data.append(indata.copy())

    def record_thread():
        with sd.InputStream(samplerate=fs, channels=1, dtype='float32', callback=callback):
            while recording:
                sd.sleep(100)

    threading.Thread(target=record_thread, daemon=True).start()

def stop_recording():
    global recording, recorded_data
    recording = False

    if not recorded_data:
        messagebox.showerror("Hata", "Hiç ses verisi alınamadı.")
        return

    audio_data = np.concatenate(recorded_data, axis=0)
    audio_data = (audio_data * 32767).astype(np.int16)

    index = len(os.listdir(segment_folder)) + 1
    filename = os.path.join(segment_folder, f"segment_{index}.wav")

    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(fs)
        wf.writeframes(audio_data.tobytes())

    messagebox.showinfo("Kayıt", f"Segment kaydedildi: {filename}")

def transcribe_all():
    segment_paths = sorted([
        os.path.join(segment_folder, f)
        for f in os.listdir(segment_folder)
        if f.endswith(".wav")
    ])

    if not segment_paths:
        messagebox.showerror("Hata", "Hiç segment bulunamadı.")
        return

    combined_path = tempfile.NamedTemporaryFile(delete=False, suffix=".wav").name
    frames = []

    for path in segment_paths:
        with wave.open(path, 'rb') as wf:
            frames.append(wf.readframes(wf.getnframes()))

    with wave.open(combined_path, 'wb') as wf_out:
        wf_out.setnchannels(1)
        wf_out.setsampwidth(2)
        wf_out.setframerate(fs)
        wf_out.writeframes(b''.join(frames))

    with open(combined_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="tr"
        )

    text = transcript.text
    analysis = analyze_meeting(text)

    
    messagebox.showinfo("Transkript", text[:1000] + ("..." if len(text) > 1000 else ""))
    messagebox.showinfo("Toplantı Özeti", json.dumps(analysis, ensure_ascii=False, indent=4))

    with open("kararlar.txt", "w", encoding="utf-8") as file:
        file.write(json.dumps(analysis, ensure_ascii=False, indent=4))

    for path in segment_paths:
        os.remove(path)
    os.remove(combined_path)

def analyze_meeting(transcript: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "Sen bir üst düzey toplantı analizcisisin. "
                    "Görevin, verilen Türkçe toplantı transkriptinden aşağıdaki bilgileri çıkarmaktır:\n\n"
                    "1. Katılımcılar (isim ve unvan)\n"
                    "2. Alınan Kararlar: Karar kelimesi geçmese bile toplantının sonucunda verilen net eylem planlarını karar olarak değerlendir. "
                    "Tarih ve görev içeren tüm ifadeleri buraya yaz.\n"
                    "3. Paylaşılan Bilgiler (örnek: sunumlar, raporlar, veriler)\n"
                    "4. Belirtilen Sorunlar veya Katılımcı Görüşleri\n"
                    "5. Sonraki Toplantı: Tarih, saat veya gündem belirtildi mi?\n\n"
                    "Çıktıyı aşağıdaki gibi tek katmanlı JSON olarak ver:\n"
                    "{\n"
                    "  'Katılımcılar': ...,\n"
                    "  'Alınan Kararlar': ...,\n"
                    "  'Paylaşılan Bilgiler': ...,\n"
                    "  'Belirtilen Sorunlar': ...,\n"
                    "  'Sonraki Toplantı': ...\n"
                    "}\n\n"
                    "Eğer bilgi eksikse 'Belirtilmedi' yaz. Çıktıda sadece JSON nesnesi olsun, açıklama veya etiketleme yapma."
                )
            },
            {"role": "user", "content": f"Toplantı transkripti:\n{transcript}"}
        ]
    )

    reply = response.choices[0].message.content
    return {
        "Tarih": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Katılımcılar": extract(reply, "Katılımcılar"),
        "Alınan Kararlar": extract(reply, "Alınan Kararlar"),
        "Paylaşılan Bilgiler": extract(reply, "Paylaşılan Bilgiler"),
        "Belirtilen Sorunlar": extract(reply, "Belirtilen Sorunlar"),
        "Sonraki Toplantı": extract(reply, "Sonraki Toplantı")
    }

def extract(text, keyword):
    for line in text.split("\n"):
        if keyword in line:
            return line.split(":", 1)[-1].strip()
    return "Belirtilmedi"

root = tk.Tk()
root.title("🎙️Toplantı Analizcisi")

tk.Button(root, text="🔴 Kaydı Başlat", command=start_recording, width=30, bg="red", fg="white").pack(pady=10)
tk.Button(root, text="⏹️ Kaydı Durdur (Segment Kaydet)", command=stop_recording, width=30).pack(pady=10)
tk.Button(root, text="📄 Segmentleri Yazıya Dönüştür ve Analiz Et", command=transcribe_all, width=40).pack(pady=10)

root.mainloop()
