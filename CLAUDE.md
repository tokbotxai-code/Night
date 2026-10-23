# Night: zasady kanału

Kanał TikTok z **oryginalnymi** horror stories po angielsku, rynek **USA/UK**.
Format: faceless, 9:16, **61–90 s** (Creator Rewards płaci od 61 s, a krótsze filmy mają wyższy % obejrzeń do końca). Lektor AI, tła AI, napisy słowo po słowie, efekty dźwiękowe.
Ten plik jest źródłem prawdy dla ludzi i dla autopilota. Ustawienia techniczne są w `channel.json`.

## 1. Treść (najważniejsze)

- **Tylko oryginalne historie.** Nie przerabiaj creepypast, wątków z r/nosleep, filmów, odcinków ani cudzych TikToków.
  Wolno korzystać ze znanych motywów (pukanie o 3:00, ktoś podszywa się pod bliską osobę), ale fabuła, twist i zdania muszą być nasze.
- **Fikcja to fikcja.** Nigdy nie piszemy „true story”, „this really happened”, „based on real events”.
  Bez prawdziwych osób, zbrodni, ofiar, miejscowości z nazwy ani marek.
- **Bez naruszeń zasad TikToka:** bez gore, krwi w kadrze, samookaleczeń, broni wymierzonej w ludzi, przemocy wobec dzieci i zwierząt
  oraz treści seksualnych. Strach budujemy sugestią: cień, dźwięk, wiadomość, ktoś, kto się nie odwraca.
- **Język:** amerykański angielski (US spelling, „mom”, „a.m.”), zrozumiały też w UK. Bez slangu tylko z jednego kraju.
- Narracja w 1. osobie, czas przeszły, krótkie zdania (najlepiej poniżej 12 słów). **160–200 słów na film** (Kokoro: zmierzone na 005, 160 słów + 8,5 s pauz = 63,5 s). Jeśli polecenie zadania podaje mniej słów, obowiązuje ta reguła.

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
- Cel: **65–90 s**. Film powyżej 90 s skróć tekstem. Skrypt przerywa pracę dopiero poniżej 61 s lub powyżej 180 s (bezpiecznik). Długość koryguj tekstem i pauzami `pre`/`post`, nie flagą.
  Orientacyjnie (Kokoro, speed 0.9): 1 słowo ≈ 0,34 s plus pauzy (zwykle ok. 8 s). Celuj w ≥ 65 s, żeby mieć zapas nad limitem 61 s.
- Lektor (od odcinka 005): **Kokoro** (licencja Apache 2.0, bezpieczna przy zarabianiu), głos **am_michael**, `speed 0.9`.
  W story.json: `"tts": "kokoro", "voice": "am_michael", "speed": 0.9` (skopiuj z 001). Modele (~350 MB) skrypt pobiera sam do `~/.cache/kokoro`.
  **Nie używaj edge-tts** w nowych filmach (niejasna licencja komercyjna; nie ma go w requirements.txt, ponowny render 001–004 wymaga `pip install edge-tts`). Odcinki 001–004 zostały nagrane edge-tts i zostają bez zmian.
  Kokoro nie podaje czasu słów: skrypt nagrywa każde zdanie osobno (dokładny początek zdania, pauza 0,28 s) i szacuje słowa tylko wewnątrz zdania. Krótkie zdania = najlepsza synchronizacja.
- Tła: Pollinations (darmowe, bez klucza). Darmowy limit zwraca błąd 402 lub 429, a skrypt sam ponawia z odstępem.
  Obrazy są cache'owane po prompcie, więc ten sam prompt daje ten sam kadr (tak robimy pętlę).
- Prompty obrazów: opis kadru po angielsku, bez tekstu w obrazie. **Nie pokazuj twarzy wprost** (cień, tył głowy, rozmycie).
  Styl dokleja `style_prompt` z pliku historii, więc trzymaj go identycznym między filmami.
- Dźwięki są syntetyzowane w `tools/sfx.py` (bez licencji zewnętrznych): `vibrate`, `hit`, `knock3`, `creak`, `tv`, `drone`, `riser`, `heartbeat`.
- Głośność: loudnorm −14 LUFS. Bitrate do 2 Mb/s: film ma ok. 7–20 MB.

### Kontrola jakości przed publikacją (obowiązkowa)

1. Długość 61–90 s (cel 65–90 s; skrypt blokuje tylko <61 s i >180 s).
2. Zrób arkusz klatek (`ffmpeg ... -vf tile=5x3`) i obejrzyj go: żadnych napisów, logo ani zniekształconych twarzy w tłach, nic nie zasłania napisów.
   Złe tło wymień: zmień prompt i wyrenderuj ponownie.
3. Napisy nie mogą wchodzić w dolne 20% ekranu ani w prawy pas 120 px (tam jest interfejs TikToka). Skrypt trzyma się tych stref.

## 3. Format `story.json`

```jsonc
{
  "id": "002-krotki-slug",             // numer kolejny + slug, taki sam jak nazwa katalogu
  "title": "...",                      // roboczy tytuł (tytuł TikToka)
  "tts": "kokoro", "voice": "am_michael", "speed": 0.9,  // skopiuj z 001 (odcinki 001–004 były na edge-tts)
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
- **Wideo NIE trafia do historii repo** (od 23.10.2026, bo repo rosło o ~35 MB na film). Do `published/<id>/` kopiuj tylko
  `cover.jpg`, `captions.srt` i `post.json` (`published/*/final.mp4` jest w `.gitignore`).
  Wideo wysyłasz poleceniem `python3 tools/upload_media.py <id>`. Skrypt wrzuca je na osobny branch `media` (nie mieszaj go z night-autopilot)
  i wypisuje publiczny URL `https://raw.githubusercontent.com/tokbotxai-code/Night/media/<id>/final.mp4`, gdy ten już zwraca 200.
  Ten URL podajesz w `createScheduledPost` (Metricool kopiuje plik do siebie przy planowaniu).
  Jeśli polecenie zadania mówi o URL `.../night-autopilot/published/<id>/final.mp4`, ta reguła je zastępuje.
  Starych MP4 z historii nie usuwaj ani nie przepisuj (żadnego force-push).
- `createScheduledPost`: `providers: [{"network":"tiktok"}]`, `text` = `post.caption`, `tiktokData`:
  `{"title": tiktok_title, "privacyOption": "PUBLIC_TO_EVERYONE", "isAigc": true, "autoAddMusic": false}`
  (oznaczenie AI jest obowiązkowe).
- **Harmonogram w czasie USA (America/New_York, ET), czyli wieczór w USA (decyzja właściciela z 23.10.2026):**
  - do 28.10.2026: **1 film dziennie o 20:00 ET**,
  - od 29.10.2026: **2 filmy dziennie: 19:00 ET i 22:00 ET**.
  - Strefa marki w Metricool to Europe/London. Godzinę ET przelicz w Pythonie (`zoneinfo`) na Europe/London i taką wyślij w `publicationDate`.
    Gdy wynik wypada w nocy zmiany czasu w UK (ostatnia niedziela października, 01:00–02:00 UK), przesuń slot o 1 h wcześniej.
  - Godzin nie zmieniaj na własną rękę. Zmiany wprowadza tylko właściciel.
- Konto TikTok jest **osobiste** (Creator Rewards), więc własna okładka nie działa: nie wysyłaj `videoThumbnailUrl`/`videoCoverMilliseconds`.
- Opis: 1 zdanie z pytaniem A/B i emoji, potem 4–6 hashtagów (`#horrortok #scarystories #creepy #horrorstory #fyp` i 1 tematyczny).
- Po zaplanowaniu dopisz wiersz do `stories/LOG.md`: id, data i godzina publikacji, długość, link plannera.

## 5. Canva Business (od 23.10.2026)

- Właściciel ma **Canva Business**, podłączoną przez narzędzia `mcp__Canva__*`. Używaj jej do warstwy wizualnej:
  sceny i tła (obrazy AI, zdjęcia i filmy premium), animacje (powolne przybliżanie, glitch, winieta),
  czołówka, styl napisów, okładki serii („Part 1/3”), zmiana formatu na 9:16.
- Styl marki „Night Stories” jest w `assets/brand.json` (kolory, czcionki, styl). W Canvie **nie zakładamy zestawu marki**
  (konto Business jest współdzielone). Podawaj styl z pliku w każdym projekcie i nigdy nie używaj materiałów PepSafe.
- Eksporty z Canvy (JPG/PNG) zapisuj w `stories/<id>/`. Gotowy film idzie przez `tools/upload_media.py` (branch `media`, sekcja 4), nigdy do repo.
- Obrazy lub wideo z AI → `tiktokData.isAigc: true`.
- Zasady TikToka: bez krwi i przemocy na zbliżeniach, bez samookaleczeń. Historie 61–90 s.
- Praktyka (test 23.10): `generate-image` zwraca tylko miniaturę, a pełna rozdzielczość wymaga projektu i eksportu.
  Dlatego Canvy używaj do 1–2 kluczowych kadrów na film (hook, twist) i do okładek serii. Eksport zapisz w `stories/<id>/`
  i podaj w ujęciu jako `{"image_file": "hook.png", "motion": "zoom_in"}`. Pozostałe tła generuje Pollinations.
- Planu konta Canva i liczby kredytów nie da się sprawdzić przez narzędzia. Gdy funkcja premium odmówi,
  napisz to w podsumowaniu i dokończ film zwykłym rendererem (`tools/make_video.py`).

## 6. Rozwój kanału (rutyna autopilota)

- **Przed pisaniem scenariusza** pobierz z Metricool statystyki TikToka z ostatnich 14 dni (views, likes, comments, shares,
  średni czas oglądania, % obejrzeń do końca). Krótko porównaj filmy w raporcie.
- **Co działa, rób więcej:** motyw lub format filmu, który ma najwięcej wyświetleń i najdłuższy czas oglądania, powtarzaj
  (ten sam typ hooka i grozy), ale nigdy tej samej historii. Słabe motywy przesuń na koniec banku pomysłów.
- **Serie:** gdy film ma co najmniej 2 razy więcej wyświetleń niż średnia kanału, zrób jego kontynuację „Part 2” jako następny film
  (hook: „Part 2: …”, okładka z „PART 2”). Maksymalnie 3 części.
- **Hook testy:** naprzemiennie hook-pytanie i hook-zdarzenie. W LOG.md zapisuj typ hooka, żeby dało się porównać.
- **Komentarze:** pytanie A/B na końcu filmu i w opisie, plus `firstCommentText` z pytaniem rozszerzającym (np. „What would you text back? 👇”).
- **Bank pomysłów:** gdy zostanie mniej niż 5 pomysłów, dopisz 10 nowych, oryginalnych.
- W raporcie dodaj 1 zdanie: czego się nauczyliśmy i co zmieniasz w najbliższym filmie.

## 7. Decyzje (ustalenie właściciela, 22.10.2026)

- Rutynowe działania wykonuj **sam, bez pytania**: treść historii, sceny, poprawki, render
  i publikację w Metricool według harmonogramu z sekcji 4. Opisz je w podsumowaniu.
- Twarde zasady z sekcji 1 i 4 (tylko marka nightstories.tv, nigdy pepsafe.info, zero gore, oznaczenie AI) obowiązują zawsze.

## 8. Repo

- `tools/make_video.py`: renderer, `tools/sfx.py`: syntezator efektów.
- `stories/<id>/story.json`: scenariusze, `stories/LOG.md`: log publikacji i bank pomysłów (nie powtarzaj motywu z ostatnich 10 filmów).
- `published/<id>/`: okładka, napisy i post.json (bez MP4). Wideo: branch `media` przez `tools/upload_media.py`.
- Autopilot pracuje na branchu `night-autopilot` (stan kanału: log i filmy).
- Po każdym pushu na `night-autopilot` wypchnij ten sam commit na `main` (`git push origin HEAD:main`), żeby `main` był zawsze aktualny.
  Gdy push zostanie odrzucony, bo inna sesja coś dopisała: `git fetch` + `git merge --no-edit origin/night-autopilot`, potem push. Nigdy force-push.
- `AUTOPILOT.md`: polecenie dla zadania cyklicznego.
- Fonty: Anton (OFL) w `assets/fonts/`.
