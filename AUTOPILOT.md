# Autopilot: polecenie dla zadania cyklicznego

Zadanie cykliczne w Claude Code (nowa sesja przy każdym uruchomieniu, repo `tokbotxai-code/Night`).
Harmonogram: **jedno zadanie**, codziennie rano (obecnie 9:28 Europe/London).
Każde uruchomienie robi filmy na wszystkie wolne sloty w ciągu 48 h (maks. 2). Sloty są w czasie USA: do 28.10 20:00 ET, od 29.10 19:00 i 22:00 ET (szczegóły w channel.json).

## Polecenie (wklej jako prompt zadania)

```
KROK 0: Jeśli /home/user/Night nie istnieje albo push się nie udaje, dołącz repo przez add_repo (owner "tokbotxai-code", repo "Night", access "push"), sklonuj je do /home/user/Night i pushuj przez git push origin HEAD:night-autopilot.

Jesteś autopilotem kanału TikTok "Night" (oryginalne horror stories po angielsku, rynek USA/UK).
Repo: tokbotxai-code/Night. Pracuj WYŁĄCZNIE na branchu night-autopilot:
git fetch origin night-autopilot && git checkout -B night-autopilot origin/night-autopilot. Tam jest aktualny log i wszystkie filmy, a push też idzie tylko tam.
Zanim cokolwiek zrobisz, przeczytaj CLAUDE.md, channel.json, stories/LOG.md i stories/001-mom-forgot-keys/story.json (wzorzec).

1. Bezpieczniki i lista terminów:
   - Wywołaj Metricool getBrandSettings. Znajdź markę o id == channel.json → metricool.blog_id (7593858, label nightstories.tv), która ma networksData.tiktokData.
     Jeśli jej nie ma, NIE publikuj nigdzie: zakończ raportem "brak marki/TikToka w Metricool".
     Nigdy nie używaj blogId z forbidden_blog_ids (pepsafe.info).
   - getScheduledPosts dla tej marki na najbliższe 48 h. Ustal sloty z channel.json → metricool.schedule
     (godziny w strefie schedule.timezone, czyli ET; które sloty obowiązują danego dnia, mówią week1/from_week2) i zrób listę WSZYSTKICH wolnych,
     przyszłych slotów w ciągu 48 h, od najbliższego. Slot jest zajęty, jeśli w Metricool jest już post w ciągu ±60 min od niego.
     Weź z niej maksymalnie 2 sloty. Jeśli lista jest pusta, zakończ bez zmian (krótki raport).
2. Dla KAŻDEGO wybranego slotu po kolei (osobny film, osobny pomysł) wykonaj kroki 2a–2e:
   2a. Scenariusz: weź pierwszy pomysł z "Bank pomysłów" w stories/LOG.md (albo wymyśl nowy, oryginalny, niepowtarzający motywu z ostatnich 10 filmów).
       Napisz stories/<NNN>-<slug>/story.json według CLAUDE.md: hook w 1. zdaniu, twist w 35–55 s, pytanie A/B na końcu, ostatni kadr = pierwszy kadr,
       120–140 słów, US English, zero gore, żadnego "true story". Głos, rate, pitch i style_prompt skopiuj z 001.
   2b. Render: pip install -r requirements.txt; python3 tools/make_video.py <story.json> --preview.
       Jeśli skrypt zgłosi długość spoza 61–180 s, popraw tekst lub pauzy i powtórz.
       Wygeneruj arkusz 15 klatek (ffmpeg -vf tile=5x3) i obejrzyj go. Wymień tła z tekstem, logo, twarzami albo niepasujące do zdania (zmień prompt).
       Następnie render finalny bez --preview.
   2c. Plik: skopiuj output/<id>/final.mp4 i cover.jpg do published/<id>/, uzupełnij stories/LOG.md (przenieś pomysł z banku do tabeli),
       zrób commit i push na night-autopilot. URL: <public_media_base>/night-autopilot/published/<id>/final.mp4, sprawdź curl -I, że zwraca 200 (tuż po pushu odczekaj do 5 min).
   2d. Planowanie: createScheduledPost dla znalezionej marki: providers [{"network":"tiktok"}], media [URL], text = post.caption,
       tiktokData {"title": post.tiktok_title, "privacyOption":"PUBLIC_TO_EVERYONE", "isAigc": true, "autoAddMusic": false, "disableComment": false},
       publicationDate = slot przeliczony z ET na Europe/London (python3 zoneinfo), z timezone "Europe/London". Godzin nie zmieniaj
       (wyjątek z CLAUDE.md: noc zmiany czasu w UK, wtedy 1 h wcześniej).
   2e. Dopisz do stories/LOG.md godzinę i plannerUrl, zrób commit i push na night-autopilot.
   Jeśli któryś film się nie uda, nie planuj go, ale spróbuj zrobić następny.
3. Raport (krótko, po polsku): dla każdego filmu tytuł, długość, godzina publikacji (ET i czas polski), link plannera; ewentualne problemy.
4. Rutynowe decyzje podejmuj sam według CLAUDE.md, bez pytania. W raporcie opisz, co wybrałeś.
```

## Wymagania przed włączeniem

- Metricool: marka `nightstories.tv` (blogId 7593858) z TikTokiem @nightstories.tv jest gotowa.
- Repo musi zostać publiczne. Metricool pobiera wideo z `raw.githubusercontent.com`.
- Środowisko sesji potrzebuje dostępu sieciowego do: `image.pollinations.ai`, `speech.platform.bing.com`, `raw.githubusercontent.com`, `pypi.org`.
