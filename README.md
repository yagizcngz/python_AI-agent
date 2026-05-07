1. KÜTÜPHANE İÇE AKTARIMLARI (IMPORTS)
import argparse
import json
import os
import sys
import subprocess  
from openai import OpenAI
•	argparse: Terminalden komut çalıştırırken yanına eklediğimiz -p "merhaba" gibi parametreleri yakalamamızı ve okumamızı sağlar.
•	json: Yapay zekanın araçları kullanırken gönderdiği veriler JSON formatındadır. Bu kütüphane o verileri Python'un anlayabileceği sözlüklere (dictionary) çevirir.
•	os: İşletim sistemiyle konuşmamızı sağlar. Dosya yollarını bulma, klasör oluşturma ve ortam değişkenlerinden API anahtarını çekme işlerini yapar.
•	sys: Sistemin o an kullandığı Python'un tam yolunu bulmak ve terminale hata/bilgi mesajları basmak (sys.stderr) için kullanılır.
•	subprocess: Terminal komutlarını (Bash aracı) doğrudan Python içinden çalıştırmamızı sağlar.
•	OpenAI: OpenRouter sunucularına bağlanıp yapay zekâ ile mesajlaşmamızı sağlayan ana köprü kütüphanesidir.

2. GÜVENLİK VE AYAR DEĞİŞKENLERİ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
•	BASE_DIR: Programın kalbidir. main.py dosyasının bilgisayardaki tam ve kesin yerini bulup kilitler. Yapay zeka ajanının bu klasörün dışına çıkmasını engeller.
•	API_KEY ve BASE_URL: Terminal ortam değişkenlerinden gizli API anahtarımızı alır. BASE_URL, OpenAI kütüphanesini kandırıp istekleri OpenAI yerine OpenRouter'a yönlendirmemizi sağlar.

3. PROGRAMIN BAŞLAMASI VE HAZIRLIK (main() Fonksiyonu)
def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()
•	Program terminalden başlatıldığında -p parametresinden sonra yazılan görevi (prompt) alır ve args.p değişkenine kaydeder.

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
•	API anahtarının var olup olmadığını kontrol eder, yoksa programı çökerterek uyarır. Varsa bağlantı istemcisini (client) oluşturur.

    messages = [
        {"role": "system", "content": "You are a helpful assistant. The user is on a Windows machine..."},
        {"role": "user", "content": args.p}
    ]
•	messages: Yapay zekanın hafızasıdır (sohbet geçmişi). Önce ona sistem komutuyla (Sen bir asistansın ve Windows'tasın) kim olduğunu söyleriz, ardından kullanıcının girdiği -p görevini ekleriz.

•	4. ARAÇLARIN (TOOLS) TANIMLANMASI
    tools = [
        # ... Read, Write ve Bash tanımları ...
    ]
•	Burada yapay zekâya "Senin ellerin ve gözlerin var, bunları kullanabilirsin" diyerek araçların kullanım kılavuzlarını (JSON formatında) veriyoruz. Model bu açıklamalara bakarak hangi aracı ne zaman seçeceğine karar verir.

5. BEYİN DÖNGÜSÜ (The while True Loop)

Ajanın adım adım düşünmesini ve görevleri zincirleme yapmasını sağlayan sonsuz döngüdür.
    while True:
        try:
            chat = client.chat.completions.create(...)
•	Ajan mevcut messages (hafıza) ve tools (araçlar) ile OpenRouter'a istek atar ve yapay zekâdan "Ne yapmalıyım?" diye cevap bekler.
A. Hafızayı Güncelleme
        assistant_msg = {"role": "assistant"}
        if message.content:
            assistant_msg["content"] = message.content
        if message.tool_calls:
            assistant_msg["tool_calls"] = [...]
        messages.append(assistant_msg)
•	Yapay zekanın verdiği cevabı veya kullanmak istediği aracı hafızaya (messages listesine) kaydeder. Böylece ajan bir sonraki adımda ne yaptığını unutmaz.
B. Araçları Çalıştırma (Eylem Aşaması)
        if message.tool_calls:
            for tool_call in message.tool_calls:
•	Eğer model "Bir araç kullanmak istiyorum" derse, bu bloğa girilir ve hangi aracı seçtiğine bakılır.
Read (Okuma) Aracı:
                if tool_call.function.name == "Read":
                    ...
                    safe_filename = os.path.basename(file_path)
                    absolute_file_path = os.path.join(BASE_DIR, safe_filename)
•	Yapay zekanın okumak istediği dosyanın yolundan sadece dosya adını çeker (safe_filename) ve bunu bizim BASE_DIR ile birleştirir. Dosyayı okur ve sonucunu hafızaya geri ekler.

Write (Yazma) Aracı:
                elif tool_call.function.name == "Write":
                    ...
                    safe_filename = os.path.basename(file_path)
                    absolute_file_path = os.path.join(BASE_DIR, safe_filename)
                    os.makedirs(os.path.dirname(absolute_file_path), exist_ok=True)
                    with open(...)
•	Okuma aracındaki aynı güvenlik duvarı buradadır. Modelin dosyayı BASE_DIR (app klasörü) dışına yazmasını engeller. Eksik klasör varsa oluşturur, dosyayı yazar ve "Başarıyla yazıldı" mesajını hafızaya ekler.
Bash (Terminal) Aracı:
                elif tool_call.function.name == "Bash":
                    ...
                    python_exe = sys.executable
                    command = command.replace("python3 ", f'"{python_exe}" ')...
                    process = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=BASE_DIR, errors="replace")
•	Eğer model python deneme.py gibi bir komut çalıştırmak isterse, kod sistemi bunu bilgisayarın gerçek Python yoluyla değiştirir.
•	cwd=BASE_DIR: Komutun her zaman app klasöründe çalışmasını garanti ederek yol bulunamadı hatalarını sıfıra indirir. Komutun terminal çıktısını yakalayıp ajana geri gönderir.
•	errors="replace" parametresi programı Python'un terminalden okuyamadığı garip bir sembol veya Türkçe karakter gelirse programı çökertmek yerine harfin yerine ? Sembolü koyup işleme devam etmesini sağlar.
C. Görevin Tamamlanması
        else:
            if message.content:
                print(message.content)
            ...
            break
•	Model artık araç kullanmak istemiyorsa (görevi bitirdiyse), son hazırladığı cevabı (message.content) ekrana basar.
•	break komutu ile while döngüsünü kırar ve programı başarıyla sonlandırır.

6 -EK NOTLAR:

**NEDEN STDOUT YERİNE STDERR KULLANILIYOR ?**
Diyelim ki asistanından bir kod yazmasını istedin ve bu kodu doğrudan bir dosyaya kaydetmek için terminalde yönlendirme (>) veya (|) işaretlerini kullandın:
Her şeyi stdout yapsaydın: sonuc.py dosyasının içine yapay zekanın cevabının yanı sıra "Logs from your program will appear here!" 
ve "DEBUG - Çalıştırılan: ..." gibi arka plan logları da yazılırdı. Dosyanın içi çorbaya dönerdi ve kod çalışmazdı.
stderr sayesinde: İşletim sistemi stderr mesajlarını dosyaya yönlendirmez. Bu loglar sadece senin ekranında akar (böylece asistanın
ne yaptığını canlı olarak izlersin), ama sonuc.py dosyasının içine sadece ve sadece yapay zekanın ürettiği o temiz kod (stdout) kaydedilir.

**NEDEN \xff YAZAN BİR HATA ALIRSIN ?**
Eğer prompt yazarken kullanılması gereken aracı belirtmediyseniz, dosya varsayılan olarak utf-16 formatında kaydedilir. \xff ibaresi bu formatın kullanıldığı anlamına gelir.
Ancak .py utf-8 formatında dosya kabul eder. Düzeltmek için dosyayı manuel olarak açıp utf-8 olarak kaydedebilir, terminal üzerinden PowerShell'e
formatı zorla utf-8 olarak yazdıran | Out-File -Encoding utf8 ekleyebilirsiniz ya da Write aracını kullanabilirsiniz çünkü içerisinde dosya formatı utf-8 var.
Write aracını kullanmak en basit ve mantıklı çözüm.

**HATA TESPİT KISMINDA NEDEN RAİSE RuntimeError YERİNE PRİNT KULLANIYORUZ ?**
•	raise RuntimeError: Programın çalışmasını o satırda anında keser. Amacı kodda gözden kaçırdığı ölümcül bir mantık hatası varsa, programın yanlış çalışmaya devam edip sistemi bozmasını engellemektir.
•	print: Sadece terminalin "hata/log" kanalına bir metin yazdırır, ancak programı durdurmaz. Kullanıcıya "Burada bir sorun var ama programı tamamen çökertecek kadar büyük değil" mesajı verir.
•	Kullanım Farkı:
- Kritik hatalar (API anahtarı bulunamadı, yapılandırma hatası): `raise RuntimeError` kullan.
- Uyarılar/Bilgilendirmeler (başarısız koşu, geçici sorunlar): `print` kullan.   

**Error Code 429 HATASI NEDİR ?**
1- Kullandığınız yapay zekâ kısa süreliğine fazla isteğe maruz kaldığından dolayı cevap veremiyor (... :free is temporarily rate-limited upstream. Please retry shortly:). 
Kısa süre içerisinde tekrar denerseniz, isteğiniz gerçekleşebilir. Ya da farklı bir model kullanabilirsiniz. 
2- O günlük ücretsiz kullanım hakkınız bittiğinden dolayı (Rate limit exceeded) hata alıyor olabilirsiniz. Farklı bir hesaptan,farklı bir key ile ya da credit alarak düzeltebilirsiniz.

**NEDEN import openai from OpenAI KULLANILIYOR ?**
Sektörün Evrensel Dili: "OpenAI Formatı"
Piyasayı domine eden şirket OpenAI Geliştiricilerin kendi sistemlerini kullanabilmesi
için bir API yapısı (isteklerin nasıl gönderileceği, JSON verilerinin nasıl sıralanacağı, rollerin system, user, assistant olarak nasıl ayrılacağı) tasarladılar.
Zamanla herkes bu yapıya o kadar alıştı ve o kadar çok proje bu yapı üzerine kuruldu ki, OpenAI'ın bu mesajlaşma formatı yapay zeka dünyasının evrensel dili haline geldi.
OpenRouter sizin OpenAI ile konuşuyormuş gibi gönderdiğiniz istekleri arka planda alıp kullanmak istediğiniz yapay zekanın anlayacağı dile çeviriyor.
İşte bu mimariye "OpenAI-Compatible API" (OpenAI Uyumlu API) denir.

**NEDEN KÜTÜPHANE OLARAK openai KULLANIYORUZ?**
Eğer openai kütüphanesini kullanmasaydık, Python'un yerleşik requests kütüphanesiyle API'ye manuel olarak bağlanmamız gerekirdi. Bu da şu anlama gelirdi:
•	Giden her isteğin HTTP başlıklarını (Headers) elde yazmak.
•	İstek koptuğunda yeniden bağlanma (Retry) mantığını sıfırdan kodlamak.
•	Gelen karmaşık JSON verilerini manuel olarak parçalamak (Parse).
Bunun yerine bilgisayarımıza indirdiğimiz openai Python kütüphanesini kullanıyoruz. Bu kütüphane, senin promptlarını ve araçlarını (paketleri) OpenAI standartlarında paketliyor.
•	Main dosyasında bulunan bu satır ile:
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
Biz openai'a diyoruz ki: "Paketi senin standartlarında, senin kutularınla hazırla ama kargoyu OpenAI'ın genel merkezine değil, benim sana verdiğim bu yeni adrese (OpenRouter'a) teslim et."

**NEDEN BASH ARACI İÇERİSİNDE errors="replace" KULLANILIYOR ?**
Eğer programı Command Prompt veya PowerShell üzerinden kullanmaya çalışırsanız, Ajan arka planda systeminfo gibi bir Windows komutu çalıştırdığında Windows, bu komutun sonucunu terminale basarken Türkçe karakterler (ı, ş, ğ) veya sisteme özel bazı semboller kullanıyor. Python terminalden gelen bu metni okumaya çalışırken karakterleri tanıyamadığı için UnicodeDecodeError hatasını veriyor. errors="replace" parametresi Python okuyamadığı garip bir sembol veya Türkçe karakter ile karşılaştığında programı çökertmek yerine ? kullanarak sorunsuz bir şekilde devam etmesini sağlar.

**NEDEN SON SATIRDA if __name__ == "__main__": KULLANIYORUZ?**
Eğer bu kontrol kullanılmasaydı ve en altta doğrudan main() fonksiyonu çağrılsaydı, ileride başka bir projenin içine import main yazıldığında ajan aniden uyanır, terminalden -p parametresini beklemeye başlar ve o yeni projeyi anında çökerterdi.
Bunun engellenmesinin sebebi, Python'da her dosyanın arka planda __name__ adında gizli bir kimliğinin bulunmasıdır. Bu kimlikte ne yazacağı, dosyanın nasıl çalıştırıldığına göre değişir:
Dosya doğrudan terminalden veya çift tıklanarak açılırsa; Python bu dosyaya "Top-Level Code" statüsü verir ve programın Giriş Noktası (Entry Point) olduğu için gizli kimliğine "__main__" (Ana Modül) yazar.
Başka bir projenin içine import edildiğinde ise hiyerarşide aşağı düşer. Python bu sefer gizli kimliğe "__main__" yazmaz, onun yerine sadece dosyanın adını ("main") yazar.
En sondaki if __name__ == "__main__": satırı, isimlerin eşleşmediğini kontrol eden bir güvenlik duvarıdır. İsim eşleşmediğinde dosya sıradan bir kütüphane gibi davranır, "Ajan döngüsünü başlatmamalıyım" diyerek sessizce bekler ve bu sayede başka projelerde hata almadan sadece içerideki araçları (Read, Write, Bash vb.) kullanabilmemize olanak tanır.
