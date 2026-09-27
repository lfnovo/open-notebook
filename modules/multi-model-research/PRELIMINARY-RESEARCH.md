# Tarayıcısız ön araştırma

Yeni işler varsayılan olarak mevcut dört aşamanın önünde bir ön araştırma aşamasıyla başlar. Ayarlardan veya iş oluştururken kapatılabilir. Eski işler sekiz görevli kalır; yeni ve ön araştırması açık işler on iki görevlidir.

1. `pre_research_gemini`, `pre_research_chatgpt`, `pre_research_claude`: aynı özgün soru ve kapsamla, birbirinin çıktısını görmeden hesap CLI'larıyla kaynak araması.
2. `pre_brief_chatgpt`: üç raporun tamamından birleşik Markdown araştırma taslağı. Zorunlu uzlaşma üretmez; kaynakları ve çözülemeyen ayrışmaları korur.
3. Mevcut dört aşama ve sekiz görev: taslak ve özgün ön raporlar değişmez kanıt paketine katılır. Web araştırmaları yine mevcut Chrome uzantısını kullanır; ön aşama kullanmaz.

Kullanıcının sorusu yeniden yazılmaz. Her ön çıktı, hash'i ve kaynaklarıyla ayrı rapordur; arayüzden Markdown olarak indirilebilir ve toplu dışa aktarmaya dahildir. Bir hesap başarısız olursa tamamlanan kardeş görevler tekrarlanmaz. Üç araştırma bitmeden birleşim, birleşim bitmeden sonraki araştırmalar başlamaz.

## Hesap profilleri

Yeni `preliminary_research` ve `preliminary_merge` profilleri mevcut sentez profilinden ayrıdır. Eski sentezin modeli, komutları, kalibrasyon parmak izi ve bütçesi değiştirilmedi. Ön aşama yeni ve muhafazakâr token ölçümü kullanır. Hiçbir girdi kesilmez; daha fazla rapor bütçeyi aşarsa mevcut bağlam denetimi açık hata verir.

Kurulumda gerçekten görülen seçenekler:

| Hesap | İstenen model | Efor |
|---|---|---|
| ChatGPT | gpt-6-astra | ultra |
| Claude | claude-fable-5-1 | max |
| Gemini | gemini-3.1-pro-high | high |

Hesap CLI'sında “Gemini Ultra” veya “Fable extra” adlı seçenek görülmedi. Model/efor `preliminary_cli_model` ve `preliminary_effort` ile dağıtım yapılandırmasında seçilebilir. Otomatik model düşürme yapılmaz; kota ve oturum engelleri kullanıcıya gösterilir. İstenen model ile sağlayıcının bildirdiği gerçek model farklı alanlardır; bildirilmeyen kimlik doğrulanmış sayılmaz.

Araştırma profilinde gerçek web arama ve kaynak okuma araç izi aranır. Modelin “araştırdım” yazması yeterli değildir. Claude yalnız WebSearch/WebFetch alır; Codex'te web araçları açılırken komut, alt ajan ve bilgisayar araçları kapalı kalır. Gemini'nin dar personası web arama/okuma içindir; CLI'ın kendi ürettiği web önbelleğini okuması ayrıca ayrılır. Kullanıcı dosyaları araştırma profilinin girdisi yapılmaz. Kaynak içerikleri talimat sayılmaz.

## Doğrulama sınırı

Üç gerçek hesap CLI'ı kısa, kamuya açık bir soruda web aradı ve sayfa okudu. Bu gerçek çıktılar köprü ayrıştırıcısından tekrar geçirildi. On iki görevli sıra, bekleme koşulları ve yeniden deneme davranışı yalıtılmış sağlayıcılarla sınandı. Yeni iş akışının tamamı uzun ve ücret/kota tüketen yeni bir gerçek Deep Research işiyle tekrar çalıştırılmadı; mevcut sekiz görevli kullanıcı raporları değişmedi.
