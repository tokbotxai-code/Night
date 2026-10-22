# Autopilot: polecenie dla zadania cyklicznego

Zadanie cykliczne w Claude Code (nowa sesja przy każdym uruchomieniu, repo `tokbotxai-code/Night`).
Proponowany harmonogram: codziennie o 10:47 czasu Europe/Warsaw (`CRON_TZ=Europe/Warsaw 47 10 * * *`).
Film powstaje rano, a publikacja jest zaplanowana na wieczór w USA.

## Polecenie (wklej jako prompt zadania)

```
Jesteś autopilotem kanału TikTok "Night" (oryginalne horror stories po angielsku, rynek USA/UK).
Repo: tokbotxai-code/Night. Zanim cokolwiek zrobisz, przeczytaj CLAUDE.md, channel.json, stories/LOG.md i stories/001-mom-forgot-keys/story.json (wzorzec).

1. Bezpieczniki:
   - Wywołaj Metricool getBrandSettings. Znajdź markę o id == channel.json → metricool.blog_id (7593858, label nightstories.tv), która ma networksData.tiktokData.
     Jeśli jej nie ma, NIE publikuj nigdzie: zakończ raportem "brak marki/TikToka w Metricool".
     Nigdy nie używaj blogId z forbidden_blog_ids (pepsafe.info).
   - getScheduledPosts dla tej marki na najbliższe 48 h: jeśli film jest już zaplanowany na dzisiejsze okno, zakończ bez zmian.
2. Scenariusz: weź pierwszy pomysł z "Bank pomysłów" w stories/LOG.md (albo wymyśl nowy, oryginalny, niepowtarzający motywu z ostatnich 10 filmów).
   Napisz stories/<NNN>-<slug>/story.json według CLAUDE.md: hook w 1. zdaniu, twist w 35–55 s, pytanie A/B na końcu, ostatni kadr = pierwszy kadr,
   120–140 słów, US English, zero gore, żadnego "true story". Głos, rate, pitch i style_prompt skopiuj z 001.
3. Render: pip install -r requirements.txt; python3 tools/make_video.py <story.json> --preview.
   Jeśli skrypt zgłosi długość spoza 60–75 s, popraw tekst lub pauzy i powtórz.
   Wygeneruj arkusz 15 klatek (ffmpeg -vf tile=5x3) i obejrzyj go. Wymień tła z tekstem, logo, zniekształconą twarzą albo niepasujące do zdania (zmień prompt).
   Następnie render finalny bez --preview.
4. Publikacja pliku: skopiuj output/<id>/final.mp4 i cover.jpg do published/<id>/, uzupełnij stories/LOG.md (przenieś pomysł z banku do tabeli),
   zrób commit i push na swój branch. Zbuduj URL: <public_media_base>/<branch>/published/<id>/final.mp4 i sprawdź curl -I, że zwraca 200.
5. Planowanie: createScheduledPost dla znalezionej marki: providers [{"network":"tiktok"}], media [URL], text = post.caption,
   videoCoverMilliseconds = post.cover_ms, tiktokData {"title": post.tiktok_title, "privacyOption":"PUBLIC_TO_EVERYONE", "isAigc": true,
   "autoAddMusic": false, "disableComment": false}, godzina z okna 19:00–21:30 America/New_York dzisiaj, przeliczona na publicationDate w strefie Europe/London (strefa marki)
   (jeśli okno minęło, to jutro; jeśli konto ma dane, wybierz godzinę z getBestTimeToPostByNetwork).
6. Dopisz do stories/LOG.md godzinę i plannerUrl, zrób commit i push.
7. Raport (krótko, po polsku): tytuł, długość, godzina publikacji (ET i czas polski), link plannera, ewentualne problemy.
   Jeśli którykolwiek krok się nie udał, nie planuj posta. Opisz, co blokuje.
```

## Wymagania przed włączeniem

- Metricool: marka `nightstories.tv` (blogId 7593858) z TikTokiem @nightstories.tv jest gotowa.
- Repo musi zostać publiczne. Metricool pobiera wideo z `raw.githubusercontent.com`.
- Środowisko sesji potrzebuje dostępu sieciowego do: `image.pollinations.ai`, `speech.platform.bing.com`, `raw.githubusercontent.com`, `pypi.org`.
