# ᚛᚜ Yggdrasil Security Framework - Yeni Tool Önerileri ᚛᚜

Bu not, Yggdrasil Security Framework'ü genişletmek için önerilen yeni rünlerin (araçların) listesidir.

---

### 1. Passive Reconnaissance (ᚠ) - Huginn & Muninn OSINT (ᚼ)
* **Teknoloji:** Python (FastAPI) + React (Frontend tarafına entegre)
* **Açıklama:** Odin'in dünyayı gezip ona haber getiren iki kuzgunundan esinlenen bu araç; hedef alan adı, e-posta veya kullanıcı adı üzerinden veri sızıntılarını (data leaks), sosyal medya profillerini ve açık kaynaklı istihbarat (OSINT) verilerini tarayıp tek bir görsel raporda birleştirir. SnoopDork_V3 ile entegre çalışabilir.

### 2. DNS & Subdomain (ᛉ) - Bifröst DNS Bridge (ᛒ)
* **Teknoloji:** Go (Golang)
* **Açıklama:** Dokuz diyarı birbirine bağlayan gökkuşağı köprüsü Bifröst gibi, hedef sistemin DNS alt yapısını ve subdomain haritasını çıkarır. Çok iş parçacıklı (multi-threaded) DNS resolver ve zone transfer testleri gerçekleştirir. Go dilinin hızıyla binlerce subdomain'i saniyeler içinde çözümler.

### 3. Active Scanning (ᛦ) - Gungnir Port-Spear (ᚷ)
* **Teknoloji:** Rust (Tokio)
* **Açıklama:** Odin'in asla hedefinden şaşmayan mızrağı Gungnir. erebus-scanner ve Advanced-SYN-Scanner'ı tamamlayacak, IDS/IPS sistemlerini atlatmak için fragmente edilmiş (parçalanmış) paketler gönderen ve decoy (sahte) IP adresleriyle tarama yapan ultra stealth bir port scanner.

### 4. Vulnerability (ᛟ) - Loki Fuzzer / Web Exploit Kit (ᛚ)
* **Teknoloji:** Python / Go
* **Açıklama:** Kılık değiştirme ve hile tanrısı Loki. Web uygulamalarındaki gizli dizinleri, parametreleri ve API uç noktalarını (endpoints) bulmak için dinamik payload'lar üreten akıllı bir fuzzer. WAF bypass senaryoları için payload'ları otomatik olarak encode eder (URL, Base64, Hex) ve XSS, SQLi, LFI açıklıklarını kılık değiştirerek test eder. mimir-scanner'ın tarama motoruna entegre edilebilir.

### 5. Kali Ghost Scripts (ᚷ) - Sleipnir Route-Shifter (ᛋ)
* **Teknoloji:** Bash + Python
* **Açıklama:** Odin'in 8 bacaklı efsanevi atı Sleipnir. Sistem genelindeki ağ trafiğini dinamik olarak çoklu VPN tünelleri, Tor devreleri ve şifreli proxy zincirleri üzerinden rastgele yönlendirerek analiz yapan kişinin izini tamamen kaybettirir. Mevcut Kali-Ghost-Scripts setine eklenebilir.

### 6. GUI Traffic Analyzer & Mimir (ᛈ / ᛗ) - Jörmungandr Network Flow Visualizer (ᛃ)
* **Teknoloji:** JavaScript (D3.js / Three.js) + Java/Spring (Mimir Backend)
* **Açıklama:** Dünyayı saran devasa yılan Jörmungandr. Network-Sniffer-Scanner-Java veya packet-injector'den gelen anlık paket akışlarını (network flows) 3 boyutlu, hareketli bir ağ topolojisi grafiğine dönüştüren göz alıcı bir görselleştirme aracı. Ağdaki cihazlar ve veri akışları yılanın boğumları gibi ekranda dinamik olarak canlanır.

### 7. Packet Injector (ᛇ) - Mjölnir Flood-Engine (ᚦ)
* **Teknoloji:** C / Rust (Raw Sockets)
* **Açıklama:** Thor'un şimşekler çaktıran çekici Mjölnir. Güvenlik testlerinde sistemlerin yük kaldırma kapasitesini ölçmek amacıyla tasarlanmış, yüksek performanslı ve kontrollü bir TCP/UDP/ICMP flooding (stress test) aracıdır. packet-injector kütüphanesini kullanarak raw soket seviyesinde çalışır.

---

## ᛝ Yeni Runic Kategoriler

### 8. Wireless & RF Security (ᚺ - Heimdall) - Heimdall WiFi-Sentry
* **Teknoloji:** Python (Scapy) + C
* **Açıklama:** Bifröst'ün bekçisi, her şeyi gören ve duyan Heimdall. Çevredeki kablosuz ağları (Wi-Fi) dinleyen, yetkisiz cihazları (Rogue AP) tespit eden, otomatik deauthentication saldırısı düzenleyip WPA el sıkışmalarını (handshake) yakalayan bir wireless denetim aracı.

### 9. Post-Exploitation & C2 (ᚱ - Ratatoskr) - Ratatoskr C2 Agent
* **Teknoloji:** Go (Agent) + Python/React (Kontrol Paneli)
* **Açıklama:** Yggdrasil ağacının dalları ve kökleri arasında haber taşıyan sincap Ratatoskr. Sızma testi sırasında hedef makinelerde çalıştırılmak üzere tasarlanmış; şifreli iletişim kanalları (HTTPS/DNS) kullanan, hafif, polymorphic (kendini gizleyebilen) bir komut-kontrol ajanı ve dinleyicisi.

### 10. Cryptography & Hash Auditing (ᚠ - Fenrir) - Fenrir Hash Cracker
* **Teknoloji:** C++ / OpenCL (GPU desteği için)
* **Açıklama:** Zincirleri parçalayan devasa kurt Fenrir. Yakalanan şifre özetlerini (hash) çözmek için sözlük (dictionary) ve brute-force saldırılarını GPU ivmeli olarak çalıştıran veya popüler API'lerden (LeakLookup, Hashkiller vb.) sorgulayan hızlı bir şifre analiz aracı.
