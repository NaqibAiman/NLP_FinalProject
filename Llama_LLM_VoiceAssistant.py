import whisper
import ollama
import os
import keyboard
import pyaudio
import wave
import time
import edge_tts 
import asyncio
import json
import pygame # NEW: For playing audio without windows

# --- CONFIGURATION ---
MODEL_SIZE = "tiny.en" 
MEMORY_FILE = MEMORY_FILE = os.path.join(os.path.expanduser("~"), "Desktop", "memory.json")

# Suppress the "Hello from pygame" message
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

print(f"Loading Whisper model ({MODEL_SIZE})...")
model = whisper.load_model(MODEL_SIZE)

# --- MEMORY FUNCTIONS ---
def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_memory(history):
    with open(MEMORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

conversation_history = load_memory()
print(f"Loaded {len(conversation_history)} past messages.")

# Hardcoded FAQs
faq = {
    "library hours": "The library is open from 8am to 10pm.",
    "exam timetable": "You can check the exam timetable on the student portal.",
    "course registration": "Course registration is done through i-Ta'leem."
}

def record_audio_on_keypress():
    """Records audio ONLY while the user holds down the SPACEBAR."""
    print("\n-------------------------------------------------")
    print("   HOLD [SPACEBAR] TO SPEAK  |  PRESS [Q] TO QUIT")
    print("-------------------------------------------------")
    
    while True:
        if keyboard.is_pressed('q'):
            return None
        if keyboard.is_pressed('space'):
            break
        time.sleep(0.05)
    
    print(">>> Listening...")

    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []

    while keyboard.is_pressed('space'):
        data = stream.read(CHUNK)
        frames.append(data)

    print(">>> Processing...")
    stream.stop_stream()
    stream.close()
    p.terminate()

    filename = "temp_voice.wav"
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    
    return filename

def speech_to_text(audio_path):
    result = model.transcribe(audio_path, fp16=False)
    return result["text"].strip()

def get_response(text):
    print(f"You said: {text}")
    
    for key in faq:
        if key in text.lower():
            return faq[key]

    conversation_history.append({'role': 'user', 'content': text + " Answer in 1 short sentence."})
    
    active_memory = conversation_history[-20:]

    print("(Thinking...)")
    try:
        response = ollama.chat(
            model='llama3.2', 
            messages=active_memory
        )
        reply = response['message']['content']
        
        conversation_history.append({'role': 'assistant', 'content': reply})
        save_memory(conversation_history)
        
        return reply
        
    except Exception as e:
        return "I cannot connect to Ollama."

# --- UPDATED SPEAK FUNCTION ---
def speak(text):
    print(f"Assistant: {text}")
    output_file = "reply.mp3"
    
    # 1. Clear old file
    if os.path.exists(output_file):
        try:
            os.remove(output_file)
        except PermissionError:
            print("Warning: Could not delete old file. Overwriting might fail.")

    # 2. Generate Audio
    try:
        communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
        asyncio.run(communicate.save(output_file))
        
        # 3. Play Audio using Pygame (Invisible)
        pygame.mixer.init()
        pygame.mixer.music.load(output_file)
        pygame.mixer.music.play()
        
        # Wait for audio to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        # 4. Release the file so we can delete it next time
        pygame.mixer.quit()
        
    except Exception as e:
        print(f"Voice Error: {e}")

# --- Main Loop ---
if __name__ == "__main__":
    while True:
        audio_file = record_audio_on_keypress()
        
        if audio_file is None:
            print("Exiting...")
            break
            
        user_text = speech_to_text(audio_file)
        
        if not user_text:
            continue
            
        reply = get_response(user_text)
        speak(reply)
        
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except:
                pass