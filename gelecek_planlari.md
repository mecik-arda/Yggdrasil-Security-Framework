# Yggdrasil - Gelecek Planlaması ve Öneriler

## Faz 1: Kod Kalitesi ve Güvenilirlik (Code Quality & Reliability)

### 1. Test Altyapısı (Unit & Integration Testing)
**Sorun:** Proje büyüdükçe yapılan yeni bir kod değişikliğinin eski bir aracı bozup bozmadığını elle test etmek zorlaşır.
**Öneri:** Projeye `pytest` tabanlı bir test altyapısı kurabilirsiniz. Araçların doğru parametrelerle çağrılıp çağrılmadığını, veritabanı fonksiyonlarının (örneğin `core/db.py`) doğru çalışıp çalışmadığını otomatize edebilirsiniz.

### 2. Otomatik CI/CD Hatları (GitHub Actions)
**Sorun:** Kodu Github'a gönderiyorsunuz ancak eklediğiniz yeni özelliklerin eski kod yapısını veya güvenlik standartlarını (kodlama hataları) bozup bozmadığını anında göremiyorsunuz.
**Öneri:** Bir `/.github/workflows/` dosyası oluşturarak GitHub Actions kurabilirsiniz. Böylece her `git push` yaptığınızda kodunuz otomatik testlerden (önceki maddede bahsettiğimiz `pytest`), kod kalitesi (linting) analizlerinden geçer.

---

## Faz 2: Performans ve Ölçeklenebilirlik (Performance & Scalability)

### 3. Güçlü Bir Asenkron Görev Yöneticisi (Celery & Redis)
**Sorun:** Şu anki sistemde taramalar (`nmap`, `whois` vb.) arka planda Python'un standart `threading` modülü ile çalıştırılıyor. Eşzamanlı 50 tarama başlatıldığında sistem kaynakları tükenebilir veya ana uygulama (Flask) çökebilir.
**Öneri:** Arka plan işlemleri için Celery gibi bir görev kuyruğu (task queue) ve aracı olarak Redis kullanılabilir. Böylece aynı anda sadece belirli sayıda tarama çalışır, geri kalanlar kuyruğa alınır ve işlemler çok daha güvenli yürütülür.

### 4. Gerçek Zamanlı İletişim (WebSocket / Socket.IO)
**Sorun:** Ön yüzdeki (frontend) terminal, arkadaki aracın bitip bitmediğini öğrenmek için sürekli sunucuya istek (polling) atıyor. Bu durum gereksiz ağ trafiği yaratır.
**Öneri:** Uygulamaya Flask-SocketIO entegre ederek WebSockets altyapısına geçebilirsiniz. Böylece bir taramanın sonucu veya yeni bir C2 bağlantısı (zombie) geldiğinde, sunucu bunu doğrudan arayüze anında (real-time) iletebilir. Arayüzünüz çok daha akıcı hale gelir.

---

## Faz 3: Gözlemlenebilirlik ve Log Yönetimi (Observability)

### 5. Kapsamlı Merkezi Hata Yönetimi
**Sorun:** Framework içerisindeki araçların çalışması sırasında (örneğin hedef makineye ulaşılamaması veya bir kütüphane eksikliği) alınan hataların takibi zor olabilir.
**Öneri:** Sistem loglarını (`.log` dosyaları) sadece arayüzde göstermek yerine; uygulamanın ne zaman ve nerede hata verdiğini izlemek için projeye ufak bir Sentry veya ELK stack benzeri basit bir "Merkezi Log Dashboard" paneli eklenebilir.
