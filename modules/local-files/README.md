# Yerel dosya modülü

`Catalog` model/depo katmanıdır; FastAPI denetleyicisi sabit ve kimlik doğrulamalı HTTP sözleşmesini sunar. React görünümü TanStack Query üzerinden bu sözleşmeyi tüketir. Çekirdeğin `SearchWidget` yuvası yalnız sorguyu iletir; modüller birbirlerinin iç sınıflarını çağırmaz. Modül kapatıldığında indeksleme durur, katalog korunur. Yeniden açıldığında değişiklikler uzlaştırılır.

## Kapsam

Kök ve dışlamalar yalnız makinedeki özel `config.json` ile tanımlanır. Bu kurulum `/Users/w6x` kökünü kapsar; Movies, Downloads, Desktop, Music, Public, Pictures, Applications, Yandex.Disk.localized ve Yandex.Disk dışarıdadır. Kullanıcının sonraki tercihiyle Library ve Documents/Codex ağacı da dışlanır; özel yapılandırmadaki gizli dizin, bağımlılık ve derleme kalıbı kuralları korunur. İndeksin kendi dizini de özyinelemeyi önlemek için dışlanır. Yol sınırları tam dizin sınırında ve çözümlenmiş hedef üzerinde kontrol edilir. Klasör symlink'leri takip edilmez; kapsam içindeki asıl hedefleri kökten taranır. Kapsam dışına çıkan bağlantılar kabul edilmez.

Okunabilen normal dosyaların adı, yolu, uzantısı, boyutu ve değişiklik zamanı kataloglanır. PDF, DOCX, XLSX (hücre/formül metinleri), PPTX (slayt ve not metinleri), Markdown, düz metin ve kod içerikleri ayrıştırılır. macOS'ta Swift/Vision ile taranmış PDF sayfaları ve görüntüler yerel OCR'dan geçer. Varsayılan giriş sınırı 256 MiB; metin çıktısı 128 MiB, belge ayrıştırma süresi 240 saniyedir. Limit, şifre veya bozuk dosya hataları açıkça gösterilir; yarım metin tamamlanmış sayılmaz. Desteklenmeyen biçimler ve kimlik doğrulama depoları yalnız adlarıyla kataloglanır. OCR doğruluğu görüntüye bağlıdır; Office içindeki gömülü resimler ve eski ikili DOC/XLS/PPT biçimleri bu okuyucu kapsamında değildir. İşletim sisteminin izin vermediği klasörler kapsam tamamlanmış gibi sayılmaz.

## Arama ve yaşam döngüsü

- SQLite WAL + FTS5: dosya adı/yolu ve belge parçaları için ayrı BM25 sıralamaları.
- Türkçe normalizasyonu ve kavram eşlemeleri; açık uzantılar OR filtresidir. “Dokümanım” ifadesi rastgele dosya türlerini dışlamaz.
- Yerel EmbeddingGemma 768 boyutlu vektörler, USearch HNSW ve karşılıklı sıra birleştirme. Model sunucusu yereldir; dosyalar buluta gönderilmez.
- İsteğe bağlı yerel BGE reranker. Kullanılamadığında kelime/vektör sıralaması korunur; kullanıcıya geri bildirim verilir.
- Dosya türü filtresi BM25 ve HNSW adayları seçilmeden uygulanır. Biçim başına en fazla dört bellekte tutulan HNSW indeksi kullanılır; yeni vektörler ve silmeler bu indekslere yansır. `go` gibi doğal sözcükler tür filtresi olmaz; `ext:go` açıktır.
- Belge arama niyetinde adı eşleşen Office belgelerine öncelik verilir; kod sonuçları silinmez. Sorgu vektörü ve aynı aday metinlerinin sıralaması kısa süreli önbelleklenir.
- İçerik SHA-256 ile tekilleştirilir; farklı yollar korunur. Değişmiş/silinmiş dosya eski içerikle sonuçlara giremez.
- Otomatik temizleyici, hiçbir güncel dosyanın kullanmadığı parçaları, FTS kayıtlarını, belge özet kayıtlarını ve bellek vektörlerini sınırlı gruplarla temizler. Ortak SHA bir dosyada kalıyorsa korunur.
- macOS dosya olayları ve 10 dakikalık tam uzlaştırma. Yeni/değişen dosyalar önceliklidir; ilk tarama kuyruğuna da düzenli işlem hakkı ayrılır. İlk tarama sürerken sonuçlar kısmidir.
- Ayrıştırıcılar Office/görüntü belgeleri için zaman ve bellek sınırı olan alt süreçte çalışır; kaynak dosyaları çalıştırmaz veya değiştirmez.

`/status`, `/search`, `/files/{id}`, `/refresh`, `/control`, `/health` uçları kimlik doğrulaması gerektirir. Tarayıcı yerel anahtarı görmez; Open Notebook modül geçidi kullanır. Özgün dosyanın indirilmesi kullanıcı tıklaması gerektirir. Klasör veya dosya yolu HTTP isteğiyle değiştirilmez.

Yerel dosyalar genel Search ekranına ve `/files` sayfasına eklenir. Belirli not defterleri seçildiğinde bilgisayar dosyaları gösterilmez. Ask'in not defteri kaynak kapsamı bu modülle genişletilmez; dosyayı Ask bağlamına almak için Open Notebook'a kaynak olarak ekleyin.

## Çalıştırma

`service/requirements.txt` bağımlılıklarını ayrı sanal ortama kurun. `LOCAL_FILES_HOME` içindeki `config.json` örneği `service/config.example.json` dosyasındadır. Aynı dizine rastgele `.key` koyun, dosya izinlerini 0600 yapın. `python service/install.py` yerel kodu ve bağımlılıkları kurar, macOS OCR ikilisini derler ve LaunchAgent hazırlar. Mevcut `config.json`, dışlamalar ve anahtar korunur; güncelleme bu değerleri varsayılanlarla değiştirmez. Servisi ayrıca yükleyin/yeniden başlatın veya `python -m uvicorn server:app --host 0.0.0.0 --port 8322` çalıştırın. Kalıcılık bu kurulumda `local.open-notebook.files` LaunchAgent'iyle sağlanır.

Open Notebook'ta `LOCAL_FILES_URL`/`LOCAL_FILES_KEY` ortam değişkenleri veya dağıtıma ait `data/module-services.json` kullanılır:

```json
{"local-files":{"url":"http://host.lima.internal:8322","key_file":"/app/data/local-files/.key"}}
```

Geri alma: modülü Ayarlar'dan kapatın; gerekirse LaunchAgent'i durdurun. Katalog ve kaynak dosyalar korunur. Vektör belleği açılışta SQLite'tan yeniden oluşturulur; ayrı ve eski bir vektör dosyasına güvenilmez.


Doğrulama: hizmet sanal ortamında `python -m pytest modules/local-files/tests -q`. Yerel OCR ikilisi `swiftc service/ocr.swift -o service/ocr` ile derlenir; ikili Git içine konmaz. Yeni ayrıştırıcı sürümü, önceki metadata-only/boyut/okuma hatalarını yeniden sıraya alır; başarılı içerikler yeniden yazılmaz. Anlamsal kapsam, içerik indeksinden sonra oluşur; `/search.partial_index` vektör kuyruğu boşalmadan tamamlanmış demez.
