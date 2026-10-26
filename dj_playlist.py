"""DJ Playlist: local projects, optional audio analysis and portable set export."""
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def safe_name(name):
    return (re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(name)).strip(' .')[:90] or 'Meu Set')


class PlaylistStore:
    def __init__(self, filename):
        self.filename = Path(filename)

    def _read(self):
        try:
            obj = json.loads(self.filename.read_text(encoding='utf-8'))
            return obj if isinstance(obj, dict) else {}
        except (OSError, ValueError):
            return {}

    def names(self):
        return sorted(self._read())

    def save(self, name, tracks):
        name = safe_name(name)
        data = self._read()
        data[name] = tracks
        self.filename.parent.mkdir(parents=True, exist_ok=True)
        temp = self.filename.with_suffix('.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.filename)

    def load(self, name):
        return list(self._read().get(name, []))


NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
CAMELOT_MAJOR = ['8B','3B','10B','5B','12B','7B','2B','9B','4B','11B','6B','1B']
CAMELOT_MINOR = ['5A','12A','7A','2A','9A','4A','11A','6A','1A','8A','3A','10A']


def analyse_track(path):
    """Estimate tempo/key/energy with optional librosa. Never fabricate missing metrics."""
    path = Path(path)
    result = {'bpm': None, 'camelot': None, 'energy': None, 'genre': ''}
    try:
        from mutagen import File
        tags = File(str(path), easy=True)
        if tags:
            result['genre'] = (tags.get('genre') or [''])[0]
            for key in ('bpm', 'tbpm'):
                if tags.get(key):
                    try:
                        result['bpm'] = round(float(tags[key][0]), 1)
                    except (TypeError, ValueError):
                        pass
    except (ImportError, OSError, ValueError):
        pass
    try:
        import librosa
        import numpy as np
        y, sr = librosa.load(str(path), sr=22050, mono=True, duration=180)
        if y.size == 0:
            return result
        if result['bpm'] is None:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            result['bpm'] = round(float(np.asarray(tempo).reshape(-1)[0]), 1)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        profile = np.mean(chroma, axis=1)
        major = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
        minor = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
        candidates = [(float(np.corrcoef(profile, np.roll(template, root))[0,1]), root, mode)
                      for mode, template in [('major',major),('minor',minor)] for root in range(12)]
        _, root, mode = max(candidates)
        result['camelot'] = (CAMELOT_MAJOR if mode == 'major' else CAMELOT_MINOR)[root]
        result['energy'] = round(float(np.sqrt(np.mean(y**2))), 4)
    except (ImportError, OSError, ValueError, RuntimeError, Exception):
        # Missing analysis libraries or unsupported codecs leave metrics unknown.
        pass
    return result


def export_set(name, tracks, destination):
    """Copy source tracks to a unique destination; write relative M3U8 and PDF."""
    root = Path(destination).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    folder = root / safe_name(name)
    counter = 2
    while folder.exists():
        folder = root / f'{safe_name(name)} ({counter})'
        counter += 1
    folder.mkdir()
    copied = []
    missing = []
    try:
        for i, item in enumerate(tracks, 1):
            src = Path(item['path'])
            if not src.is_file():
                missing.append(src.name)
                continue
            filename = f'{i:03d} - {safe_name(src.stem)}{src.suffix.lower()}'
            target = folder / filename
            shutil.copy2(src, target)
            copied.append((item, filename))
        playlist = folder / (safe_name(name) + '.m3u8')
        playlist.write_text('#EXTM3U\n' + ''.join(f'#EXTINF:-1,{item["name"]}\n{filename}\n' for item, filename in copied), encoding='utf-8')
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.pagesizes import A4
        from xml.sax.saxutils import escape
        styles = getSampleStyleSheet()
        story = [Paragraph(escape(str(name)), styles['Title']), Paragraph('TavaresMusic Studio Pro | Set DJ', styles['Normal']), Spacer(1, 15)]
        rows = [['#', 'Faixa', 'BPM', 'Tom', 'Gênero']]
        for idx, (item, filename) in enumerate(copied, 1):
            rows.append([str(idx), Paragraph(escape(item['name'][:60]), styles['Normal']), str(item.get('bpm') or '—'), item.get('camelot') or '—', Paragraph(escape(item.get('genre') or '—'), styles['Normal'])])
        if len(rows) > 1:
            table = Table(rows, colWidths=[25, 245, 55, 45, 115], repeatRows=1)
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#12385A')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8)]))
            story.append(table)
        if missing:
            story.extend([Spacer(1, 18), Paragraph('Arquivos não encontrados:', styles['Heading2'])])
            story.extend(Paragraph(escape(x), styles['Normal']) for x in missing)
        SimpleDocTemplate(str(folder / 'Relatorio do Set.pdf'), pagesize=A4).build(story)
        return folder
    except Exception:
        # Keep copies in place on partial failure for recovery.
        raise
