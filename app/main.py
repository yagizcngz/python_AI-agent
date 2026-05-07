"""
=============================================================================
OTONOM YAPAY ZEKA AJANI (AI Agent) 
=============================================================================
Bu program, OpenRouter API üzerinden çeşitli dil modellerini kullanarak çalışan 
ve bilgisayarda otonom olarak dosya okuma (Read), dosya yazma (Write) ve 
terminal komutlari (Bash) çaliştirabilen bir asistandir.

KULLANIM İÇİN GEREKEN ADIMLAR:

1. PYTHON KURULUMU:
   Bilgisayarinizda Python'in (tercihen 3.x ve üzeri) yüklü olduğundan ve 
   sistem yoluna (PATH) eklendiğinden emin olun.

2. GEREKLİ KÜTÜPHANELER VE KURULUM:
   Bu projede hem Python'in yerleşik kütüphaneleri hem de dişaridan 
   yüklenmesi gereken özel kütüphaneler kullanilmiştir.

   A. Kurulum GEREKTİRMEYEN (Yerleşik) Kütüphaneler:
      Aşağidaki kütüphaneler Python ile birlikte hazir gelir, bunlar 
      için herhangi bir yükleme komutu çaliştirmaniza gerek YOKTUR:
      - os         : Dosya ve klasör işlemleri 
      - sys        : Sistem yollari ve dinamik Python çaliştirma işlemleri 
      - json       : API'den gelen verileri ayriştirma işlemleri
      - subprocess : Terminal (Bash) araçlarini ve komutlarini çaliştirma

   B. Kurulum GEREKTİREN (Diş) Kütüphaneler:
      Programin OpenRouter API sunucularina bağlanabilmesi için 
      aşağidaki kütüphanenin bilgisayariniza indirilmesi GEREKLİDİR. 
      Terminali (veya PowerShell'i) açip şu komutlari sirasiyla çaliştirin:

         pip install openai

3. API ANAHTARI AYARLAMA:
   Bu kodun çalişmasi için bir OpenRouter API anahtarina ihtiyaciniz vardir.
   - https://openrouter.ai/ adresine gidin ve ücretsiz bir hesap açin.
   - Profilinizden yeni bir "API Key" oluşturun.
   - Oluşturduğunuz bu API anahtarını güvenli bir yerde saklayın, çünkü bu anahtar 
    sizin API erişiminizi sağlar ve başkalarıyla paylaşılmamalıdır.
   - API anahtarınızı bilgisayarınızın ortam değişkenlerine (environment variables) ekleyin.
    Eklemek için terminal veya PowerShell'e aşağıdaki komutu yazabilirsiniz.

   - $env:OPENROUTER_API_KEY=" api_key_değeriniz " --> tırnak içine API-KEY girebilirsiniz. 
   - Eğer Programı Command Promt üzerinden çalıştırıyorsanız, set OPENROUTER_API_KEY=api_key_değeriniz  komutunu kullanarak ortam değişkenini ekleyebilirsiniz.

   - Bu komut, PowerShell kullanıyorsanız geçici olarak ortam değişkeni ekler. Kalıcı olarak eklemek için işletim sisteminizin ortam değişkenleri ayarlarına gidip OPENROUTER_API_KEY adında yeni bir değişken oluşturup değer olarak API anahtarınızı girebilirsiniz.

4. ÇALIŞTIRMA:
   Projenin ana dizininde bir terminal (veya PowerShell) açın.
   Windows kullanıcıları için programı başlatma komutu:
   
   py app/main.py -p "Buraya asistanın yapmasını istediğiniz görevi yazın."
   
   (Not: Eğer macOS/Linux kullanıyorsanız veya 'py' komutu çalışmazsa, 
   bunun yerine 'python app/main.py -p "merhaba"' veya 
   'python3 app/main.py -p "merhaba"' komutlarını deneyebilirsiniz.)

   --> API ANAHTARI ekledikten sonra çalıştırmayı deneyip [Errno 2] No such file or directory hatasını alırsanız,
   terminale cd python_AI_agent (dosyanın adını istediğiniz gibi değiştirebilirsiniz ancak değiştirdikten sonra komutta da değiştirmeyi unutmayın) komutunu yazarak bu dosyanın bulunduğu dizine geçiş yapabilirsiniz. Ardından tekrar çalıştırmayı deneyin.
   ya da py python_AI_agent/app/main.py -p "merhaba" gibi main.py dosyasının tam yolunu vererek de çalıştırabilirsiniz. 

5. EK NOTLAR:
 Prompt içinde kullanması gereken aracı özellikle belirtmezseniz, model markdown karakterleri, açıklama cümleleri ekleyebilir veya doğru aracı seçmeyebilir ve bu da programın doğru çalışmamasına neden olabilir.
 Bu yüzden, modelin hangi aracı kullanması gerektiğini açıkça belirtmek önemlidir. Örneğin, "Write aracını kullanarak 'deneme.txt' dosyasına 'Hello World!' yaz" gibi net bir talimat vermek, modelin doğru aracı kullanmasını sağlar.

 Read aracı denemek için --> py app/main.py -p "app/main.py dosyasını oku ve bana bu kodun ne işe yaradığını tek cümleyle söyle."

 Write aracını denemek için --> py app/main.py -p "app klasöründe 'deneme.txt' oluşturup içine 'Hello World!' yazan bir kod yaz ve sonra bu dosyayı oku ve içeriğini bana söyle."
 Write aracını denemek için --> py app/main.py -p "Ekrana 'Test Basarili' yazdiran kisa bir Python kodu uret. Bu kodu KESINLIKLE Write aracini kullanarak 'temiz_kod.py' isimli bir dosyaya kaydet. Baska hiçbir islem yapma."

 Bash aracını denemek için --> py app/main.py -p "Şu an bulunduğum dizindeki dosyaları listele ve bana isimlerini söyle."
 Bash aracını denemek için --> py app/main.py -p "app klasöründe 'hesap.py' oluştur, içine 5 ile 10'u toplayıp EKRANA YAZDIRAN bir kod yaz ve sonra bu dosyayı çalıştırıp sonucu bana söyle."

 Read ve Write aracı için --> py app/main.py -p "app klasöründe "app klasöründe 'deneme.txt' adında bir dosya oluştur. Bunu yapmak için doğrudan sistem araçlarını (Write) kullan ve içine 'Hello World!' yaz. Ardından okuma aracını (Read) kullanarak bu dosyayı oku ve okuduğun bu içeriği bana söyle. Bana nasıl yapılacağını anlatan bir kod metni verme, bu işlemleri bizzat yap."
 Read ve Bash aracı için --> py app/main.py -p "Terminal aracını (Bash) kullanarak Windows'un sistem bilgilerini almak için systeminfo > sistem_bilgisi.txt komutunu çalıştır (bu işlem birkaç saniye sürebilir). İşlem bittikten sonra okuma aracını (Read) kullanarak oluşan bu 'sistem_bilgisi.txt' dosyasını oku ve bana işletim sistemimin tam adını ve sürümünü söyle."

 Write ve Bash aracı için --> py app/main.py -p "1'den 50'ye kadar olan çift sayıları toplayıp sonucu ekrana yazdıran bir Python kodu üret. 1. ADIM: Bu kodu 'hesap_testi.py' adında bir dosyaya kaydet. 2. ADIM: Dosya kaydedildikten sonra terminalde bu dosyayı çalıştır ve ekrana çıkan nihai sonucu bana söyle."

 Read, Write ve Bash aracı için --> py app/main.py -p "Lütfen Yazma (Write) aracını kullanarak zincir_testi.py adında bir Python dosyası oluştur. Bu kod, 1'den 1000'e kadar olan sayıların toplamını hesaplasın ve bu sonucu gizli_sonuc.txt adında yeni bir dosyaya kaydetsin. Ardından Terminal (Bash) aracını kullanarak yazdığın bu Python dosyasını çalıştır. Son olarak Okuma (Read) aracını kullanarak, kodun ürettiği o gizli_sonuc.txt dosyasını oku ve içerideki nihai sayıyı bana söyle. Bana nasıl yapılacağını anlatma veya örnek kod verme, tüm bu araçları bizzat arka arkaya kullanarak görevi tamamla."

=============================================================================
"""

import argparse
import json
import os
import sys
import subprocess  

from openai import OpenAI

# Dizin Sabitleme (Absolute Path)
# os.path.abspath(__file__) -> Bu main.py dosyasının bilgisayardaki KESİN yolunu bulur (Örn: C:\Users\Cengiz\python-chatbot\app\main.py)
# os.path.dirname -> Bu yolun sadece klasör kısmını alır (Örn: C:\Users\Cengiz\python-chatbot\app)
# Böylece terminalin nerede açıldığına bağımlı kalmadan, her zaman doğru 'app' klasörünü hedefleriz.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    # Konuşma geçmişi - Sisteme Windows'ta olduğunu açıkça söylüyoruz
    messages = [
        # eğer linux kullanıyorsanız, bu satırı şu şekilde değiştirebilirsiniz:
        # "You are a helpful assistant. The user is on a Linux machine. Always use Linux-compatible shell commands (e.g., use 'ls' instead of 'dir', and use 'mkdir -p' for creating directories)."
        #  macOS için :
        #  "You are a helpful assistant. The user is on a macOS machine. Always use macOS-compatible shell commands (e.g., use 'ls' instead of 'dir', and use 'mkdir -p' for creating directories)."
        {"role": "system", "content": "You are a helpful assistant. The user is on a Windows machine. Always use Windows-compatible shell commands (e.g., use 'dir' instead of 'ls', and avoid 'mkdir -p' - just use 'mkdir')."},
        {"role": "user", "content": args.p}
    ]
    
    tools = [
        # --- READ ARACI ---
        {
            "type": "function",
            "function": {
                "name": "Read",
                "description": "Read and return the contents of a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path to the file to read"
                        }
                    },
                    "required": ["file_path"]
                }
            }
        },
        # --- WRITE ARACI ---
        {
            "type": "function",
            "function": {
                "name": "Write",
                "description": "Write content to a file",
                "parameters": {
                    "type": "object",
                    "required": ["file_path", "content"],
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "The path of the file to write to"
                        },
                        "content": {
                            "type": "string",
                            "description": "The content to write to the file"
                        }
                    }
                }
            }
        },
        # --- BASH ARACI ---
        {
            "type": "function",
            "function": {
                "name": "Bash",
                "description": "Execute a shell command",
                "parameters": {
                    "type": "object",
                    "required": ["command"],
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The command to execute"
                        }
                    }
                }
            }
        }
    ]

    print("Logs from your program will appear here!", file=sys.stderr)

    # Eğer dosya herhangi bir nedenden çalışmaz ve sadece Logs from your program will appear here! yazarsa API'den gelen mesajı ekranda görmek için
    # 1'den 5'e kadar olan ADIMlardaki print() fonksiyonlarının yorum satırlarını kaldırarak API'den gelen ham veriyi görebilirsiniz.
    # Bu, modelin neden beklenmedik şekilde davrandığını anlamanıza yardımcı olabilir.

    while True:
        # 1- print(">>> 1. ADIM: API'ye istek gonderiliyor (Lutfen bekleyin)...", file=sys.stderr)
        
        try:
            chat = client.chat.completions.create(
                model="poolside/laguna-xs.2:free", # (google/gemma-4-26b-a4b-it:free) modeli istediğiniz gibi değiştirebilirsiniz. Ancak, araç kullanımını destekleyen bir model seçtiğinizden emin olun.
                messages=messages,
                tools=tools,
            )
            # 2-print(">>> 2. ADIM: API'den cevap basariyla alindi!", file=sys.stderr)
        except Exception as e:
            print(f"!!! KRITIK HATA: API baglantisi coktu: {e}", file=sys.stderr)
            break


        # 1. GÜVENLİK AĞI: API tamamen çökerse veya boş dönerse
        if not chat.choices or len(chat.choices) == 0:
            print("!!! HATA: OpenRouter bombos yanit gonderdi. (Sunucu yoğun veya limit asildi)", file=sys.stderr)
            break

        message = chat.choices[0].message
        
        # repr() kullanarak gizli bosluk veya kacis karakterlerini (\n) aciga cikariyoruz
        # 3- print(f">>> 3. ADIM: Modelin verisi -> ICERIK: {repr(message.content)} | ARAC_KULLANIMI: {bool(message.tool_calls)}", file=sys.stderr)

        # API dictionary dönüşümü (Geçmişi unutmaması için)
        assistant_msg = {"role": "assistant"}
        if message.content:
            assistant_msg["content"] = message.content
        if message.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in message.tool_calls
            ]
            
        messages.append(assistant_msg)

        if message.tool_calls:
            # 4- print(">>> 4. ADIM: Model bir aractan yardim istiyor, isleniyor...", file=sys.stderr)
            for tool_call in message.tool_calls:
                
                # --- READ İŞLEMİ ---
                if tool_call.function.name == "Read":
                    arguments = json.loads(tool_call.function.arguments)
                    file_path = arguments["file_path"]
                    
                    # Dosya Okuma Güvenliği
                    # os.path.basename() -> Gelen yoldan sadece dosya adını ("deneme.txt") ayıklar.
                    # os.path.join() -> Bu dosya adını bizim kesin yolumuzla (BASE_DIR) birleştirip içeriye hapseder.
                    safe_filename = os.path.basename(file_path)
                    absolute_file_path = os.path.join(BASE_DIR, safe_filename)

                    try:
                        with open(absolute_file_path, "r", encoding="utf-8",errors="ignore") as f:
                            content = f.read()
                    except Exception as e:
                        content = f"Error reading file: {e}"
                        print(content, file=sys.stderr)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": content
                    })
                
                # --- WRITE İŞLEMİ ---
                elif tool_call.function.name == "Write":
                    arguments = json.loads(tool_call.function.arguments)
                    # Esnek anahtar kontrolü (KeyError önleyici)
                    file_path = arguments.get("file_path") or arguments.get("filename")
                    file_content = arguments.get("content") or arguments.get("file_content")

                    # Dosya Yazma Güvenliği
                    # Tıpkı Read işlemindeki gibi, dosyanın başka bir klasöre (ana dizine) yazılmasını engelliyoruz.
                    # Sadece dosyanın ismini alıyor ve zorla kendi klasörümüzün içine (BASE_DIR) kaydediyoruz.
                    safe_filename = os.path.basename(file_path)
                    absolute_file_path = os.path.join(BASE_DIR, safe_filename)

                    try:
                        # Dosyanın kaydedileceği dizin yoksa (ki artık hep BASE_DIR olacak) güvenli bir şekilde oluşturur.
                        os.makedirs(os.path.dirname(absolute_file_path), exist_ok=True)
                        with open(absolute_file_path, "w", encoding="utf-8",errors="replace") as f:
                            f.write(file_content)
                        result = f"File {file_path} written successfully."
                    except Exception as e:
                        result = f"Error writing file: {e}"
                        print(result, file=sys.stderr)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

                # --- BASH İŞLEMİ ---
                elif tool_call.function.name == "Bash":
                    arguments = json.loads(tool_call.function.arguments)
                    command = arguments.get("command") or arguments.get("cmd")
                    
                    if not command and arguments:
                        command = list(arguments.values())[0]
                    
                    if command:
                        # Sistemde ne yüklü olursa olsun, şu an çalışan Python'un tam yolunu kullanır
                        python_exe = sys.executable
                        # Hem 'python' hem de 'python3' kelimelerini doğru yolla değiştiriyoruz
                        command = command.replace("python3 ", f'"{python_exe}" ').replace("python ", f'"{python_exe}" ')
                        
                        try:
                            # Hangi komutun gittiğini görmen için stderr'e yazdırıyoruz. Eğer program Bash işlemi yaptıktan sonra terminalde DEBUG ve Terminal çıktısı görmek istiyorsanız print(f...) satırlarındaki yorum satırlarını kaldırabilirsiniz.
                            # print(f"DEBUG - Çaliştirilan: {command}", file=sys.stderr)

                            # Terminal Çalışma Dizini (CWD) Sabitleme
                            # cwd=BASE_DIR parametresi, çalıştırılan terminal komutunun doğrudan 'app' klasörü 
                            # içerisinde çalışmasını garanti eder. Bu sayede model kendi yazdığı python dosyasını 
                            # çalıştırırken "dosya bulunamadı" hatası almaz.
                            process = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=BASE_DIR,errors="replace")
                            result = f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}"
                            # print(f"--- Terminal Çiktisi ---\n{result}\n-----------------------", file=sys.stderr)
                        except Exception as e:
                            result = f"Error: {e}"
                            print(result, file=sys.stderr)
                    else:
                        result = "Error: No command found."

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

        else:
            # 5- print(">>> 5. ADIM: Model arac kullanmadi, nihai cevap yazdirilip donguden cikiliyor.", file=sys.stderr)
            if message.content:
                print(message.content)
            else:
                # 2. GÜVENLİK AĞI: Model araç kullanmaz ve cevap da vermezse
                # Modelin boş dönme ihtimalini terminalde yakalıyoruz
                print(">>> 5. ADIM HATA: Model hiçbir araç kullanmadi ve metin üretmedi. Sadece donup kaldi.", file=sys.stderr)
            break

if __name__ == "__main__":
    main()