# ᚛᚜ Yggdrasil Security Framework ᚛᚜

![Dashboard Overview](screenshots/1.png?v=3)

[ 🇬🇧 English ](#-english) | [ 🇹🇷 Türkçe ](#-türkçe)

---

## 🇬🇧 English

This repository features an advanced security reconnaissance and vulnerability assessment framework developed to centralize offensive security operations. It integrates industry-standard tools into a unified, Norse-themed dashboard to streamline the information gathering and exploitation phases of a penetration test.

### Project Reflection & Technical Q&A

#### 1. Why did I write the code this way? (XYZ Analysis)
* My objective was to eliminate the inefficiency of switching between multiple command-line tools during a security audit. 
* I accomplished a centralized, web-based management system as measured by reducing tool initialization and reporting time by integrating a Python Flask backend with a dynamic Runic Dashboard. 
* This ensures that reconnaissance data is visualized and logged in real-time within a cohesive operational environment.

#### 2. What challenges did I face?
* **Subprocess Management**: Handling multiple concurrent security tools required a robust subprocess execution logic to prevent the Flask backend from hanging during intensive scans.
* **Dependency Orchestration**: I implemented a "Runic Installation Ritual" (Automated Dependency Checker) to detect missing system tools and install them dynamically without manual user intervention.
* **Output Streaming**: Implementing the typewriter effect for real-time output rendering was a challenge in managing asynchronous JavaScript data streams within a synchronous HTML environment.

#### 3. How did I manage the Security Arsenal?
* **Modular Integration**: I architected a modular command execution engine that handles specialized flags for Nmap, Sqlmap, Nikto, and WPScan to ensure optimal scan accuracy.
* **Artifact Logging**: The framework includes a reporting module that sanitizes terminal output and exports it into structured TXT or JSON artifacts for professional security documentation.

---

### ᚛᚜ Complete Integrated Arsenal & Features ᚛᚜

The Yggdrasil Security Framework integrates **25 core features and modules** divided into 7 distinct tactical categories:

| Runic Category | Tool Name | Description | Target Req. | OS Support | Command / Handler |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Passive Reconnaissance (ᚠ)** | WHOIS Lookup | Domain registration information retrieval | Yes | Linux/Win | `whois {target}` |
| | The Harvester | Email, subdomain, and host intelligence gathering | Yes | Linux/Win | `theHarvester -d {target} -l 100 -b all` |
| | Amass Enumeration | Deep open-source subdomain scanning | Yes | Linux/Win | `amass enum -d {target} -passive` |
| | Sherlock | Search social accounts by username | Yes | Linux/Win | `sherlock {target} --timeout 5` |
| | Google Dorks Tree | Interactive dork search links (admin/login/indexes/PDFs...) | Yes | Custom | `generate_dorks` handler |
| | Wayback Machine | Query archive.org for past URLs and cached endpoints | Yes | Custom | `wayback` handler |
| **DNS & Subdomain (ᛉ)** | DNS Enum | Locate DNS records and subdomains | Yes | Linux | `dnsenum --noreverse {target}` |
| | Subfinder | Fast passive subdomain enumeration | Yes | Linux/Win | `subfinder` handler |
| | Assetfinder | Lightweight subdomain discovery | Yes | Linux/Win | `assetfinder --subs-only {target}` |
| | Fierce | IP block and zone-transfer DNS scanner | Yes | Linux/Win | `fierce --domain {target}` |
| | Knockpy | Brute-force DNS subdomain scanner | Yes | Linux/Win | `knockpy` handler |
| | Gobuster DNS | Fast brute-force subdomain discovery | Yes | Linux/Win | `gobuster_dns` handler |
| | Nslookup | Built-in DNS query utility | Yes | Linux/Win | `nslookup -type=any {target}` |
| | Sublist3r | Fast multi-engine subdomain enumeration | Yes | Linux/Win | `sublist3r -d {target}` |
| | DNS Recon | Advanced DNS discovery and AXFR query tool | Yes | Linux/Win | `dnsrecon -d {target}` |
| | Dig (DNS Utils) | Direct query utility for DNS records | Yes | Linux/Win | `dig ANY {target}` |
| **Active Scanning (ᛦ)** | Nmap (Full Scan) | Rapid service identification and port scanning | Yes | Linux/Win | `nmap -sV -F --version-light {target}` |
| | WAF Detection | Detect and identify Web Application Firewalls (Wafw00f) | Yes | Linux/Win | `wafw00f {target}` |
| | Packet Sniffer | Capture network traffic using live Tshark stream | Yes | Linux/Win | `tshark -c 5 -i any` |
| | Nikto Web Scan | Scan target web servers for dangerous files and outdated software | Yes | Linux | `nikto -h {target} -Tuning 1` |
| | WPScan | WordPress vulnerability enumeration & user scan | Yes | Linux | `wpscan --url {target} --enumerate p --random-user-agent` |
| **Vulnerability (ᛟ)** | Exploit-DB Search | Offline check for local exploit binaries (Searchsploit) | Yes | Linux | `searchsploit {target}` |
| | Lynis (System Hardening) | Security auditing and system hardening tool | No | Linux | `lynis audit system` |
| | Nuclei (Vuln Scanner) | Fast and customizable vulnerability scanner | Yes | Linux/Win | `nuclei -u {target}` |
| | Wapiti (Web Scanner) | Web application vulnerability scanner | Yes | Linux/Win | `wapiti -u {target}` |
| | Nmap (CVE Vulners) | Nmap scan using Vulners script | Yes | Linux/Win | `nmap -sV --script vulners {target}` |
| | Hydra (Brute Force) | Parallelized network login cracker | Yes | Linux/Win | `hydra_bruteforce` handler |
| | Sqlmap | Automate detection and exploitation of SQL injection | Yes | Linux/Win | `sqlmap -u {target} --batch --banner` |
| | Commix | Automated command injection vulnerability scanner | Yes | Linux/Win | `commix --url {target} --batch` |
| | Fenrir Hash Cracker | Advanced GPU/CPU (AVX2/OpenCL) accelerated password hash auditor. | Yes | Linux/Win | `fenrir_handler` |
| **Erebus Scanner (Rust) (ᛥ)** | Erebus Scanner | Multi-threaded port scanner with banner grabbing, proxy routing, and IDS evasion | Yes | Linux/Win | `cargo run --manifest-path Runes/erebus-scanner/Cargo.toml` |
| **Kali Ghost Scripts (ᚷ)** | MAC Değiştir | Spoof network interfaces with random MAC | No | Linux | `bash Runes/mac_degistir.sh` |
| | Kimlik Sorgula | Query current public metadata & geolocate | No | Linux | `bash Runes/sorgula.sh` |
| | Yeni IP (Tor) | Renew active IP addressing on Tor circuits | No | Linux | `bash Runes/yeni_ip.sh` |
| **Advanced SYN Scanning (ᛋ)** | Advanced SYN Scan | High speed custom TCP SYN port scanner | Yes | Linux | `Runes/Advanced-SYN-Scanner/syn_scanner` |
| **GUI Traffic Analyzer (ᛈ)** | Launch GUI Sniffer | Maven-compiled JavaFX graphic packet analysis UI | No | Linux/Win | `mvn javafx:run` (in sniffer dir) |
| **Mimir Scanner (ᛗ)** | Mimir Scanner | Real-time network traffic analyzer (Java Spring Boot + React) | No | Linux/Win | `mimir_scanner` handler |
| **SnoopDork OSINT V3 (ᛞ)** | Launch SnoopDork OSINT | Dynamic Target-Oriented OSINT Dork Generator | No | Linux/Win | Browser-based GUI |
| **Packet Injector (ᛇ)** | Packet Injector | Raw packet crafter, TCP SYN/ARP injector, and sniffer engine | Yes | Linux | `sudo python3 Runes/packet-injector/main.py` |
| **Bifrost Gateway (ᛒ)** | Bifrost Gateway | High-performance, cybersecurity-focused API Gateway built with Spring Boot | No | Linux/Win | `mvn spring-boot:run` (in bifrost dir) |
| **System Operations (⚙️)** | Sync All Runes | Synchronize local tool repos with upstream GitHub releases | No | Custom | `update_modules` handler |

---

### ᛝ Custom Integrations (My Runes)

We have expanded the framework with specialized, custom-built tools compiled under the **Runes** directory:

1. **Fenrir Hash Cracker:** Advanced GPU/CPU (AVX2/OpenCL) accelerated password hash auditor. Supports Dictionary, Mask, and Rule-based attacks with live TUI progress.
2. **Erebus Scanner (Rust):** An advanced, highly concurrent network scanner written in Rust. Features a dedicated UI Modal for deep configuration:
   * **Port Ranges & Randomization:** Evade basic IDS logic by scrambling ports.
   * **Banner Grabbing & Vulnerability Checking:** Instantly identify services and check CVE logs.
   * **Adaptive Rate Limiting:** Dynamically throttle connection speeds to avoid triggering network firewalls.
   * **Proxy Support:** Route scans seamlessly through Tor or SOCKS5 proxies.
3. **Kali Ghost Scripts:** Essential networking manipulation tools fully integrated into the dashboard (MAC changer, Public IP lookup, IP renewal for Tor nodes).
4. **Advanced SYN Scanner:** Configurable SYN port scanner offering automated and manual modes with custom source/target routing directly from the web interface.
5. **GUI Sniffer (JavaFX & Maven):** A cross-platform GUI Packet Sniffer built in Java, tracking packet lengths, protocols, source/destination IPs, and network activity.
6. **SnoopDork V3:** A dynamic, target-oriented OSINT Dork generator that operates entirely client-side. Generates comprehensive queries for Google, Shodan, GitHub, Pastebin, and more, complete with a stealth mode for privacy.
7. **Packet Injector:** Advanced raw socket packet crafter and injector tool. Supports TCP SYN injection, ARP Poison crafting, operation rate limits, bursts, and standalone packet sniffing/ARP detection on raw ethernet interfaces.
8. **Mimir Scanner:** A full-stack Real-time Network Traffic Analyzer. Uses a Spring Boot backend with pcap4j and GeoIP2 mapping to capture packets, delivering real-time flows to a React frontend via WebSockets.
9. **Bifrost Gateway:** A high-performance, cybersecurity-focused API Gateway built with Spring Boot. Operates as a stateless security intermediary intercepting malicious traffic. Features a robust WAF (Mjolnir) capable of inspecting Request Bodies (JSON/XML) and Headers, along with DoS protection utilizing Caffeine Cache for rapid IP eviction and token-bucket rate limiting.
10. **Dependency Manager (Runic Installation Ritual):** Scans the host system for missing dependencies (Nmap, Sqlmap, Cargo, Maven, etc.) and provides a one-click automated installation across Linux and Windows environments through consecutive animated terminal outputs.

---

### ᚛᚜ System Manual & Deployment ᚛᚜

#### Installation Guide

Since the custom **Runes** are integrated as Git Submodules, make sure to clone the repository recursively so that all modules are loaded:

```bash
# Clone the repository along with all custom submodules
git clone --recurse-submodules https://github.com/mecik-arda/Yggdrasil-Security-Framework.git
cd Yggdrasil-Security-Framework
```

*If you already cloned it without `--recurse-submodules`, run the following commands to download the submodules:*
```bash
git submodule update --init --recursive
```

#### Environment Setup
Ensure Python 3.x and Flask are installed in your realm. You can use the included virtual environment scripts:

**On Linux/macOS:**
```bash
chmod +x run.sh
./run.sh
```

**On Windows:**
```cmd
run.bat
```

*Or manually:*
```bash
pip install -r requirements.txt
python app.py
```

---

### ᚦ Usage Protocol

1. **Step 1**: Enter the target's IP address or Domain in the central input field.
2. **Step 2**: Select a specific "Rune" (Tool) from the sidebar categories.
3. **Step 3**: Monitor the "Status Bar" for system feedback and the "Output Area" for live results.
4. **Step 4**: Once the operation is complete, use the Artifact Export buttons to secure your findings.

---

### Disclaimer
This framework is developed for educational purposes and authorized penetration testing only. The author is not responsible for any misuse of this tool.

### License
This project is licensed under the MIT License - see the LICENSE file for details.

---

<br>

## 🇹🇷 Türkçe

Bu depo, ofansif güvenlik operasyonlarını tek bir merkezde toplamak için geliştirilmiş kapsamlı bir güvenlik keşif (reconnaissance) ve zafiyet değerlendirme framework'üdür. Sızma testi (penetration test) süreçlerindeki bilgi toplama ve sömürme aşamalarını kolaylaştırmak için endüstri standardı araçları İskandinav mitolojisi (Norse) temalı dinamik bir kontrol panelinde (dashboard) birleştirir.

### Proje Yansımaları & Teknik Soru-Cevap

#### 1. Kodu Neden Bu Şekilde Yazdım? (XYZ Analizi)
* Amacım, güvenlik denetimleri sırasında birden fazla komut satırı aracı arasında geçiş yapmanın getirdiği verimsizliği ortadan kaldırmaktı.
* Python Flask tabanlı bir backend ile dinamik bir "Runic Dashboard"u entegre ederek, araç başlatma ve raporlama sürelerini ciddi oranda düşüren, merkezi ve web tabanlı bir yönetim sistemi kurmayı başardım.
* Bu yapı, keşif verilerinin bütünleşik bir operasyonel ortamda eşzamanlı olarak (real-time) görselleştirilmesini ve loglanmasını sağlıyor.

#### 2. Ne Tür Zorluklarla Karşılaştım?
* **Subprocess (Alt Süreç) Yönetimi**: Eşzamanlı çalışan çok sayıda güvenlik aracını idare etmek, Flask sunucusunun yoğun taramalar sırasında çökmemesi veya kilitlenmemesi adına güçlü bir subprocess çalışma mantığı gerektirdi.
* **Bağımlılık (Dependency) Orkestrasyonu**: Sistemde eksik olan araçları otomatik tespit eden ve manuel müdahale olmaksızın kurulumlarını gerçekleştiren "Runic Installation Ritual" (Otomatik Bağımlılık Yöneticisi) sistemini kurdum.
* **Canlı Veri Akışı**: Terminal çıktılarının tarayıcıya yansıtılması (typewriter animasyonu ile), senkron çalışan bir HTML yapısı içinde asenkron JavaScript veri akışlarını yönetmeyi zorunlu kıldı.

#### 3. Güvenlik Arsenalini Nasıl Yönettim?
* **Modüler Entegrasyon**: Nmap, Sqlmap, Nikto ve WPScan gibi araçların kendilerine has argümanlarını en verimli tarama sonuçları için işleyebilen, modüler bir komut çalıştırma motoru tasarladım.
* **Log ve Veri Dışa Aktarımı (Artifacts)**: Terminal çıktılarındaki gereksiz karakterleri temizleyerek sonuçları yapılandırılmış (structured) TXT veya JSON dosyalarına dönüştüren profesyonel bir raporlama modülü ekledim.

---

### ᚛᚜ Entegre Arsenal ve Tüm Özellikler ᚛᚜

Yggdrasil Security Framework, 7 farklı taktiksel kategoriye ayrılmış **25 ana özellik ve modül** barındırmaktadır:

| Runic Kategori | Araç İsmi | Açıklama | Hedef (Target) Zorunlu mu? | İşletim Sistemi (OS) Desteği | Komut / Handler |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Pasif Keşif (ᚠ)** | WHOIS Lookup | Domain kayıt bilgisi (WHOIS) sorgulama | Evet | Linux/Win | `whois {target}` |
| | The Harvester | Email, subdomain ve host istihbarat aracı | Evet | Linux/Win | `theHarvester -d {target} -l 100 -b all` |
| | Amass Enumeration | Kapsamlı açık kaynak (OSINT) subdomain taraması | Evet | Linux/Win | `amass enum -d {target} -passive` |
| | Sherlock | Sosyal medya hesaplarında kullanıcı adı araması | Evet | Linux/Win | `sherlock {target} --timeout 5` |
| | Google Dorks Tree | Interaktif dork arama bağlantıları (admin/login/pdf vb.) | Evet | Özel | `generate_dorks` handler |
| | Wayback Machine | archive.org üzerinden geçmiş URL ve endpoint tespiti | Evet | Özel | `wayback` handler |
| **DNS & Subdomain (ᛉ)** | DNS Enum | DNS kayıtları ve subdomain bulma aracı | Evet | Linux | `dnsenum --noreverse {target}` |
| | Subfinder | Hızlı ve pasif subdomain keşfi | Evet | Linux/Win | `subfinder` handler |
| | Assetfinder | Hafif ve sade subdomain tespiti | Evet | Linux/Win | `assetfinder --subs-only {target}` |
| | Fierce | IP bloğu ve zone-transfer DNS taraması | Evet | Linux/Win | `fierce --domain {target}` |
| | Knockpy | Kaba kuvvet (Brute-force) DNS subdomain taraması | Evet | Linux/Win | `knockpy` handler |
| | Gobuster DNS | Hızlı brute-force subdomain tespiti | Evet | Linux/Win | `gobuster_dns` handler |
| | Nslookup | Dahili DNS sorgulayıcı (Sisteme yerleşik) | Evet | Linux/Win | `nslookup -type=any {target}` |
| | Sublist3r | Çok motorlu (multi-engine) hızlı subdomain aracı | Evet | Linux/Win | `sublist3r -d {target}` |
| | DNS Recon | Gelişmiş DNS keşfi ve AXFR sorgu aracı | Evet | Linux/Win | `dnsrecon -d {target}` |
| | Dig (DNS Utils) | DNS kayıtları için doğrudan sorgu aracı | Evet | Linux/Win | `dig ANY {target}` |
| **Aktif Tarama (ᛦ)** | Nmap (Full Scan) | Hızlı servis ve port tanımlama taraması | Evet | Linux/Win | `nmap -sV -F --version-light {target}` |
| | WAF Detection | Web Uygulama Güvenlik Duvarı (WAF) tespiti (Wafw00f) | Evet | Linux/Win | `wafw00f {target}` |
| | Packet Sniffer | Canlı Tshark akışı kullanarak ağ trafiğini yakalama | Evet | Linux/Win | `tshark -c 5 -i any` |
| | Nikto Web Scan | Hedef sunuculardaki tehlikeli dosya ve zafiyetli sürümleri arama | Evet | Linux | `nikto -h {target} -Tuning 1` |
| | WPScan | WordPress kullanıcı arama ve zafiyet tespiti | Evet | Linux | `wpscan --url {target} --enumerate p --random-user-agent` |
| **Zafiyet Taraması (ᛟ)** | Exploit-DB Search | Yerel veritabanında exploit taraması (Searchsploit) | Evet | Linux | `searchsploit {target}` |
| | Lynis (System Hardening) | Sistem sertleştirme (Hardening) ve güvenlik denetimi aracı | Hayır | Linux | `lynis audit system` |
| | Nuclei (Vuln Scanner) | Hızlı ve özelleştirilebilir genel zafiyet tarayıcısı | Evet | Linux/Win | `nuclei -u {target}` |
| | Wapiti (Web Scanner) | Web uygulamaları için kapsamlı zafiyet tarayıcısı | Evet | Linux/Win | `wapiti -u {target}` |
| | Nmap (CVE Vulners) | Vulners script'i ile Nmap tabanlı CVE zafiyet taraması | Evet | Linux/Win | `nmap -sV --script vulners {target}` |
| | Hydra (Brute Force) | Paralel işlem gücüyle ağ login/parola kırma aracı | Evet | Linux/Win | `hydra_bruteforce` handler |
| | Sqlmap | SQL Enjeksiyonu tespiti ve sömürülmesi | Evet | Linux/Win | `sqlmap -u {target} --batch --banner` |
| | Commix | Otomatik komut enjeksiyonu (Command Injection) taraması | Evet | Linux/Win | `commix --url {target} --batch` |
| | Fenrir Hash Cracker | Gelişmiş GPU/CPU (AVX2/OpenCL) destekli parola kırıcı | Evet | Linux/Win | `fenrir_handler` |
| **Erebus Scanner (Rust) (ᛥ)** | Erebus Scanner | Banner alma, Proxy yönlendirme ve IDS atlatma özellikli multi-thread port tarayıcı | Evet | Linux/Win | `cargo run --manifest-path Runes/erebus-scanner/Cargo.toml` |
| **Kali Ghost Scripts (ᚷ)** | MAC Değiştir | MAC adresini rastgele (spoof) değiştirme | Hayır | Linux | `bash Runes/mac_degistir.sh` |
| | Kimlik Sorgula | Mevcut public metadata ve lokasyon sorgusu | Hayır | Linux | `bash Runes/sorgula.sh` |
| | Yeni IP (Tor) | Tor devreleri üzerinde aktif IP adresini yenileme | Hayır | Linux | `bash Runes/yeni_ip.sh` |
| **Gelişmiş SYN Taraması (ᛋ)** | Advanced SYN Scan | Yüksek hızlı özel TCP SYN port tarayıcı | Evet | Linux | `Runes/Advanced-SYN-Scanner/syn_scanner` |
| **GUI Ağ Trafiği İzleyici (ᛈ)** | Launch GUI Sniffer | Maven ile derlenmiş JavaFX grafik arayüzlü paket analiz aracı | Hayır | Linux/Win | `mvn javafx:run` (in sniffer dir) |
| **Mimir Scanner (ᛗ)** | Mimir Scanner | Gerçek zamanlı ağ trafiği analizi (Java Spring Boot + React) | Hayır | Linux/Win | `mimir_scanner` handler |
| **SnoopDork OSINT V3 (ᛞ)** | Launch SnoopDork OSINT | Dinamik ve Hedef odaklı OSINT Dork Üretici | Hayır | Linux/Win | Browser-based GUI |
| **Paket Enjektörü (ᛇ)** | Packet Injector | TCP SYN/ARP paketleri oluşturma ve enjekte etme aracı | Evet | Linux | `sudo python3 Runes/packet-injector/main.py` |
| **Bifrost Gateway (ᛒ)** | Bifrost Gateway | Spring Boot tabanlı yüksek performanslı siber güvenlik API Gateway'i | Hayır | Linux/Win | `mvn spring-boot:run` (in bifrost dir) |
| **Sistem İşlemleri (⚙️)** | Sync All Runes | Yerel araç depolarını (Github) güncel sürümlerle senkronize etme | Hayır | Özel | `update_modules` handler |

---

### ᛝ Özel Entegrasyonlar (My Runes)

Framework, **Runes** dizini altında derlenen özel yapım araçlarla genişletilmiştir:

1. **Fenrir Hash Cracker:** Gelişmiş GPU/CPU (AVX2/OpenCL) destekli parola (hash) kırıcı. Dictionary (Sözlük), Maske ve Kural tabanlı saldırıları destekler.
2. **Erebus Scanner (Rust):** Rust ile yazılmış gelişmiş ve yüksek hızlı ağ tarayıcısı. Özel bir UI (Arayüz) Modal penceresine sahiptir:
   * **Port Aralıkları ve Rastgele Seçim:** Portları karıştırarak temel IDS algoritmalarından (Intrusion Detection System) kaçınır.
   * **Banner Grabbing & Zafiyet Kontrolü:** Servisleri anında tanımlar ve CVE geçmişlerini kontrol eder.
   * **Adaptif Hız Sınırlandırma (Rate Limiting):** Ağ güvenlik duvarlarını tetiklememek için bağlantı hızını dinamik olarak kısıtlar.
   * **Proxy Desteği:** Aramaları Tor veya SOCKS5 proxy'leri üzerinden sorunsuzca yönlendirir.
3. **Kali Ghost Scripts:** Arayüze entegre edilmiş temel ağ manipülasyon araçları (MAC değiştirici, Genel IP sorgulama, Tor node'ları için IP yenileme).
4. **Advanced SYN Scanner:** Doğrudan web arayüzünden hedef rota belirleyebilen, otomatik ve manuel modlar sunan ayarlanabilir SYN port tarayıcı.
5. **GUI Sniffer (JavaFX & Maven):** Java ile kodlanmış; paket boyutlarını, protokolleri, kaynak/hedef IP adreslerini ve ağ aktivitesini grafiksel olarak izleyen çapraz platform paket dinleyicisi.
6. **SnoopDork V3:** Tamamen istemci tarafında (client-side) çalışan hedef odaklı bir OSINT Dork üretici. Gizlilik için "stealth mode" barındırarak Google, Shodan, GitHub, Pastebin vb. platformlar için kapsamlı sorgular üretir.
7. **Packet Injector:** Gelişmiş raw socket paket üretici ve enjektörü. TCP SYN enjeksiyonu, ARP Zehirlemesi (ARP Poisoning), gönderim hızı sınırlandırma (rate limits) ve ağ kartlarında bağımsız dinleme (sniffing) / ARP tespiti yapabilme özelliklerini destekler.
8. **Mimir Scanner:** Spring Boot arka uç (backend), pcap4j ve GeoIP2 altyapısıyla canlı paket dinleme ve WebSockets üzerinden React önyüzüne aktarım (real-time stream) sağlayan Ağ Trafik Analizörü.
9. **Bifrost Gateway:** Spring Boot tabanlı yüksek performanslı siber güvenlik API Ağ Geçidi (Gateway). Mjolnir WAF entegrasyonu sayesinde JSON/XML gövdelerini, Header'ları analiz eder; Caffeine Cache destekli Token-Bucket algoritmasıyla IP tabanlı Rate-Limiting ve DoS koruması sağlar.
10. **Dependency Manager (Runic Installation Ritual):** Kullanıcı sistemini (Windows/Linux) tarayarak eksik olan araçları tespit eder ve animasyonlu terminal arayüzü eşliğinde tüm bağımlılıkları tek tuşla otomatik olarak kurar.

---

### ᚛᚜ Sistem Kullanımı & Kurulum ᚛᚜

#### Kurulum Rehberi

Özel **Runes** modülleri birer Git Submodule olarak sisteme entegre edildiği için, projeyi klonlarken tüm modüllerin yüklenmesi adına `recurse-submodules` argümanını kullanmanız gerekmektedir:

```bash
# Projeyi tüm alt modülleriyle (submodules) beraber klonlayın
git clone --recurse-submodules https://github.com/mecik-arda/Yggdrasil-Security-Framework.git
cd Yggdrasil-Security-Framework
```

*Eğer projeyi daha önceden argümansız klonladıysanız, eksik alt modülleri indirmek için şu komutu çalıştırın:*
```bash
git submodule update --init --recursive
```

#### Ortam (Environment) Ayarları
Bilgisayarınızda (realm) Python 3.x ve Flask'in kurulu olduğundan emin olun. Sisteme entegre başlatıcı scriptleri kullanabilirsiniz:

**Linux/macOS İçin:**
```bash
chmod +x run.sh
./run.sh
```

**Windows İçin:**
```cmd
run.bat
```

*Veya manuel kurulum için:*
```bash
pip install -r requirements.txt
python app.py
```

---

### ᚦ Kullanım Protokolü

1. **Adım 1**: Orta kısımda bulunan giriş (input) alanına hedefin IP adresini veya Domain bilgisini girin.
2. **Adım 2**: Sol kısımdaki kategorilerden belirli bir "Rune" (Araç) seçin.
3. **Adım 3**: Sistemdeki genel durumu "Status Bar" üzerinden, aktif süreç ve çıktıları ise "Output Area" (Terminal) üzerinden izleyin.
4. **Adım 4**: İşlem tamamlandığında, bulgularınızı güvenli bir şekilde saklamak için "Artifact Export" butonlarını kullanın.

---

### Yasal Uyarı (Disclaimer)
Bu framework yalnızca eğitim amaçlı ve yetkili olduğunuz sistemlerde sızma testleri (penetration testing) gerçekleştirmeniz için geliştirilmiştir. Yazar, bu aracın herhangi bir kötüye kullanımından sorumlu tutulamaz.

### Lisans (License)
Bu proje MIT Lisansı altında lisanlanmıştır - detaylar için LICENSE dosyasına göz atabilirsiniz.

---
**Yazar**: Arda Meçik  
**Pozisyon**: Trakya Üniversitesi Bilgisayar Mühendisliği Öğrencisi  
**Öğrenci Numarası**: 1241602620
