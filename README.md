# Night

Kanał TikTok @nightstories.tv: oryginalne horror stories po angielsku (USA/UK), robione i publikowane automatycznie.

- `CLAUDE.md`: zasady kanału (treść, produkcja, publikacja, harmonogram). To źródło prawdy.
- `AUTOPILOT.md`: polecenie dla codziennego zadania „Night”.
- `channel.json`: ustawienia (głos, długość, harmonogram, Metricool).
- `stories/`: scenariusze (`<id>/story.json`) i `LOG.md` (log publikacji, obserwacje, bank pomysłów).
- `published/<id>/`: okładka, napisy i dane posta. Wideo jest na branchu `media`.
- `tools/make_video.py`: renderer, `tools/sfx.py`: efekty dźwiękowe, `tools/upload_media.py`: wysyłka wideo.

```
pip install -r requirements.txt   # + ffmpeg
python3 tools/make_video.py stories/<id>/story.json
python3 tools/upload_media.py <id>
```

Branch roboczy: `night-autopilot` (`main` jest jego kopią).
