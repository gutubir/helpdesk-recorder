"""
Helpdesk Recorder - núcleo de captura (MVP 1)

Grava, ao mesmo tempo:
  - microfone padrão do Windows  -> microfone.wav  (você)
  - áudio que sai no fone padrão -> sistema.wav    (cliente, via WASAPI loopback)

Cada atendimento vira uma pasta:
  atendimentos/2026-11-17_17-50-12/
      microfone.wav
      sistema.wav
      meta.json

Detalhe importante: o loopback do Windows NÃO entrega dados quando nada está
tocando. Por isso cada trilha preenche os silêncios com zeros usando o relógio,
mantendo microfone.wav e sistema.wav com a mesma duração e alinhados no tempo.
"""

import json
import logging
import queue
import threading
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import pyaudiowpatch as pyaudio

log = logging.getLogger("recorder")

CHUNK = 1024  # frames por leitura
GAP_TOLERANCE_S = 0.25  # lacuna mínima (s) para inserir silêncio


class _Track:
    """Uma trilha de áudio (mono, taxa nativa do dispositivo) gravada em WAV."""

    def __init__(self, pa, device, path, nome):
        self.pa = pa
        self.device = device
        self.path = Path(path)
        self.nome = nome
        self.rate = int(device["defaultSampleRate"])
        self.channels = int(device["maxInputChannels"])
        self.queue = queue.Queue()
        self.frames_written = 0
        self.t0 = None
        self.t_end = None
        self.stream = None
        self.wav = None
        self.thread = None
        self._stop = threading.Event()

    # -- callback do PortAudio (thread de áudio: só enfileira) ---------------
    def _callback(self, in_data, frame_count, time_info, status):
        self.queue.put((time.monotonic(), in_data))
        return (None, pyaudio.paContinue)

    def _to_mono(self, data):
        audio = np.frombuffer(data, dtype=np.int16)
        if self.channels > 1:
            audio = audio.reshape(-1, self.channels).mean(axis=1)
        return audio.astype(np.int16)

    def _pad(self, n_frames):
        """Escreve n_frames de silêncio, em blocos."""
        while n_frames > 0:
            bloco = min(n_frames, self.rate)
            self.wav.writeframes(np.zeros(bloco, dtype=np.int16).tobytes())
            self.frames_written += bloco
            n_frames -= bloco

    # -- thread que escreve no disco -----------------------------------------
    def _writer(self):
        while True:
            try:
                ts, data = self.queue.get(timeout=0.2)
            except queue.Empty:
                if self._stop.is_set():
                    break
                continue
            mono = self._to_mono(data)
            # onde este bloco deveria começar, segundo o relógio
            inicio_esperado = (ts - self.t0 - len(mono) / self.rate) * self.rate
            lacuna = int(inicio_esperado - self.frames_written)
            if lacuna > GAP_TOLERANCE_S * self.rate:
                self._pad(lacuna)
            self.wav.writeframes(mono.tobytes())
            self.frames_written += len(mono)

    def start(self, t0):
        self.t0 = t0
        self.wav = wave.open(str(self.path), "wb")
        self.wav.setnchannels(1)
        self.wav.setsampwidth(2)  # int16
        self.wav.setframerate(self.rate)
        self.thread = threading.Thread(target=self._writer, daemon=True)
        self.thread.start()
        self.stream = self.pa.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.rate,
            input=True,
            input_device_index=int(self.device["index"]),
            frames_per_buffer=CHUNK,
            stream_callback=self._callback,
        )
        log.info("Trilha '%s' iniciada: %s (%d Hz, %d canais)",
                 self.nome, self.device["name"], self.rate, self.channels)

    def stop(self, t_end):
        self.t_end = t_end
        try:
            self.stream.stop_stream()
            self.stream.close()
        except Exception:
            log.exception("Erro ao fechar stream de %s", self.nome)
        self._stop.set()
        self.thread.join()
        # completa até o fim real da gravação
        total = int((t_end - self.t0) * self.rate)
        if total > self.frames_written:
            self._pad(total - self.frames_written)
        self.wav.close()
        return self.frames_written / self.rate


class Recorder:
    def __init__(self, pasta_base):
        self.pasta_base = Path(pasta_base)
        self.pa = None
        self.mic = None
        self.sistema = None
        self.pasta = None
        self.inicio = None
        self.recording = False
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self.recording:
                raise RuntimeError("Já existe uma gravação em andamento.")

            self.inicio = datetime.now()
            self.pasta = self.pasta_base / self.inicio.strftime("%Y-%m-%d_%H-%M-%S")
            self.pasta.mkdir(parents=True, exist_ok=True)

            self.pa = pyaudio.PyAudio()
            try:
                mic_dev = self.pa.get_default_input_device_info()
            except Exception as e:
                self.pa.terminate()
                raise RuntimeError("Nenhum microfone padrão encontrado no Windows.") from e
            try:
                loop_dev = self.pa.get_default_wasapi_loopback()
            except Exception as e:
                self.pa.terminate()
                raise RuntimeError(
                    "Não consegui abrir o loopback do fone padrão (WASAPI)."
                ) from e

            self.mic = _Track(self.pa, mic_dev, self.pasta / "microfone.wav", "microfone")
            self.sistema = _Track(self.pa, loop_dev, self.pasta / "sistema.wav", "sistema")

            t0 = time.monotonic()
            try:
                self.mic.start(t0)
                self.sistema.start(t0)
            except Exception:
                self._abortar()
                raise
            self.recording = True
            log.info("Gravação iniciada em %s", self.pasta)
            return self.pasta

    def _abortar(self):
        for t in (self.mic, self.sistema):
            try:
                if t and t.stream:
                    t.stream.close()
            except Exception:
                pass
            try:
                if t and t.wav:
                    t.wav.close()
            except Exception:
                pass
        self.pa.terminate()

    def stop(self):
        with self._lock:
            if not self.recording:
                raise RuntimeError("Nenhuma gravação em andamento.")
            t_end = time.monotonic()
            dur_mic = self.mic.stop(t_end)
            dur_sis = self.sistema.stop(t_end)
            self.pa.terminate()
            self.recording = False

            meta = {
                "inicio": self.inicio.isoformat(timespec="seconds"),
                "fim": datetime.now().isoformat(timespec="seconds"),
                "duracao_segundos": round(max(dur_mic, dur_sis), 1),
                "microfone": {
                    "arquivo": "microfone.wav",
                    "dispositivo": self.mic.device["name"],
                    "taxa_hz": self.mic.rate,
                },
                "sistema": {
                    "arquivo": "sistema.wav",
                    "dispositivo": self.sistema.device["name"],
                    "taxa_hz": self.sistema.rate,
                },
            }
            (self.pasta / "meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            log.info("Gravação finalizada: %.1fs em %s", meta["duracao_segundos"], self.pasta)
            return self.pasta, meta
