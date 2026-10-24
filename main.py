import json
import sys
import tempfile
import re
import os
import queue
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

# Locate bundled FFmpeg tools in a PyInstaller onedir build.
_BUNDLE = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
# PyInstaller --onedir stores bundled data in _internal on recent versions.
# Search both the frozen bundle and executable folder for portable tools.
_CANDIDATE_BINS = [
    _BUNDLE / 'bin',
    Path(sys.executable).resolve().parent / 'bin',
    Path(__file__).resolve().parent / 'bin',
]
for _bin_dir in _CANDIDATE_BINS:
    if (_bin_dir / 'ffmpeg.exe').is_file():
        os.environ['PATH'] = str(_bin_dir) + os.pathsep + os.environ.get('PATH', '')
        break

ctk.set_appearance_mode('dark')
ctk.set_default_color_theme('blue')

BASE = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'MusicDownloader'
BASE.mkdir(parents=True, exist_ok=True)
CONFIG = BASE / 'settings.json'
HISTORY = BASE / 'history.json'
BG = '#090E18'
PANEL = '#141E30'
ACCENT = '#1769E8'
MUTED = '#93A6C5'
WHITE = '#F4F7FF'


def load_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def parse_time(value):
    """Accept seconds, MM:SS or HH:MM:SS; return seconds or None for blank."""
    value = value.strip()
    if not value:
        return None
    if not re.fullmatch(r'\d+(?::[0-5]\d){0,2}(?:\.\d{1,3})?', value):
        raise ValueError('Use segundos, MM:SS ou HH:MM:SS (ex.: 01:30).')
    parts = value.split(':')
    if len(parts) > 3:
        raise ValueError('Horário inválido.')
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    return seconds


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Music Downloader | Desktop Edition')
        self.geometry('1080x750')
        self.minsize(850, 560)
        self.configure(fg_color=BG)
        self.settings = load_json(CONFIG, {'output': str(Path.home() / 'Music')})
        self.history = load_json(HISTORY, [])
        self.files = []
        self.events = queue.Queue()
        self.busy = False
        self.format_var = tk.StringVar(value='MP3')
        self.bitrate_var = tk.StringVar(value='320')
        self.trim_enabled = tk.BooleanVar(value=False)
        self.stem_mode = tk.StringVar(value='Voz + Instrumental')
        self.stem_format = tk.StringVar(value='WAV')
        self.trim_start = tk.StringVar(value='00:00')
        self.trim_end = tk.StringVar(value='')
        self.output_var = tk.StringVar(value=self.settings['output'])
        self.status_var = tk.StringVar(value='Pronto para converter arquivos autorizados.')
        self.build_shell()
        self.show_page('Conversor')
        self.after(120, self.poll_events)

    def build_shell(self):
        self.sidebar = ctk.CTkFrame(self, fg_color='#0F1726', width=210, corner_radius=0)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)
        ctk.CTkLabel(self.sidebar, text='♫  MUSIC', font=('Segoe UI', 25, 'bold'), text_color=WHITE).pack(anchor='w', padx=22, pady=(28, 0))
        ctk.CTkLabel(self.sidebar, text='DOWNLOADER  •  V1.2', font=('Segoe UI', 10), text_color=MUTED).pack(anchor='w', padx=24, pady=(0, 38))
        for name, symbol in [('Conversor', '↪'), ('Studio DJ', '🎚'), ('Biblioteca', '♫'), ('Histórico', '◷'), ('Configurações', '⚙')]:
            ctk.CTkButton(self.sidebar, text=f'{symbol}   {name}', height=43, anchor='w', fg_color='transparent', hover_color='#223754', command=lambda n=name: self.show_page(n)).pack(fill='x', padx=12, pady=4)
        ctk.CTkLabel(self.sidebar, text='WINDOWS DESKTOP', text_color=MUTED, font=('Segoe UI', 10)).pack(side='bottom', pady=24)
        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.pack(side='left', fill='both', expand=True, padx=30, pady=24)

    def clear(self):
        for child in self.content.winfo_children():
            child.destroy()

    def header(self, title, subtitle):
        ctk.CTkLabel(self.content, text=title, font=('Segoe UI', 28, 'bold'), text_color=WHITE).pack(anchor='w')
        ctk.CTkLabel(self.content, text=subtitle, font=('Segoe UI', 13), text_color=MUTED).pack(anchor='w', pady=(2, 23))

    def show_page(self, page):
        self.page = page
        self.clear()
        if page == 'Conversor':
            self.header('Converter áudio', 'Transforme arquivos locais em áudio pronto para sua biblioteca.')
            card = ctk.CTkFrame(self.content, fg_color=PANEL, corner_radius=16)
            card.pack(fill='x', pady=(0, 18))
            ctk.CTkLabel(card, text='Arquivos selecionados', text_color=WHITE, font=('Segoe UI', 15, 'bold')).pack(anchor='w', padx=22, pady=(20, 5))
            self.files_label = ctk.CTkLabel(card, text=self.file_summary(), text_color=MUTED, wraplength=650, justify='left')
            self.files_label.pack(anchor='w', padx=22, pady=(0, 12))
            row = ctk.CTkFrame(card, fg_color='transparent')
            row.pack(fill='x', padx=20, pady=(0, 16))
            ctk.CTkButton(row, text='＋  Selecionar arquivos', command=self.pick_files, fg_color=ACCENT).pack(side='left', padx=(0, 8))
            ctk.CTkButton(row, text='Limpar seleção', command=self.clear_files, fg_color='#2B3B54').pack(side='left')
            options = ctk.CTkFrame(self.content, fg_color=PANEL, corner_radius=16)
            options.pack(fill='x', pady=(0, 18))
            ctk.CTkLabel(options, text='Formato de saída', text_color=WHITE).grid(row=0, column=0, padx=20, pady=(20, 8), sticky='w')
            ctk.CTkLabel(options, text='Qualidade MP3', text_color=WHITE).grid(row=0, column=1, padx=20, pady=(20, 8), sticky='w')
            ctk.CTkOptionMenu(options, values=['MP3', 'WAV', 'FLAC'], variable=self.format_var, fg_color='#253A5A', button_color=ACCENT).grid(row=1, column=0, padx=20, pady=(0, 20), sticky='ew')
            ctk.CTkOptionMenu(options, values=['128', '192', '320'], variable=self.bitrate_var, fg_color='#253A5A', button_color=ACCENT).grid(row=1, column=1, padx=20, pady=(0, 20), sticky='ew')
            options.grid_columnconfigure((0, 1), weight=1)
            cut = ctk.CTkFrame(self.content, fg_color=PANEL, corner_radius=16)
            cut.pack(fill='x', pady=(0, 15))
            ctk.CTkCheckBox(cut, text='Ativar corte de áudio (antes de salvar)', variable=self.trim_enabled, text_color=WHITE, fg_color=ACCENT).pack(anchor='w', padx=20, pady=(14, 7))
            cut_row = ctk.CTkFrame(cut, fg_color='transparent')
            cut_row.pack(fill='x', padx=20, pady=(0, 8))
            ctk.CTkLabel(cut_row, text='Início').pack(side='left', padx=(0, 8))
            ctk.CTkEntry(cut_row, textvariable=self.trim_start, width=105, placeholder_text='00:00').pack(side='left', padx=(0, 18))
            ctk.CTkLabel(cut_row, text='Fim').pack(side='left', padx=(0, 8))
            ctk.CTkEntry(cut_row, textvariable=self.trim_end, width=105, placeholder_text='03:30').pack(side='left')
            ctk.CTkButton(cut_row, text='▶ Prévia', width=100, fg_color='#263B5B', command=self.preview_cut).pack(side='right')
            ctk.CTkLabel(cut, text='Horários em MM:SS ou HH:MM:SS. Fim vazio = até terminar. O mesmo corte será aplicado a todos os arquivos.', text_color=MUTED, font=('Segoe UI', 11), wraplength=620).pack(anchor='w', padx=20, pady=(0, 13))
            ctk.CTkLabel(self.content, text='Pasta de destino', text_color=WHITE).pack(anchor='w')
            destination = ctk.CTkFrame(self.content, fg_color='transparent')
            destination.pack(fill='x', pady=(7, 20))
            ctk.CTkEntry(destination, textvariable=self.output_var, height=42).pack(side='left', fill='x', expand=True, padx=(0, 10))
            ctk.CTkButton(destination, text='Escolher pasta', command=self.pick_output, width=125, fg_color='#263B5B').pack(side='left')
            self.start_button = ctk.CTkButton(self.content, text='↓  INICIAR CONVERSÃO', height=48, font=('Segoe UI', 14, 'bold'), fg_color=ACCENT, command=self.start_conversion)
            self.start_button.pack(fill='x')
            self.progress = ctk.CTkProgressBar(self.content, progress_color=ACCENT)
            self.progress.pack(fill='x', pady=(18, 8))
            self.progress.set(0)
            ctk.CTkLabel(self.content, textvariable=self.status_var, text_color=MUTED).pack(anchor='w')
        elif page == 'Studio DJ':
            self.header('Studio DJ | Separação por IA', 'Extraia voz, instrumental ou 4 faixas de arquivos locais autorizados.')
            card = ctk.CTkFrame(self.content, fg_color=PANEL, corner_radius=16)
            card.pack(fill='x', pady=(0, 18))
            ctk.CTkLabel(card, text='Músicas selecionadas', font=('Segoe UI', 15, 'bold'), text_color=WHITE).pack(anchor='w', padx=20, pady=(18, 5))
            self.stem_files_label = ctk.CTkLabel(card, text=self.file_summary(), text_color=MUTED, wraplength=650)
            self.stem_files_label.pack(anchor='w', padx=20, pady=(0, 10))
            ctk.CTkButton(card, text='＋ Selecionar músicas', command=self.pick_files, fg_color=ACCENT).pack(anchor='w', padx=20, pady=(0, 18))
            ctk.CTkLabel(card, text='O que deseja extrair?', text_color=WHITE).pack(anchor='w', padx=20)
            ctk.CTkOptionMenu(card, values=['Somente voz', 'Somente instrumental', 'Voz + Instrumental', '4 stems (voz, bateria, baixo, outros)'], variable=self.stem_mode, width=380, fg_color='#253A5A', button_color=ACCENT).pack(anchor='w', padx=20, pady=(8, 16))
            ctk.CTkLabel(card, text='Formato dos arquivos separados', text_color=WHITE).pack(anchor='w', padx=20)
            ctk.CTkOptionMenu(card, values=['WAV', 'MP3'], variable=self.stem_format, width=180, fg_color='#253A5A', button_color=ACCENT).pack(anchor='w', padx=20, pady=(8, 16))
            ctk.CTkCheckBox(card, text='Aplicar corte antes da separação', variable=self.trim_enabled, text_color=WHITE).pack(anchor='w', padx=20, pady=(0, 10))
            times = ctk.CTkFrame(card, fg_color='transparent')
            times.pack(anchor='w', padx=20, pady=(0, 18))
            ctk.CTkLabel(times, text='Início').pack(side='left', padx=(0, 8))
            ctk.CTkEntry(times, textvariable=self.trim_start, width=100).pack(side='left', padx=(0, 20))
            ctk.CTkLabel(times, text='Fim').pack(side='left', padx=(0, 8))
            ctk.CTkEntry(times, textvariable=self.trim_end, width=100).pack(side='left')
            ctk.CTkLabel(self.content, text='Pasta de destino', text_color=WHITE).pack(anchor='w')
            dest = ctk.CTkFrame(self.content, fg_color='transparent')
            dest.pack(fill='x', pady=(7, 18))
            ctk.CTkEntry(dest, textvariable=self.output_var).pack(side='left', fill='x', expand=True, padx=(0, 10))
            ctk.CTkButton(dest, text='Escolher pasta', command=self.pick_output, fg_color='#263B5B').pack(side='left')
            self.stem_button = ctk.CTkButton(self.content, text='♫ SEPARAR MÚSICA COM IA', height=48, font=('Segoe UI', 14, 'bold'), fg_color=ACCENT, command=self.start_stems)
            self.stem_button.pack(fill='x')
            self.stem_progress = ctk.CTkProgressBar(self.content, progress_color=ACCENT)
            self.stem_progress.pack(fill='x', pady=(18, 8))
            self.stem_progress.set(0)
            ctk.CTkLabel(self.content, textvariable=self.status_var, text_color=MUTED, wraplength=680).pack(anchor='w')
            ctk.CTkLabel(self.content, text='Requer Demucs e FFmpeg. A primeira execução pode baixar o modelo de IA. O processamento pode levar vários minutos.', text_color=MUTED, wraplength=680).pack(anchor='w', pady=(16, 0))
        elif page == 'Biblioteca':
            self.header('Biblioteca musical', 'Arquivos convertidos recentemente.')
            self.records(self.history[:40], show_open=True)
        elif page == 'Histórico':
            self.header('Histórico', 'Registro das conversões realizadas.')
            self.records(self.history, show_open=False)
        else:
            self.header('Configurações', 'Preferências do Music Downloader.')
            ctk.CTkLabel(self.content, text='Pasta padrão para conversões', text_color=WHITE).pack(anchor='w')
            ctk.CTkEntry(self.content, textvariable=self.output_var, height=42).pack(fill='x', pady=10)
            ctk.CTkButton(self.content, text='Selecionar pasta', command=self.pick_output, fg_color=ACCENT).pack(anchor='w')
            ctk.CTkLabel(self.content, text='FFmpeg: ' + ('detectado' if shutil.which('ffmpeg') else 'não encontrado no PATH'), text_color=MUTED).pack(anchor='w', pady=30)
            ctk.CTkLabel(self.content, text='Conversão local. Esta versão não realiza downloads de sites.', text_color=MUTED).pack(anchor='w')

    def file_summary(self):
        if not self.files:
            return 'Nenhum arquivo selecionado. Adicione vídeos ou arquivos de áudio.'
        return f'{len(self.files)} arquivo(s): ' + ', '.join(p.name for p in self.files[:3]) + ('...' if len(self.files) > 3 else '')

    def pick_files(self):
        names = filedialog.askopenfilenames(title='Selecionar arquivos', filetypes=[('Áudio e vídeo', '*.mp4 *.mkv *.mov *.webm *.avi *.mp3 *.wav *.flac *.m4a *.aac *.ogg'), ('Todos os arquivos', '*.*')])
        if names:
            self.files = [Path(p) for p in names]
            self.refresh_files_labels()

    def clear_files(self):
        self.files = []
        self.refresh_files_labels()

    def refresh_files_labels(self):
        for attr in ('files_label', 'stem_files_label'):
            label = getattr(self, attr, None)
            if label is not None and label.winfo_exists():
                label.configure(text=self.file_summary())

    def start_stems(self):
        if self.busy:
            return
        if not self.files:
            messagebox.showwarning('Studio DJ', 'Selecione pelo menos uma música.')
            return
        if not shutil.which('ffmpeg'):
            messagebox.showerror('FFmpeg', 'FFmpeg não encontrado no PATH.')
            return
        try:
            import demucs.separate  # noqa: F401
        except ImportError:
            messagebox.showerror('Demucs', 'Instale o Demucs: python -m pip install -r requirements-studio.txt')
            return
        try:
            start, end = self.cut_range()
            folder = Path(self.output_var.get()).expanduser()
            folder.mkdir(parents=True, exist_ok=True)
        except (ValueError, OSError) as exc:
            messagebox.showerror('Configuração inválida', str(exc))
            return
        self.settings['output'] = str(folder)
        save_json(CONFIG, self.settings)
        self.busy = True
        self.stem_button.configure(state='disabled')
        threading.Thread(target=self.stems_worker, args=(list(self.files), folder, self.stem_mode.get(), self.stem_format.get(), start, end), daemon=True).start()

    def stems_worker(self, files, folder, mode, fmt, start, end):
        ffmpeg = shutil.which('ffmpeg')
        try:
            for idx, src in enumerate(files):
                self.events.put(('status', f'Separando {idx+1}/{len(files)}: {src.name} (aguarde)...'))
                with tempfile.TemporaryDirectory(prefix='music_stems_') as td:
                    td = Path(td)
                    source = src
                    if start is not None:
                        source = td / 'trecho.wav'
                        cmd = [ffmpeg, '-y', '-nostdin', '-hide_banner', '-loglevel', 'error', '-i', str(src), '-ss', str(start)]
                        if end is not None:
                            cmd += ['-t', str(end - start)]
                        cmd += ['-vn', '-ac', '2', '-ar', '44100', str(source)]
                        self.run_checked(cmd)
                    elif not src.is_file():
                        raise FileNotFoundError(str(src))
                    model = 'htdemucs' if mode.startswith('4 stems') else 'htdemucs'
                    cmd = ([sys.executable, '--demucs-worker'] if getattr(sys, 'frozen', False) else [sys.executable, '-m', 'demucs.separate']) + ['-n', model, '-o', str(td / 'separated')]
                    if not mode.startswith('4 stems'):
                        cmd += ['--two-stems', 'vocals']
                    cmd += [str(source)]
                    self.run_checked(cmd, timeout=10800)
                    output_dir = td / 'separated' / model / source.stem
                    names = (['vocals', 'no_vocals'] if mode == 'Voz + Instrumental' else
                             ['vocals'] if mode == 'Somente voz' else
                             ['no_vocals'] if mode == 'Somente instrumental' else
                             ['vocals', 'drums', 'bass', 'other'])
                    # In 2-stem mode Demucs exports vocals.wav and no_vocals.wav.
                    target_dir = folder / (src.stem + '_stems')
                    suffix = 2
                    while target_dir.exists():
                        target_dir = folder / f'{src.stem}_stems_{suffix}'
                        suffix += 1
                    target_dir.mkdir(parents=True)
                    for name in names:
                        stem = output_dir / (name + '.wav')
                        if not stem.exists():
                            raise FileNotFoundError(f'Faixa {name} não gerada pelo Demucs.')
                        destination = target_dir / (name + '.' + fmt.lower())
                        if fmt == 'WAV':
                            shutil.copy2(stem, destination)
                        else:
                            self.run_checked([ffmpeg, '-y', '-nostdin', '-loglevel', 'error', '-i', str(stem), '-codec:a', 'libmp3lame', '-b:a', '320k', str(destination)])
                        self.events.put(('success', {'source': str(src), 'output': str(destination), 'format': fmt + ' • ' + name, 'cut': {'start': start, 'end': end} if start is not None else None, 'date': datetime.now().strftime('%d/%m/%Y %H:%M')}))
                self.events.put(('progress', (idx + 1) / len(files)))
        except Exception as exc:
            self.events.put(('error', str(exc)))
        finally:
            self.events.put(('done', None))

    @staticmethod
    def run_checked(cmd, timeout=3600):
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout or 'Erro no processamento')[-1000:])

    def pick_output(self):
        folder = filedialog.askdirectory(initialdir=self.output_var.get() if Path(self.output_var.get()).exists() else str(Path.home()))
        if folder:
            self.output_var.set(folder)
            self.settings['output'] = folder
            save_json(CONFIG, self.settings)

    def cut_range(self):
        if not self.trim_enabled.get():
            return None, None
        start = parse_time(self.trim_start.get())
        end = parse_time(self.trim_end.get())
        start = start or 0.0
        if end is not None and end <= start:
            raise ValueError('O fim do corte deve ser maior que o início.')
        return start, end

    def preview_cut(self):
        if not self.files:
            messagebox.showwarning('Prévia', 'Selecione um arquivo primeiro.')
            return
        ffplay = shutil.which('ffplay')
        if not ffplay:
            messagebox.showinfo('Prévia', 'Instale o FFplay (incluído em alguns pacotes FFmpeg) e adicione-o ao PATH.')
            return
        try:
            start, end = self.cut_range()
        except ValueError as exc:
            messagebox.showerror('Corte inválido', str(exc))
            return
        cmd = [ffplay, '-autoexit', '-nodisp', '-loglevel', 'error']
        if start is not None:
            cmd += ['-ss', str(start)]
        if end is not None:
            cmd += ['-t', str(end - (start or 0))]
        cmd.append(str(self.files[0]))
        try:
            subprocess.Popen(cmd, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except OSError as exc:
            messagebox.showerror('Prévia', str(exc))

    def start_conversion(self):
        if self.busy:
            return
        if not self.files:
            messagebox.showwarning('Selecione arquivos', 'Adicione pelo menos um arquivo para converter.')
            return
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            messagebox.showerror('FFmpeg necessário', 'Instale FFmpeg e adicione ao PATH do Windows.')
            return
        try:
            start, end = self.cut_range()
        except ValueError as exc:
            messagebox.showerror('Corte inválido', str(exc))
            return
        folder = Path(self.output_var.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror('Pasta inválida', str(exc))
            return
        self.settings['output'] = str(folder)
        save_json(CONFIG, self.settings)
        self.busy = True
        self.start_button.configure(state='disabled')
        threading.Thread(target=self.worker, args=(ffmpeg, list(self.files), folder, self.format_var.get(), self.bitrate_var.get(), start, end), daemon=True).start()

    def worker(self, ffmpeg, files, folder, fmt, bitrate, start, end):
        total = len(files)
        for index, src in enumerate(files):
            self.events.put(('status', f'Convertendo {index + 1}/{total}: {src.name}'))
            ext = fmt.lower()
            dest = folder / f'{src.stem}{"_corte" if start is not None else ""}.{ext}'
            counter = 2
            while dest.exists():
                dest = folder / f'{src.stem}{"_corte" if start is not None else ""} ({counter}).{ext}'
                counter += 1
            command = [ffmpeg, '-nostdin', '-hide_banner', '-loglevel', 'error', '-i', str(src)]
            if start is not None:
                command += ['-ss', str(start)]
            if end is not None:
                command += ['-t', str(end - (start or 0))]
            command += ['-vn']
            if fmt == 'MP3':
                command += ['-codec:a', 'libmp3lame', '-b:a', f'{bitrate}k']
            elif fmt == 'WAV':
                command += ['-codec:a', 'pcm_s16le']
            else:
                command += ['-codec:a', 'flac']
            command += [str(dest)]
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=3600, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip()[-500:] or 'Falha na conversão')
                self.events.put(('success', {'source': str(src), 'output': str(dest), 'format': fmt, 'cut': {'start': start, 'end': end} if start is not None else None, 'date': datetime.now().strftime('%d/%m/%Y %H:%M')}))
            except Exception as exc:
                if dest.exists():
                    dest.unlink()
                self.events.put(('error', f'{src.name}: {exc}'))
            self.events.put(('progress', (index + 1) / total))
        self.events.put(('done', None))

    def poll_events(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'status':
                    self.status_var.set(value)
                elif kind == 'progress':
                    if self.page == 'Conversor':
                        self.progress.set(value)
                    elif self.page == 'Studio DJ':
                        self.stem_progress.set(value)
                elif kind == 'success':
                    self.history.insert(0, value)
                    save_json(HISTORY, self.history)
                elif kind == 'error':
                    self.status_var.set('Erro: ' + value)
                elif kind == 'done':
                    self.busy = False
                    self.status_var.set('Processamento concluído. Consulte a Biblioteca e o Histórico.')
                    if self.page == 'Conversor':
                        self.start_button.configure(state='normal')
                    elif self.page == 'Studio DJ':
                        self.stem_button.configure(state='normal')
        except queue.Empty:
            pass
        self.after(120, self.poll_events)

    def records(self, items, show_open):
        panel = ctk.CTkScrollableFrame(self.content, fg_color=PANEL, corner_radius=14)
        panel.pack(fill='both', expand=True)
        if not items:
            ctk.CTkLabel(panel, text='Nenhuma conversão registrada.', text_color=MUTED).pack(pady=35)
        for record in items:
            row = ctk.CTkFrame(panel, fg_color='#1C2A40', corner_radius=10)
            row.pack(fill='x', padx=10, pady=5)
            path = Path(record['output'])
            ctk.CTkLabel(row, text=path.name, font=('Segoe UI', 13, 'bold'), text_color=WHITE, anchor='w').pack(fill='x', padx=15, pady=(9, 0))
            ctk.CTkLabel(row, text=f"{record['date']}  •  {record['format']}", text_color=MUTED, anchor='w').pack(fill='x', padx=15, pady=(0, 7))
            if show_open:
                ctk.CTkButton(row, text='Abrir arquivo', width=110, fg_color=ACCENT, command=lambda p=path: self.open_file(p)).pack(anchor='e', padx=12, pady=(0, 9))

    def open_file(self, path):
        if path.exists():
            os.startfile(path)
        else:
            messagebox.showwarning('Arquivo não encontrado', 'O arquivo foi movido ou excluído.')


if __name__ == '__main__':
    if '--demucs-worker' in sys.argv:
        # Run Demucs CLI within the packaged executable.
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        from demucs.separate import main as demucs_main
        demucs_main()
    else:
        App().mainloop()
