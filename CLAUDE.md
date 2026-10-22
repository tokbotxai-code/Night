# Night: zasady kanału

Kanał TikTok z **oryginalnymi** horror stories po angielsku, rynek **USA/UK**.
Format: faceless, 9:16, 60–75 s. Lektor AI, tła AI, napisy słowo po słowie, efekty dźwiękowe.
Ten plik jest źródłem prawdy dla ludzi i dla autopilota. Ustawienia techniczne są w `channel.json`.

## 1. Treść (najważniejsze)

- **Tylko oryginalne historie.** Nie przerabiaj creepypast, wątków z r/nosleep, filmów, odcinków ani cudzych TikToków.
  Wolno korzystać ze znanych motywów (pukanie o 3:00, ktoś podszywa się pod bliską osobę), ale fabuła, twist i zdania muszą być nasze.
- **Fikcja to fikcja.** Nigdy nie piszemy „true story”, „this really happened”, „based on real events”.
  Bez prawdziwych osób, zbrodni, ofiar, miejscowości z nazwy ani marek.
- **Bez naruszeń zasad TikToka:** bez gore, krwi w kadrze, samookaleczeń, broni wymierzonej w ludzi, przemocy wobec dzieci i zwierząt
  oraz treści seksualnych. Strach budujemy sugestią: cień, dźwięk, wiadomość, ktoś, kto się nie odwraca.
- **Język:** amerykański angielski (US spelling, „mom”, „a.m.”), zrozumiały też w UK. Bez slangu tylko z jednego kraju.
- Narracja w 1. osobie, czas przeszły, krótkie zdania (najlepiej poniżej 12 słów). 120–140 słów na film.

### Struktura (sprawdzona na filmie #1)

| Czas | Element | Zasada |
|---|---|---|
| 0–3 s | **Hook** | Pierwsze zdanie zawiera cały niepokojący konflikt. Ten sam hook na ekranie (`hook_text`). |
| 3–8 s | Sprzeczność | Zdanie, które zmienia sens hooka („…mama siedziała obok mnie”). Pod nie mocny `hit`. |
| 8–35 s | Eskalacja | Co 4–7 s nowy sygnał (dźwięk, wiadomość, cień). Zmiana kadru co 3–6 s. |
| 35–55 s | **Twist** | Odwraca to, w co widz uwierzył. Najlepiej jako SMS albo szept. |
| 55–65 s | Obraz końcowy | Powolny ruch, cięcie do czerni. Bez wyjaśniania. |
| ostatnie 5 s | Pytanie + pętla | Pytanie z wyborem A/B do komentarzy, a ostatni kadr = pierwszy kadr (zapętlenie). |

## 2. Produkcja

```
pip install -r requirements.txt          # + ffmpeg w systemie
python3 tools/make_video.py stories/<id>/story.json --preview   # szybki podgląd 540x960
python3 tools/make_video.py stories/<id>/story.json             # finał 1080x1920
```

- Wynik trafia do `output/<id>/`: `final.mp4`, `cover.jpg`, `captions.srt`, `post.json` (katalog w `.gitignore`).
- Skrypt **przerywa pracę**, gdy film ma mniej niż 60 s lub więcej niż 75 s. Długość koryguj tekstem i pauzami `pre`/`post`, nie flagą.
  Orientacyjnie: 1 słowo ≈ 0,42 s przy `rate: +4%`.
- Lektor: `edge-tts`, głos kanału **en-US-ChristopherNeural**, `rate +4%`, `pitch -4Hz`. Nie zmieniaj głosu między filmami (rozpoznawalność).
- Tła: Pollinations (darmowe, bez klucza). Darmowy limit zwraca błąd 402 lub 429, a skrypt sam ponawia z odstępem.
  Obrazy są cache'owane po prompcie, więc ten sam prompt daje ten sam kadr (tak robimy pętlę).
- Prompty obrazów: opis kadru po angielsku, bez tekstu w obrazie. **Nie pokazuj twarzy wprost** (cień, tył głowy, rozmycie).
  Styl dokleja `style_prompt` z pliku historii, więc trzymaj go identycznym między filmami.
- Dźwięki są syntetyzowane w `tools/sfx.py` (bez licencji zewnętrznych): `vibrate`, `hit`, `knock3`, `creak`, `tv`, `drone`, `riser`, `heartbeat`.
- Głośność: loudnorm −14 LUFS. Bitrate ograniczony do 4 Mb/s, więc plik ma około 30–40 MB (mieści się w GitHubie i Metricool).

### Kontrola jakości przed publikacją (obowiązkowa)

1. Długość 60–75 s (skrypt to pilnuje).
2. Zrób arkusz klatek (`ffmpeg ... -vf tile=5x3`) i obejrzyj go: żadnych napisów, logo ani zniekształconych twarzy w tłach, nic nie zasłania napisów.
   Złe tło wymień: zmień prompt i wyrenderuj ponownie.
3. Napisy nie mogą wchodzić w dolne 20% ekranu ani w prawy pas 120 px (tam jest interfejs TikToka). Skrypt trzyma się tych stref.

## 3. Format `story.json`

```jsonc
{
  "id": "002-krotki-slug",             // numer kolejny + slug, taki sam jak nazwa katalogu
  "title": "...",                      // roboczy tytuł (tytuł TikToka)
  "voice": "en-US-ChristopherNeural", "rate": "+4%", "pitch": "-4Hz",
  "style_prompt": "...",               // skopiuj z 001 bez zmian
  "hook_text": "...",                  // tekst hooka na górze ekranu
  "hook_scenes": 2,                    // przez ile pierwszych scen widać hook
  "scenes": [{
    "narration": "...",                // "" = scena bez lektora (np. pętla)
    "pre": 0.1, "post": 0.4,           // pauzy w sekundach
    "shots": [{"prompt": "...", "motion": "zoom_in|slow_zoom_in|zoom_out|pan_right|shake"}, {"black": true}],
    "flicker": true,                   // migotanie jak od telewizora
    "captions": true,
    "sfx": [{"type": "hit", "at_word": "next"}, {"type": "tv", "at": 0.0, "until": "end", "gain": 0.5}],
    "overlays": [
      {"kind": "sms", "sender": "Mom", "text": "...", "time": "3:12 AM", "at_word": "Open", "until": "end", "slot": 0},
      {"kind": "title", "text": "...", "at": "end", "until": 3.0},
      {"kind": "choice", "text": "DOOR  or  COUCH", "at_word": "door", "until": "end"}
    ]
  }],
  "post": {"caption": "...", "tiktok_title": "...", "cover_ms": 1500}
}
```

Znaczniki czasu: `at` to sekundy od początku sceny albo `"end"` (koniec lektora), `at_word` to pierwsze wystąpienie słowa w narracji sceny,
`until` to `"end"` (koniec sceny) albo długość w sekundach.

## 4. Publikacja (Metricool)

- **Tylko marka `nightstories.tv` (blogId 7593858, TikTok @nightstories.tv, strefa marki Europe/London)**, zgodnie z `channel.json`. Marka `pepsafe.info` (blogId 7506075) to inny projekt: **nigdy** tam nie publikuj.
  Jeśli marki kanału nie ma albo nie ma podpiętego TikToka (`networksData.tiktokData`), zatrzymaj się i zgłoś to. Nie publikuj gdzie indziej.
- Plik wideo musi mieć publiczny URL. Po commicie skopiuj `final.mp4` i `cover.jpg` do `published/<id>/` i użyj
  `https://raw.githubusercontent.com/tokbotxai-code/Night/<branch>/published/<id>/final.mp4`. Przed planowaniem sprawdź, że URL zwraca 200.
- `createScheduledPost`: `providers: [{"network":"tiktok"}]`, `text` = `post.caption`, `tiktokData`:
  `{"title": tiktok_title, "privacyOption": "PUBLIC_TO_EVERYONE", "isAigc": true, "autoAddMusic": false}`
  (oznaczenie AI jest obowiązkowe), `videoCoverMilliseconds` = `post.cover_ms`.
- Godziny: wieczór we wschodnich USA, **19:00–21:30 America/New_York** (w UK to 0:00–2:30, czyli nocny scroll).
  `publicationDate` podawaj w strefie marki (Europe/London), więc przelicz godzinę z ET (zwykle +5 h, a +4 h w tygodniach, gdy w USA i UK obowiązuje inny czas).
  Gdy konto ma już dane, użyj `getBestTimeToPostByNetwork`. Na start 1 film dziennie, nie częściej niż co 20 h.
- Opis: 1 zdanie z pytaniem A/B i emoji, potem 4–6 hashtagów (`#horrortok #scarystories #creepy #horrorstory #fyp` i 1 tematyczny).
- Po zaplanowaniu dopisz wiersz do `stories/LOG.md`: id, data i godzina publikacji, długość, link plannera.

## 5. Repo

- `tools/make_video.py`: renderer, `tools/sfx.py`: syntezator efektów.
- `stories/<id>/story.json`: scenariusze, `stories/LOG.md`: log publikacji i bank pomysłów (nie powtarzaj motywu z ostatnich 10 filmów).
- `published/<id>/`: wideo i okładki do publikacji (publiczny URL dla Metricool).
- `AUTOPILOT.md`: polecenie dla zadania cyklicznego.
- Fonty: Anton (OFL) w `assets/fonts/`.
