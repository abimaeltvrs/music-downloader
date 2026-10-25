import json
import sys
import tempfile
import re
import os
import queue
import shutil
import subprocess
import threading
import atexit
import webbrowser
import urllib.parse
import urllib.request
import math
import struct
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
    _BUNDLE,
    Path(sys.executable).resolve().parent / '_internal' / 'bin',
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
BG = '#080D16'
PANEL = '#111F32'
ACCENT = '#1787FF'
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
        self.title('DJ Tavares | Music Downloader V1.4.7 Beta')
        self._window_icon = None
        try:
            self.iconbitmap(str(_BUNDLE / 'assets' / 'dj_tavares.ico'))
        except Exception:
            pass
        try:
            self._window_icon = tk.PhotoImage(file=str(_BUNDLE / 'assets' / 'dj_tavares_icon.png'))
            self.iconphoto(True, self._window_icon)
        except Exception:
            pass
        self.preview_path = None
        self.geometry('1180x820')
        self.minsize(920, 620)
        self.configure(fg_color=BG)
        self.settings = load_json(CONFIG, {'output': str(Path.home() / 'Music')})
        self.history = load_json(HISTORY, [])
        self.files = []
        self.events = queue.Queue()
        self.busy = False
        self.had_error = False
        self.format_var = tk.StringVar(value='MP3')
        self.bitrate_var = tk.StringVar(value='320')
        self.trim_enabled = tk.BooleanVar(value=False)
        self.stem_mode = tk.StringVar(value='Voz + Instrumental')
        self.stem_format = tk.StringVar(value='WAV')
        self.trim_start = tk.StringVar(value='00:00')
        self.trim_end = tk.StringVar(value='')
        self.output_var = tk.StringVar(value=self.settings['output'])
        self.url_var = tk.StringVar(value='')
        self.download_queue = []
        self.queue_index = 0
        self.queue_active = False
        self.queue_cancelled = False
        self.queue_pause = threading.Event()
        self.queue_pause.set()
        self.transfer_pause = threading.Event()
        self.transfer_pause.set()
        self.transfer_cancel = threading.Event()
        self.link_format = tk.StringVar(value='MP3')
        self.link_playlist = tk.BooleanVar(value=False)
        self.playlist_save_mode = tk.StringVar(value=self.settings.get('playlist_save_mode', 'subfolder'))
        self.playlist_folder_name = tk.StringVar(value=self.settings.get('playlist_folder_name', ''))
        self.link_audio_quality = tk.StringVar(value='320')
        self.link_video_quality = tk.StringVar(value='1080p')
        self.stem_quality = tk.StringVar(value='Rápido')
        self.fade_in_var = tk.BooleanVar(value=False)
        self.fade_out_var = tk.BooleanVar(value=False)
        self.fade_duration_var = tk.StringVar(value='3')
        self.status_var = tk.StringVar(value='Pronto para converter arquivos autorizados.')
        self.build_shell()
        self.show_page('Conversor')
        self.after(120, self.poll_events)

    def build_shell(self):
        self.sidebar = ctk.CTkFrame(self, fg_color='#101B2D', width=230, corner_radius=0)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)
        self.nav_buttons = {}
        self.brand_image = None
        try:
            from PIL import Image as PILImage
            self.brand_image = ctk.CTkImage(light_image=PILImage.open(_BUNDLE / 'assets' / 'dj_tavares_banner.png'), dark_image=PILImage.open(_BUNDLE / 'assets' / 'dj_tavares_banner.png'), size=(185, 125))
            ctk.CTkLabel(self.sidebar, text='', image=self.brand_image).pack(anchor='w', padx=14, pady=(12, 0))
        except Exception:
            ctk.CTkLabel(self.sidebar, text='DJ TAVARES', font=('Segoe UI', 24, 'bold'), text_color=WHITE).pack(anchor='w', padx=20, pady=(28, 0))
        ctk.CTkLabel(self.sidebar, text='STUDIO PRO  •  V1.4.6 BETA', font=('Segoe UI', 10), text_color=MUTED).pack(anchor='w', padx=20, pady=(0, 20))
        for name, symbol in [('Conversor', '♫'), ('Studio DJ', '◈'), ('Links', '⇩'), ('Biblioteca', '▣'), ('Histórico', '◷'), ('Configurações', '⚙')]:
            button = ctk.CTkButton(self.sidebar, text=f'{symbol}    {name}', height=45, corner_radius=10, anchor='w', font=('Segoe UI', 13, 'bold'), fg_color='transparent', hover_color='#223754', command=lambda n=name: self.show_page(n))
            button.pack(fill='x', padx=12, pady=3)
            self.nav_buttons[name] = button
        ctk.CTkLabel(self.sidebar, text='WINDOWS DESKTOP', text_color=MUTED, font=('Segoe UI', 10)).pack(side='bottom', pady=24)
        self.content = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.content.pack(side='left', fill='both', expand=True, padx=24, pady=18)

    def clear(self):
        for child in self.content.winfo_children():
            child.destroy()

    def header(self, title, subtitle):
        ctk.CTkLabel(self.content, text=title, font=('Segoe UI', 27, 'bold'), text_color=WHITE).pack(anchor='w')
        ctk.CTkLabel(self.content, text=subtitle, font=('Segoe UI', 13), text_color=MUTED).pack(anchor='w', pady=(2, 15))

    def show_page(self, page):
        self.page = page
        for nav_name, button in self.nav_buttons.items():
            button.configure(fg_color=ACCENT if nav_name == page else 'transparent')
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
            ctk.CTkButton(cut_row, text='▥ Editor visual', width=130, fg_color=ACCENT, command=self.open_waveform_editor).pack(side='right', padx=(8, 0))
            ctk.CTkButton(cut_row, text='▶ Prévia', width=100, fg_color='#263B5B', command=self.preview_cut).pack(side='right')
            effects = ctk.CTkFrame(cut, fg_color='transparent')
            effects.pack(fill='x', padx=20, pady=(0, 9))
            ctk.CTkCheckBox(effects, text='Fade-in', variable=self.fade_in_var, width=100).pack(side='left')
            ctk.CTkCheckBox(effects, text='Fade-out', variable=self.fade_out_var, width=110).pack(side='left', padx=(15, 0))
            ctk.CTkLabel(effects, text='Duração (s):').pack(side='left', padx=(18, 5))
            ctk.CTkEntry(effects, textvariable=self.fade_duration_var, width=60).pack(side='left')
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
            ctk.CTkLabel(card, text='Qualidade da separação', text_color=WHITE).pack(anchor='w', padx=20)
            ctk.CTkOptionMenu(card, values=['Rápido', 'Alta qualidade'], variable=self.stem_quality, width=220, fg_color='#253A5A').pack(anchor='w', padx=20, pady=(8, 14))
            ctk.CTkButton(card, text='▥ Editor visual para selecionar trecho', command=self.open_waveform_editor, fg_color=ACCENT).pack(anchor='w', padx=20, pady=(0, 12))
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
        elif page == 'Links':
            self.header('Download por link', 'Somente videos proprios ou com download autorizado pela plataforma.')
            panel = ctk.CTkScrollableFrame(self.content, fg_color=PANEL, corner_radius=16, border_width=1, border_color='#263B59')
            panel.pack(fill='both', expand=True, pady=(4, 8))
            ctk.CTkLabel(panel, text='URL do video', text_color=WHITE).pack(anchor='w', padx=20, pady=(20, 8))
            ctk.CTkEntry(panel, textvariable=self.url_var, height=42, placeholder_text='https://www.youtube.com/watch?v=...').pack(fill='x', padx=20)
            ctk.CTkLabel(panel, text='Vários links: cole um por linha abaixo e adicione à fila.', text_color=MUTED).pack(anchor='w', padx=20, pady=(10, 3))
            self.multi_links = ctk.CTkTextbox(panel, height=76, fg_color='#0D1626', border_width=1, border_color='#2B4566')
            self.multi_links.pack(fill='x', padx=20)
            controls = ctk.CTkFrame(panel, fg_color='transparent')
            controls.pack(fill='x', padx=20, pady=(8, 2))
            ctk.CTkButton(controls, text='＋ Adicionar à fila', command=self.add_download_queue, width=150).pack(side='left', padx=(0, 8))
            ctk.CTkButton(controls, text='Limpar fila', fg_color='#33445E', command=self.clear_download_queue, width=105).pack(side='left')
            self.queue_label = ctk.CTkLabel(panel, text='', text_color=MUTED, anchor='w')
            self.queue_label.pack(fill='x', padx=20)
            self.refresh_download_queue()
            ctk.CTkLabel(panel, text='Formato de saida', text_color=WHITE).pack(anchor='w', padx=20, pady=(15, 8))
            ctk.CTkOptionMenu(panel, values=['MP3', 'MP4', 'WAV'], variable=self.link_format, fg_color='#253A5A').pack(anchor='w', padx=20)
            ctk.CTkLabel(panel, text='Qualidade MP3 (kbps)', text_color=WHITE).pack(anchor='w', padx=20, pady=(12, 4))
            ctk.CTkOptionMenu(panel, values=['128', '192', '256', '320'], variable=self.link_audio_quality, width=190).pack(anchor='w', padx=20)
            ctk.CTkLabel(panel, text='Resolução MP4 (máximo disponível)', text_color=WHITE).pack(anchor='w', padx=20, pady=(12, 4))
            ctk.CTkOptionMenu(panel, values=['360p', '480p', '720p', '1080p', 'Melhor disponível'], variable=self.link_video_quality, width=220).pack(anchor='w', padx=20)
            ctk.CTkLabel(panel, text='Spotify: identifica faixa e oferece pesquisa em lojas de música. Não extrai áudio protegido.', text_color=MUTED, wraplength=700).pack(anchor='w', padx=20, pady=(10, 0))
            ctk.CTkCheckBox(panel, text='Baixar playlist inteira (quando permitido)', variable=self.link_playlist, fg_color=ACCENT).pack(anchor='w', padx=20, pady=(12, 0))
            ctk.CTkLabel(panel, text='Organização dos downloads', text_color=WHITE, font=('Segoe UI', 13, 'bold')).pack(anchor='w', padx=20, pady=(15, 5))
            ctk.CTkRadioButton(panel, text='Salvar diretamente na pasta selecionada', variable=self.playlist_save_mode, value='direct').pack(anchor='w', padx=20, pady=3)
            ctk.CTkRadioButton(panel, text='Criar subpasta para a playlist', variable=self.playlist_save_mode, value='subfolder').pack(anchor='w', padx=20, pady=3)
            ctk.CTkLabel(panel, text='Nome da subpasta (vazio = título da playlist)' , text_color=MUTED).pack(anchor='w', padx=20, pady=(7, 3))
            ctk.CTkEntry(panel, textvariable=self.playlist_folder_name, placeholder_text='Funk 2026').pack(fill='x', padx=20)
            ctk.CTkLabel(panel, text='Pasta de destino', text_color=WHITE).pack(anchor='w', padx=20, pady=(15, 8))
            ctk.CTkEntry(panel, textvariable=self.output_var).pack(fill='x', padx=20)
            ctk.CTkButton(panel, text='Escolher pasta', command=self.pick_output).pack(anchor='w', padx=20, pady=12)
            self.link_button = ctk.CTkButton(panel, text='BAIXAR CONTEUDO AUTORIZADO', height=45, command=self.start_link_download)
            self.link_button.pack(fill='x', padx=20, pady=(5, 6))
            rowq = ctk.CTkFrame(panel, fg_color='transparent')
            rowq.pack(fill='x', padx=20, pady=(0, 6))
            ctk.CTkButton(rowq, text='▶ Iniciar fila', command=self.start_download_queue, fg_color=ACCENT).pack(side='left', padx=(0, 8))
            ctk.CTkButton(rowq, text='Pausar / Retomar', command=self.toggle_download_queue, fg_color='#344B6D').pack(side='left', padx=(0, 8))
            ctk.CTkButton(rowq, text='Cancelar após item atual', command=self.cancel_download_queue, fg_color='#6B3440').pack(side='left')
            ctk.CTkLabel(panel, text='CONTROLE DE PLAYLIST', font=('Segoe UI', 12, 'bold'), text_color='#64B5FF').pack(anchor='w', padx=20, pady=(6, 4))
            transport = ctk.CTkFrame(panel, fg_color='transparent')
            transport.pack(fill='x', padx=20, pady=(0, 8))
            self.pause_transfer_button = ctk.CTkButton(transport, text='Ⅱ  Pausar playlist', width=155, fg_color='#2B4768', hover_color='#385C82', command=self.toggle_transfer_pause)
            self.pause_transfer_button.pack(side='left', padx=(0, 8))
            self.cancel_transfer_button = ctk.CTkButton(transport, text='■  Parar playlist', width=205, fg_color='#8B3448', hover_color='#A84055', command=self.cancel_transfer)
            self.cancel_transfer_button.pack(side='left')
            self.transfer_progress = ctk.CTkProgressBar(panel, progress_color='#27A8FF')
            self.transfer_progress.pack(fill='x', padx=20, pady=(3, 8))
            self.transfer_progress.set(0)
            self.transfer_detail = ctk.CTkLabel(panel, text='Nenhum download de playlist em andamento.', text_color=MUTED, anchor='w')
            self.transfer_detail.pack(fill='x', padx=20, pady=(0, 10))
            self.queue_progress = ctk.CTkProgressBar(panel, progress_color=ACCENT)
            self.queue_progress.pack(fill='x', padx=20, pady=(4, 4))
            self.queue_progress.set(0)
            ctk.CTkLabel(panel, textvariable=self.status_var, text_color=MUTED, wraplength=690).pack(anchor='w', padx=20, pady=10)
            ctk.CTkLabel(panel, text='Vídeos privados ou indisponíveis serão ignorados. O relatório distingue falhas de itens ainda não tentados.', text_color=MUTED, wraplength=690).pack(anchor='w', padx=20, pady=(0, 12))
        elif page == 'Biblioteca':
            self.header('Biblioteca musical', 'Arquivos convertidos, baixados e separados recentemente.')
            self.record_actions('Biblioteca')
            self.records(self.history[:40], show_open=True)
        elif page == 'Histórico':
            self.header('Histórico', 'Registro das conversões, downloads e separações.')
            self.record_actions('Histórico')
            self.records(self.history, show_open=False)
        else:
            self.header('Configurações', 'Preferências do Music Downloader.')
            ctk.CTkLabel(self.content, text='Pasta padrão para conversões', text_color=WHITE).pack(anchor='w')
            ctk.CTkEntry(self.content, textvariable=self.output_var, height=42).pack(fill='x', pady=10)
            ctk.CTkButton(self.content, text='Selecionar pasta', command=self.pick_output, fg_color=ACCENT).pack(anchor='w')
            ctk.CTkLabel(self.content, text='FFmpeg: ' + ('detectado' if shutil.which('ffmpeg') else 'não encontrado no pacote/PATH'), text_color=MUTED).pack(anchor='w', pady=30)
            ctk.CTkLabel(self.content, text='Downloads por link disponíveis na aba Links, para conteúdos autorizados.', text_color=MUTED).pack(anchor='w')

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

    def refresh_download_queue(self):
        if hasattr(self, 'queue_label') and self.queue_label.winfo_exists():
            preview = '  |  '.join(f"{i+1}. {item['url'][:55]}" for i, item in enumerate(self.download_queue[:3]))
            self.queue_label.configure(text=f'{len(self.download_queue)} link(s) na fila. {preview}')

    def add_download_queue(self):
        raw = self.multi_links.get('1.0', 'end').strip()
        raw = '\n'.join([self.url_var.get().strip(), raw])
        urls = [u.strip() for u in raw.splitlines() if u.strip()]
        seen = {item['url'] for item in self.download_queue}
        added = 0
        for url in urls:
            if not url.startswith(('https://', 'http://')) or url in seen:
                continue
            self.download_queue.append({'url': url, 'format': self.link_format.get(),
                'bitrate': self.link_audio_quality.get(), 'resolution': self.link_video_quality.get(),
                'playlist': self.link_playlist.get(), 'save_mode': self.playlist_save_mode.get(), 'subfolder': self.playlist_folder_name.get()})
            seen.add(url)
            added += 1
        self.multi_links.delete('1.0', 'end')
        self.url_var.set('')
        self.refresh_download_queue()
        if not added:
            messagebox.showinfo('Fila', 'Nenhum link novo e válido foi adicionado.')

    def clear_download_queue(self):
        if self.queue_active:
            messagebox.showwarning('Fila em execução', 'Cancele a fila antes de limpá-la.')
            return
        self.download_queue.clear()
        self.queue_index = 0
        self.refresh_download_queue()

    def start_download_queue(self):
        if self.busy or self.queue_active:
            return
        if not self.download_queue:
            self.add_download_queue()
        if not self.download_queue:
            return
        if not shutil.which('ffmpeg'):
            messagebox.showerror('FFmpeg', 'FFmpeg não encontrado no pacote.')
            return
        folder = Path(self.output_var.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror('Pasta', str(exc))
            return
        self.queue_active = True
        self.transfer_cancel.clear()
        self.transfer_pause.set()
        self.queue_cancelled = False
        self.queue_pause.set()
        self.queue_index = 0
        self.busy = True
        self.had_error = False
        threading.Thread(target=self.download_queue_worker, args=(folder,), daemon=True).start()

    def download_queue_worker(self, folder):
        # Each item uses the already-tested download engine; one at a time.
        while self.queue_index < len(self.download_queue) and not self.queue_cancelled:
            self.queue_pause.wait()
            if self.queue_cancelled:
                break
            item = self.download_queue[self.queue_index]
            self.events.put(('status', f"Fila {self.queue_index+1}/{len(self.download_queue)}: {item['url']}"))
            if 'open.spotify.com/' in item['url'].lower():
                self.events.put(('status', 'Link Spotify: abra individualmente para identificar a faixa e buscar uma loja autorizada.'))
            else:
                self.link_worker(item['url'], folder, item['format'], item['playlist'], item['bitrate'], item['resolution'], queue_item=True, save_mode=item.get('save_mode'), subfolder=item.get('subfolder'))
            self.queue_index += 1
            self.events.put(('queue_progress', self.queue_index / max(len(self.download_queue), 1)))
        self.events.put(('queue_finished', None))

    def toggle_download_queue(self):
        if not self.queue_active:
            return
        if self.queue_pause.is_set():
            self.queue_pause.clear()
            self.status_var.set('Fila pausada; o download atual termina antes da pausa.')
        else:
            self.queue_pause.set()
            self.status_var.set('Fila retomada.')

    def cancel_download_queue(self):
        self.cancel_transfer()

    def toggle_transfer_pause(self):
        if not self.busy:
            return
        if self.transfer_pause.is_set():
            self.transfer_pause.clear()
            self.status_var.set('Pausa solicitada: aguardando o próximo ponto de controle do download.')
            if hasattr(self, 'pause_transfer_button') and self.pause_transfer_button.winfo_exists():
                self.pause_transfer_button.configure(text='▶  Retomar playlist')
        else:
            self.transfer_pause.set()
            self.status_var.set('Download retomado.')
            if hasattr(self, 'pause_transfer_button') and self.pause_transfer_button.winfo_exists():
                self.pause_transfer_button.configure(text='Ⅱ  Pausar playlist')

    def cancel_transfer(self):
        if not self.busy:
            return
        self.transfer_cancel.set()
        self.queue_cancelled = True
        self.transfer_pause.set()
        self.queue_pause.set()
        self.status_var.set('Parando playlist; preparando resumo das faixas processadas...')

    def record_actions(self, page):
        bar = ctk.CTkFrame(self.content, fg_color='transparent')
        bar.pack(fill='x', pady=(0, 12))
        ctk.CTkButton(bar, text='Limpar registros', fg_color='#6B3440', hover_color='#873C4A',
            command=lambda: self.clear_records(page)).pack(side='right')
        ctk.CTkLabel(bar, text='A limpeza não apaga músicas do computador.', text_color=MUTED).pack(side='left')

    def clear_records(self, page):
        if not messagebox.askyesno('Confirmar limpeza',
                f'Limpar os registros de {page.lower()}? Os arquivos físicos serão preservados.'):
            return
        self.history.clear()
        save_json(HISTORY, self.history)
        self.show_page(page)

    def start_link_download(self):
        if self.busy:
            return
        url = self.url_var.get().strip()
        if not url.startswith(('https://', 'http://')):
            messagebox.showwarning('Link invalido', 'Informe uma URL HTTP ou HTTPS valida.')
            return
        if 'open.spotify.com/' in url.lower():
            self.lookup_spotify(url)
            return
        if not shutil.which('ffmpeg'):
            messagebox.showerror('FFmpeg', 'FFmpeg nao encontrado no pacote.')
            return
        try:
            import yt_dlp  # noqa: F401
        except Exception as exc:
            messagebox.showerror('yt-dlp', 'Biblioteca indisponivel: ' + repr(exc))
            return
        folder = Path(self.output_var.get()).expanduser()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror('Pasta invalida', str(exc))
            return
        self.had_error = False
        self.transfer_cancel.clear()
        self.transfer_pause.set()
        self.busy = True
        self.link_button.configure(state='disabled')
        threading.Thread(target=self.link_worker, args=(url, folder, self.link_format.get(), self.link_playlist.get(), self.link_audio_quality.get(), self.link_video_quality.get()), daemon=True).start()

    def lookup_spotify(self, url):
        """Identify Spotify metadata and let the user select a YouTube result manually."""
        def work():
            try:
                endpoint = 'https://open.spotify.com/oembed?url=' + urllib.parse.quote(url, safe='')
                req = urllib.request.Request(endpoint, headers={'User-Agent': 'DJTavares/1.4.5'})
                with urllib.request.urlopen(req, timeout=15) as response:
                    data = json.load(response)
                title = data.get('title') or 'Faixa não identificada'
                artist = data.get('author_name') or ''
                # Spotify oEmbed may already include the artist in the title.
                query = title if artist.lower() in title.lower() else ' '.join(x for x in (artist, title) if x)
                def display():
                    if messagebox.askyesno('Spotify — pesquisar no YouTube',
                        f'Música: {title}\nArtista: {artist or "não informado"}\n\n'
                        'Abrir resultados no YouTube para você escolher a versão correta?\n\n'
                        'Depois copie o link do vídeo e cole no downloader. '
                        'O acesso e download dependem das permissões da fonte.'):
                        webbrowser.open('https://www.youtube.com/results?search_query=' + urllib.parse.quote(query))
                    self.status_var.set('Spotify identificado. Escolha um vídeo disponível no YouTube e cole o link.')
                self.after(0, display)
            except Exception as exc:
                self.after(0, lambda msg=str(exc): messagebox.showerror('Spotify', 'Não foi possível identificar o link: ' + msg))
        threading.Thread(target=work, daemon=True).start()

    def link_worker(self, url, folder, fmt, playlist, bitrate='320', resolution='1080p', queue_item=False, save_mode=None, subfolder=None):
        """Record completed files, including individual items from playlists."""
        try:
            import yt_dlp
            ffmpeg_path = shutil.which('ffmpeg')
            finished = {}
            failed_messages = []
            playlist_entries = []
            seen_indices = set()
            attempted_ids = set()
            cancelled = False
            save_mode = save_mode or self.playlist_save_mode.get()
            subfolder = self.playlist_folder_name.get() if subfolder is None else subfolder
            # Persist user preference for the next session.
            self.settings['playlist_save_mode'] = save_mode
            self.settings['playlist_folder_name'] = subfolder
            save_json(CONFIG, self.settings)
            folder = Path(folder).expanduser().resolve()
            # Never permit traversal outside the selected parent directory.
            def safe_folder(label):
                label = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', str(label)).strip(' .')[:100]
                return label if label and label not in ('.', '..') else 'Playlist'
            if playlist and save_mode == 'subfolder':
                label = subfolder.strip() if subfolder else ''
                if not label:
                    # Obtain playlist metadata before downloading, so folder uses real title.
                    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True, 'extract_flat': True, 'skip_download': True, 'noplaylist': False}) as probe:
                        metadata = probe.extract_info(url, download=False)
                    label = (metadata or {}).get('title') or (metadata or {}).get('playlist_title') or 'Playlist'
                folder = folder / safe_folder(label)
            folder.mkdir(parents=True, exist_ok=True)
            if playlist:
                # Flat metadata listing keeps track of unavailable playlist entries.
                try:
                    with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True,
                        'extract_flat': 'in_playlist', 'skip_download': True,
                        'ignoreerrors': True, 'noplaylist': False}) as probe:
                        listing = probe.extract_info(url, download=False)
                    playlist_entries = [x for x in (listing or {}).get('entries', []) if isinstance(x, dict)]
                except Exception as probe_exc:
                    failed_messages.append('Não foi possível obter a lista completa: ' + str(probe_exc))
            prior_files = {str(x.resolve()): x.stat().st_mtime_ns for x in folder.iterdir() if x.is_file()}
            self.events.put(('status', f'Pasta de destino: {folder}'))

            def remember(info):
                if not isinstance(info, dict):
                    return
                ident = str(info.get('id') or '')
                filename = info.get('filepath') or info.get('_filename')
                if not filename:
                    downloads = info.get('requested_downloads') or []
                    if downloads:
                        filename = downloads[0].get('filepath')
                if filename:
                    finished[ident or str(filename)] = (dict(info), str(filename))

            class StopRequested(Exception):
                pass

            def transfer_hook(data):
                # Called regularly by yt-dlp while each track downloads.
                if self.transfer_cancel.is_set():
                    raise StopRequested('Interrompido pelo usuário')
                self.transfer_pause.wait()
                if self.transfer_cancel.is_set():
                    raise StopRequested('Interrompido pelo usuário')
                info = data.get('info_dict') or {}
                video_id = str(info.get('id') or '')
                if video_id:
                    attempted_ids.add(video_id)
                position = info.get('playlist_index')
                try:
                    if position is not None:
                        seen_indices.add(int(position))
                except (TypeError, ValueError):
                    pass
                if data.get('status') == 'finished':
                    remember(info)
                self.events.put(('transfer_detail', f"{info.get('title') or 'Música'} • {data.get('status', '')}"))

            def postprocess_hook(data):
                if data.get('status') == 'finished':
                    remember(data.get('info_dict'))

            class DownloadLogger:
                def debug(self, msg):
                    pass
                def warning(self, msg):
                    pass
                def error(self, msg):
                    failed_messages.append(str(msg))

            options = {
                'logger': DownloadLogger(),
                'outtmpl': str(folder / '%(title).180B [%(id)s].%(ext)s'),
                'noplaylist': not playlist,
                'ffmpeg_location': str(Path(ffmpeg_path).parent),
                'quiet': True,
                'no_warnings': True,
                'postprocessor_hooks': [postprocess_hook],
                'progress_hooks': [transfer_hook],
                'ignoreerrors': True if playlist else False,
            }
            if fmt == 'MP4':
                height = int(resolution[:-1]) if resolution.endswith('p') else None
                limit = f'[height<={height}]' if height else ''
                options['format'] = f'bv*[ext=mp4]{limit}+ba[ext=m4a]/bv*{limit}+ba/b[ext=mp4]{limit}/b{limit}'
                options['merge_output_format'] = 'mp4'
            else:
                options['format'] = 'bestaudio/best'
                options['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': fmt.lower(), 'preferredquality': bitrate if fmt == 'MP3' else '0'}]
            self.events.put(('status', 'Baixando conteúdo autorizado; arquivos longos podem demorar...'))
            try:
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=True)
                    entries = (info.get('entries') or []) if isinstance(info, dict) and info.get('_type') == 'playlist' else [info]
                    for item in entries:
                        if not isinstance(item, dict):
                            continue
                        ident = str(item.get('id') or '')
                        if ident not in finished:
                            remember(item)
                        if ident not in finished:
                            guessed = Path(ydl.prepare_filename(item)).with_suffix('.' + fmt.lower())
                            finished[ident or str(guessed)] = (item, str(guessed))
            except StopRequested:
                cancelled = True
            except Exception as exc:
                if self.transfer_cancel.is_set():
                    cancelled = True
                else:
                    raise
            cancelled = cancelled or self.transfer_cancel.is_set()
            count = 0
            registered = set()
            for item, filename in finished.values():
                output = Path(filename)
                if fmt != 'MP4':
                    output = output.with_suffix('.' + fmt.lower())
                elif output.suffix.lower() != '.mp4':
                    output = output.with_suffix('.mp4')
                if not output.is_file():
                    continue
                key = str(output.resolve())
                if key in prior_files and prior_files[key] == output.stat().st_mtime_ns:
                    continue
                registered.add(str(output.resolve()))
                self.events.put(('success', {
                    'source': item.get('webpage_url') or url,
                    'output': str(output), 'format': fmt + ' • Link',
                    'date': datetime.now().strftime('%d/%m/%Y %H:%M'),
                    'cut': None,
                }))
                count += 1
            # Some yt-dlp postprocessors report pre-conversion filenames.
            # Discover only real finished files in this download directory.
            for output in sorted(folder.glob('*')):
                if not output.is_file() or output.suffix.lower() != '.' + fmt.lower():
                    continue
                key = str(output.resolve())
                if key in registered or (key in prior_files and prior_files[key] == output.stat().st_mtime_ns):
                    continue
                registered.add(key)
                self.events.put(('success', {'source': url, 'output': key,
                    'format': fmt + ' • Link', 'date': datetime.now().strftime('%d/%m/%Y %H:%M'), 'cut': None}))
                count += 1
            if playlist:
                # Compare playlist IDs to downloaded filenames; the filename template
                # includes [video_id], even when postprocessing changes the extension.
                completed_ids = set()
                for output in folder.iterdir():
                    if output.is_file() and output.suffix.lower() == '.' + fmt.lower():
                        match = re.search(r'\[([^\[\]]{6,})\]$', output.stem)
                        if match:
                            completed_ids.add(match.group(1))
                # Keep a named record for every successful playlist entry, not just totals.
                downloaded_items = []
                files_by_id = {}
                for output in sorted(folder.iterdir()):
                    if output.is_file() and output.suffix.lower() == '.' + fmt.lower():
                        match = re.search(r'\[([^\[\]]{6,})\]$', output.stem)
                        if match:
                            files_by_id[match.group(1)] = output
                missing = []
                pending = []
                for index, entry in enumerate(playlist_entries, 1):
                    video_id = str(entry.get('id') or '')
                    title = entry.get('title') or f'Item {index} (título indisponível)'
                    if video_id and video_id in completed_ids:
                        saved = files_by_id.get(video_id)
                        downloaded_items.append(f'{index}. {title}\n   Arquivo: {saved.name if saved else "baixado"}')
                        continue
                    link = entry.get('webpage_url') or entry.get('url') or ''
                    if link and not str(link).startswith('http') and video_id:
                        link = 'https://www.youtube.com/watch?v=' + video_id
                    item_text = f'{index}. {title}\n   {link}'
                    errors_so_far = '\n'.join(failed_messages)
                    mentioned_in_errors = bool(video_id and video_id in errors_so_far)
                    if cancelled and not (video_id in attempted_ids or index in seen_indices or mentioned_in_errors):
                        pending.append(item_text)
                    else:
                        missing.append(item_text)
                # Errors for private videos can occur before progress hooks fire.
                # Classify explicitly mentioned IDs as attempted failures.
                if cancelled and failed_messages and pending:
                    errors = '\n'.join(failed_messages)
                    for item in pending[:]:
                        match = re.search(r'watch\?v=([\w-]+)', item)
                        if match and match.group(1) in errors:
                            pending.remove(item)
                            missing.append(item)
                # A report is only generated if the user explicitly requests it.
                # Keep PDFs out of the music download directory.
                successful = [x.name for x in sorted(folder.iterdir()) if x.is_file() and x.suffix.lower() == '.' + fmt.lower() and re.search(r'\[([^\[\]]{6,})\]$', x.stem)]
                self.events.put(('playlist_report', {
                    'downloaded': count, 'present': len(successful),
                    'failed': len(missing), 'pending': len(pending),
                    'cancelled': cancelled, 'url': url, 'folder': str(folder),
                    'downloaded_items': downloaded_items,
                    'missing_items': missing, 'pending_items': pending,
                    'failed_messages': list(dict.fromkeys(failed_messages)),
                }))
            if cancelled:
                self.events.put(('status', 'Download interrompido. Arquivos concluídos preservados; escolha se deseja um relatório PDF.'))
            if count == 0 and not playlist:
                raise RuntimeError('Download finalizado, mas não foi possível localizar os arquivos para registrar. Confira a pasta de destino.')
            self.events.put(('status', f'{count} arquivo(s) baixado(s) e registrado(s).'))
        except Exception as exc:
            self.events.put(('error', str(exc)))
        finally:
            if not queue_item:
                self.events.put(('done', None))

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
        except Exception as exc:
            messagebox.showerror('Demucs', 'Falha ao carregar o Demucs empacotado:\n' + repr(exc) + '\n\nEnvie esta mensagem para corrigirmos o build.')
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
        self.had_error = False
        self.busy = True
        self.stem_button.configure(state='disabled')
        threading.Thread(target=self.stems_worker, args=(list(self.files), folder, self.stem_mode.get(), self.stem_format.get(), start, end, self.stem_quality.get()), daemon=True).start()

    def stems_worker(self, files, folder, mode, fmt, start, end, quality='Rápido'):
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
                    if quality == 'Alta qualidade':
                        cmd += ['--shifts', '2', '--overlap', '0.5']
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
        if end is None:
            raise ValueError('Informe o horário final do corte.')
        if end is not None and end <= start:
            raise ValueError('O fim do corte deve ser maior que o início.')
        return start, end

    def open_waveform_editor(self):
        """Interactive waveform selection using mouse; keeps manual time fields synchronized."""
        if not self.files:
            messagebox.showwarning('Editor visual', 'Selecione uma música primeiro.')
            return
        ffmpeg = shutil.which('ffmpeg')
        ffprobe = shutil.which('ffprobe')
        if not ffmpeg or not ffprobe:
            messagebox.showerror('Editor visual', 'FFmpeg/FFprobe não encontrados.')
            return
        src = self.files[0]
        win = ctk.CTkToplevel(self)
        win.title('DJ Tavares | Editor visual')
        try:
            win.iconbitmap(str(_BUNDLE / 'assets' / 'dj_tavares.ico'))
        except Exception:
            pass
        win.geometry('980x570')
        win.configure(fg_color=BG)
        win.transient(self)
        ctk.CTkLabel(win, text='Editor visual • ' + src.name, font=('Segoe UI', 18, 'bold')).pack(padx=20, pady=(18, 4), anchor='w')
        ctk.CTkLabel(win, text='Clique e arraste na onda para marcar o trecho. O corte será aplicado na conversão.', text_color=MUTED).pack(padx=20, anchor='w')
        canvas = tk.Canvas(win, height=190, bg='#111D30', highlightthickness=0, cursor='crosshair')
        canvas.pack(fill='x', padx=20, pady=(20, 10))
        info = ctk.CTkLabel(win, text='Carregando forma de onda...', text_color=MUTED)
        info.pack(pady=5)
        state = {'duration': 0, 'samples': [], 'start': 0., 'end': 0., 'drag': False, 'cursor': 0., 'playing': False, 'started': 0., 'preview_file': None, 'zoom': 1.0, 'view': 0.0}
        def fmt(seconds):
            return f'{int(seconds//3600):02d}:{int(seconds%3600//60):02d}:{seconds%60:05.2f}'
        def draw():
            canvas.delete('all')
            w = max(canvas.winfo_width(), 200)
            h = max(canvas.winfo_height(), 100)
            samples = state['samples']
            if not samples:
                return
            n = len(samples)
            for x in range(w):
                idx = min(n-1, int((state['view'] + x/w / state['zoom'])*n))
                amp = samples[idx] * (h*.44)
                canvas.create_line(x, h/2-amp, x, h/2+amp, fill='#328CFF')
            duration = state['duration']
            if not duration: return
            canvas.create_line((state['cursor']/duration-state['view'])*state['zoom']*w, 0, (state['cursor']/duration-state['view'])*state['zoom']*w, h, fill='#FFCC55', width=2, tags='playhead')
            a = int((min(state['start'], state['end']) / duration-state['view'])*state['zoom']*w)
            b = int((max(state['start'], state['end']) / duration-state['view'])*state['zoom']*w)
            canvas.create_rectangle(a, 0, b, h, outline='#86D7FF', width=2, fill='', stipple='gray25')
            canvas.create_line(a, 0, a, h, fill='#D4F2FF', width=3)
            canvas.create_line(b, 0, b, h, fill='#D4F2FF', width=3)
            info.configure(text=f'Início: {fmt(min(state["start"], state["end"]))}   •   Fim: {fmt(max(state["start"], state["end"]))}   •   Duração total: {fmt(duration)}')
        def pos(event):
            return max(0., min(state['duration'], (state['view'] + event.x/max(canvas.winfo_width(), 1)/state['zoom'])*state['duration']))
        def down(event):
            if state['duration']:
                state['start'] = state['end'] = pos(event)
                state['drag'] = True
                draw()
        def move(event):
            if state['drag']:
                state['end'] = pos(event)
                draw()
        def up(event):
            state['drag'] = False
            move(event)
        def seek(event):
            state['cursor'] = pos(event)
            stop_audio()
            draw()
        canvas.bind('<Button-3>', seek)
        def zoom(change):
            old = state['zoom']
            state['zoom'] = max(1.0, min(24.0, old * change))
            state['view'] = max(0., min(1.-1./state['zoom'], state['cursor']/max(state['duration'],1)-.5/state['zoom']))
            draw()
        def scroll(event):
            state['view'] = max(0., min(1.-1./state['zoom'], state['view'] - (event.delta/120)*.1/state['zoom']))
            draw()
        canvas.bind('<MouseWheel>', scroll)
        canvas.bind('<Button-1>', down)
        canvas.bind('<B1-Motion>', move)
        canvas.bind('<ButtonRelease-1>', up)
        canvas.bind('<Configure>', lambda e: draw())
        import time
        def stop_audio():
            state['playing'] = False
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception: pass
        def play_audio(selection=False):
            if not state['duration']: return
            stop_audio()
            start, end = sorted((state['start'], state['end'])) if selection else (state['cursor'], state['duration'])
            if end-start < .1: return
            def prepare():
                try:
                    import winsound
                    fd, filename = tempfile.mkstemp(prefix='dj_tavares_player_', suffix='.wav'); os.close(fd)
                    cmd = [ffmpeg, '-y', '-nostdin', '-v', 'error', '-ss', str(start), '-i', str(src), '-t', str(end-start), '-vn', '-ac', '2', '-ar', '22050', '-c:a', 'pcm_s16le', filename]
                    self.run_checked(cmd, timeout=240)
                    def begin():
                        if not win.winfo_exists(): return
                        state['preview_file'] = filename
                        state['cursor'] = start
                        state['started'] = time.monotonic()
                        state['play_from'] = start
                        state['playing'] = True
                        state['stop_at'] = end
                        winsound.PlaySound(filename, winsound.SND_FILENAME | winsound.SND_ASYNC)
                        tick()
                    self.after(0, begin)
                except Exception as exc:
                    self.after(0, lambda msg=str(exc): info.configure(text='Falha na prévia: '+msg) if win.winfo_exists() else None)
            threading.Thread(target=prepare, daemon=True).start()
        def tick():
            if not win.winfo_exists() or not state['playing']: return
            state['cursor'] = min(state['stop_at'], state['cursor'] if not state['started'] else state['play_from'] + time.monotonic()-state['started'])
            draw()
            if state['cursor'] >= state['stop_at']:
                stop_audio()
            else:
                win.after(90, tick)
        def apply():
            a, b = sorted((state['start'], state['end']))
            if b-a < .1:
                messagebox.showwarning('Seleção', 'Marque um trecho com pelo menos 0,1 segundo.', parent=win)
                return
            self.trim_start.set(fmt(a))
            self.trim_end.set(fmt(b))
            self.trim_enabled.set(True)
            stop_audio()
            win.destroy()
        player = ctk.CTkFrame(win, fg_color=PANEL)
        player.pack(fill='x', padx=20, pady=(4, 4))
        ctk.CTkButton(player, text='▶ Reproduzir', command=play_audio, width=125).pack(side='left', padx=8, pady=8)
        ctk.CTkButton(player, text='▶ Ouvir seleção', command=lambda: play_audio(True), width=140).pack(side='left', padx=8)
        ctk.CTkButton(player, text='■ Parar', command=stop_audio, width=90, fg_color='#34445C').pack(side='left', padx=8)
        ctk.CTkButton(player, text='Zoom +', command=lambda: zoom(1.7), width=75, fg_color='#344B6D').pack(side='left', padx=4)
        ctk.CTkButton(player, text='Zoom −', command=lambda: zoom(1/1.7), width=75, fg_color='#344B6D').pack(side='left', padx=4)
        ctk.CTkLabel(win, text='Botão direito: mover cursor • Roda do mouse: navegar na faixa ampliada • Zoom +/-', text_color=MUTED).pack(padx=20, anchor='w')
        fades = ctk.CTkFrame(win, fg_color='transparent')
        fades.pack(fill='x', padx=20, pady=6)
        ctk.CTkCheckBox(fades, text='Fade-in', variable=self.fade_in_var).pack(side='left', padx=8)
        ctk.CTkCheckBox(fades, text='Fade-out', variable=self.fade_out_var).pack(side='left', padx=8)
        ctk.CTkLabel(fades, text='Duração (segundos)').pack(side='left', padx=8)
        ctk.CTkEntry(fades, textvariable=self.fade_duration_var, width=70).pack(side='left')
        win.protocol('WM_DELETE_WINDOW', lambda: (stop_audio(), win.destroy()))
        buttons = ctk.CTkFrame(win, fg_color='transparent')
        buttons.pack(fill='x', padx=20, pady=10)
        ctk.CTkButton(buttons, text='Aplicar seleção ao corte', command=apply, width=220).pack(side='right')
        ctk.CTkButton(buttons, text='Cancelar', fg_color='#34445C', command=lambda: (stop_audio(), win.destroy())).pack(side='right', padx=8)
        def generate():
            try:
                probe = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(src)], capture_output=True, text=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                duration = float(probe.stdout.strip())
                if duration <= 0:
                    raise ValueError('Duração inválida')
                # Limit decoding to 60k samples even for long audio files.
                rate = max(1, min(400, int(60000 / duration)))
                raw = subprocess.run([ffmpeg, '-nostdin', '-v', 'error', '-i', str(src), '-vn', '-ac', '1', '-ar', str(rate), '-f', 's16le', '-'], capture_output=True, timeout=180, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                if raw.returncode:
                    raise RuntimeError(raw.stderr.decode(errors='replace')[-250:])
                values = memoryview(raw.stdout).cast('h')
                chunk = max(1, len(values)//1600)
                samples = [max(abs(v) for v in values[i:i+chunk])/32768 for i in range(0,len(values),chunk)]
                def loaded():
                    if not win.winfo_exists(): return
                    state.update(duration=duration, samples=samples, start=0., end=duration)
                    draw()
                self.after(0, loaded)
            except Exception as exc:
                self.after(0, lambda msg=str(exc): info.configure(text='Não foi possível carregar: ' + msg) if win.winfo_exists() else None)
        threading.Thread(target=generate, daemon=True).start()

    def preview_cut(self):
        """Render a short PCM WAV preview using bundled FFmpeg; play with Windows audio."""
        if not self.files:
            messagebox.showwarning('Prévia', 'Selecione um arquivo primeiro.')
            return
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            messagebox.showerror('Prévia', 'FFmpeg não encontrado no pacote do aplicativo.')
            return
        try:
            import winsound
            # Preview fields apply even if the conversion checkbox is off.
            start = parse_time(self.trim_start.get()) or 0.0
            end = parse_time(self.trim_end.get())
            if end is not None and end <= start:
                raise ValueError('O fim deve ser maior que o início.')
            duration = min((end - start) if end is not None else 30.0, 30.0)
            if duration <= 0:
                raise ValueError('Escolha um intervalo válido.')
            winsound.PlaySound(None, winsound.SND_PURGE)
            if self.preview_path:
                try:
                    Path(self.preview_path).unlink(missing_ok=True)
                except OSError:
                    pass
            fd, path = tempfile.mkstemp(suffix='.wav', prefix='music_preview_')
            os.close(fd)
            self.preview_path = path
            command = [ffmpeg, '-y', '-nostdin', '-hide_banner', '-loglevel', 'error',
                       '-ss', str(start), '-i', str(self.files[0]), '-t', str(duration),
                       '-vn', '-ac', '2', '-ar', '44100', '-c:a', 'pcm_s16le', path]
            self.run_checked(command, timeout=120)
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            self.status_var.set('Reproduzindo prévia (até 30 segundos).')
        except Exception as exc:
            messagebox.showerror('Prévia', f'Não foi possível reproduzir: {exc}')

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
        try:
            fade_seconds = float(self.fade_duration_var.get().replace(',', '.'))
            if not 0 <= fade_seconds <= 60:
                raise ValueError()
        except ValueError:
            self.busy = False
            self.start_button.configure(state='normal')
            messagebox.showerror('Fade inválido', 'Informe uma duração de 0 a 60 segundos.')
            return
        threading.Thread(target=self.worker, args=(ffmpeg, list(self.files), folder, self.format_var.get(), self.bitrate_var.get(), start, end, self.fade_in_var.get(), self.fade_out_var.get(), fade_seconds), daemon=True).start()

    def worker(self, ffmpeg, files, folder, fmt, bitrate, start, end, fade_in, fade_out, fade_seconds):
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
            if (fade_in or fade_out) and fade_seconds:
                filters = []
                if fade_in:
                    filters.append(f'afade=t=in:st=0:d={fade_seconds:g}')
                if fade_out:
                    duration = (end - (start or 0)) if end is not None else None
                    if duration is None:
                        probe = shutil.which('ffprobe')
                        if probe:
                            try:
                                r = subprocess.run([probe, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(src)], capture_output=True, text=True, timeout=30, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                                duration = float(r.stdout.strip()) - (start or 0)
                            except (ValueError, OSError, subprocess.SubprocessError):
                                duration = None
                    if duration is None:
                        self.events.put(('error', f'{src.name}: duração indisponível para fade-out.'))
                        self.events.put(('progress', (index + 1) / total))
                        continue
                    filters.append(f'afade=t=out:st={max(0, duration - fade_seconds):g}:d={min(fade_seconds, duration):g}')
                command += ['-af', ','.join(filters)]
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

    def show_playlist_report_options(self, data):
        """Offer report scope after completion; never create a file by default."""
        downloaded = data.get('downloaded', 0)
        failed = data.get('failed', 0)
        pending = data.get('pending', 0)
        state = 'Interrompida' if data.get('cancelled') else 'Concluída'
        self.status_var.set(f'Playlist {state.lower()}: {downloaded} novos; {failed} falhas; {pending} pendentes.')
        dialog = ctk.CTkToplevel(self)
        dialog.title('Resumo da playlist - DJ Tavares')
        dialog.geometry('590x370')
        dialog.minsize(550, 340)
        dialog.configure(fg_color=BG)
        dialog.transient(self)
        dialog.grab_set()
        ctk.CTkLabel(dialog, text='RELATÓRIO DA PLAYLIST', font=('Segoe UI', 19, 'bold'), text_color=WHITE).pack(pady=(22, 12))
        ctk.CTkLabel(dialog, text=f'Situação: {state}  |  Novos arquivos: {downloaded}\nFalhas detectadas: {failed}  |  Ainda não tentadas: {pending}',
            font=('Segoe UI', 14), text_color=MUTED, justify='center').pack(pady=(0, 14))
        ctk.CTkLabel(dialog, text='Qual relatório deseja gerar?', text_color=WHITE).pack(pady=(0, 9))
        def generate(mode):
            try:
                path = self.write_playlist_pdf(data, mode)
                dialog.grab_release()
                dialog.destroy()
                self.status_var.set('PDF salvo em: ' + str(path))
                if messagebox.askyesno('Relatório PDF', f'Relatório salvo em:\n{path}\n\nAbrir agora?'):
                    try:
                        os.startfile(str(path))
                    except (OSError, AttributeError):
                        webbrowser.open(path.as_uri())
            except Exception as exc:
                messagebox.showerror('Falha ao gerar PDF', str(exc), parent=dialog)
        ctk.CTkButton(dialog, text='Relatório completo (baixadas + erros + pendentes)', height=39,
            command=lambda: generate('full')).pack(fill='x', padx=38, pady=5)
        ctk.CTkButton(dialog, text='Somente erros ocorridos', height=39, fg_color='#295278',
            command=lambda: generate('errors')).pack(fill='x', padx=38, pady=5)
        def dismiss():
            dialog.grab_release()
            dialog.destroy()
        ctk.CTkButton(dialog, text='Não gerar relatório', height=35, fg_color='#354155',
            command=dismiss).pack(fill='x', padx=38, pady=(5, 15))
        dialog.protocol('WM_DELETE_WINDOW', dismiss)

    @staticmethod
    def write_playlist_pdf(data, mode):
        """Write an opt-in PDF to the app's separate reports directory."""
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from xml.sax.saxutils import escape
        if mode not in ('full', 'errors'):
            raise ValueError('Tipo de relatório inválido')
        reports_dir = BASE / 'Relatorios'
        reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        kind = 'COMPLETO' if mode == 'full' else 'SOMENTE_ERROS'
        path = reports_dir / f'DJ_TAVARES_PLAYLIST_{kind}_{stamp}.pdf'
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='DJTitle', parent=styles['Title'], textColor=colors.HexColor('#1362A4'), fontSize=17, alignment=TA_CENTER, spaceAfter=15))
        styles.add(ParagraphStyle(name='DJItem', parent=styles['BodyText'], leading=15, spaceAfter=9, wordWrap='CJK'))
        doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=45, leftMargin=45, topMargin=42, bottomMargin=42)
        story = [Paragraph('DJ TAVARES | RELATÓRIO DE PLAYLIST', styles['DJTitle'])]
        status = 'INTERROMPIDA' if data.get('cancelled') else 'CONCLUÍDA'
        info = [f'Situação: {status}', f'Data: {datetime.now():%d/%m/%Y %H:%M}',
                f'Novos arquivos registrados: {data.get("downloaded", 0)}',
                f'Falhas detectadas: {data.get("failed", 0)}',
                f'Pendentes não tentadas: {data.get("pending", 0)}',
                f'Origem: {data.get("url", "")}']
        for line in info:
            story.append(Paragraph(escape(str(line)), styles['DJItem']))
        def section(title, entries):
            story.append(Spacer(1, 12))
            story.append(Paragraph(escape(title), styles['Heading2']))
            if not entries:
                story.append(Paragraph('Nenhum item identificado.', styles['DJItem']))
            for entry in entries:
                story.append(Paragraph(escape(str(entry)).replace('\n', '<br/>'), styles['DJItem']))
        if mode == 'full':
            section('Músicas baixadas com sucesso', data.get('downloaded_items', []))
        section('Falhas durante o download', data.get('missing_items', []))
        if mode == 'full':
            section('Músicas pendentes (não tentadas)', data.get('pending_items', []))
        # Technical error details may help identify unavailable/private tracks.
        if data.get('failed_messages'):
            section('Mensagens de erro da origem', data['failed_messages'])
        doc.build(story)
        return path

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
                    self.had_error = True
                    self.status_var.set('Erro: ' + value)
                elif kind == 'playlist_report':
                    self.show_playlist_report_options(value)
                elif kind == 'transfer_detail':
                    if self.page == 'Links' and hasattr(self, 'transfer_detail') and self.transfer_detail.winfo_exists():
                        self.transfer_detail.configure(text=value[:110])
                elif kind == 'queue_progress':
                    if self.page == 'Links' and hasattr(self, 'queue_progress'):
                        self.queue_progress.set(value)
                    self.refresh_download_queue()
                elif kind == 'queue_finished':
                    self.queue_active = False
                    self.busy = False
                    self.download_queue.clear()
                    self.queue_index = 0
                    self.refresh_download_queue()
                    self.status_var.set('Fila interrompida.' if self.queue_cancelled else 'Fila finalizada. Consulte o Histórico e a Biblioteca.')
                elif kind == 'done':
                    self.busy = False
                    if not self.had_error and not self.transfer_cancel.is_set() and self.page != 'Links':
                        self.status_var.set('Processamento concluído. Consulte a Biblioteca e o Histórico.')
                    if self.page == 'Conversor':
                        self.start_button.configure(state='normal')
                    elif self.page == 'Studio DJ':
                        self.stem_button.configure(state='normal')
                    elif self.page == 'Links':
                        self.link_button.configure(state='normal')
                        if hasattr(self, 'pause_transfer_button') and self.pause_transfer_button.winfo_exists():
                            self.pause_transfer_button.configure(text='Ⅱ  Pausar playlist')
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
