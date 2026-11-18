"""
Helpdesk Recorder - aplicativo da bandeja (MVP 1)

Uso:
  python app.py              -> abre na bandeja (atalho global para iniciar/parar)
  python app.py --teste 10   -> grava 10 segundos sem bandeja, para validar o áudio
"""

import argparse
import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

from recorder import Recorder

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
PADRAO = {"pasta_saida": "atendimentos", "atalho": "ctrl+alt+r"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "helpdesk_recorder.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("app")


def carregar_config():
    cfg = dict(PADRAO)
    if CONFIG_PATH.exists():
        cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    pasta = Path(cfg["pasta_saida"])
    if not pasta.is_absolute():
        pasta = BASE_DIR / pasta
    cfg["pasta_saida"] = pasta
    return cfg


def modo_teste(segundos):
    cfg = carregar_config()
    rec = Recorder(cfg["pasta_saida"])
    pasta = rec.start()
    print(f"Gravando {segundos}s em {pasta} ...")
    print("Fale no microfone e toque algum áudio no fone (ex.: um vídeo).")
    time.sleep(segundos)
    pasta, meta = rec.stop()
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"Pronto. Ouça os arquivos em: {pasta}")


def modo_bandeja():
    import keyboard
    import pystray
    from PIL import Image, ImageDraw

    cfg = carregar_config()
    rec = Recorder(cfg["pasta_saida"])
    estado_lock = threading.Lock()

    def icone(gravando):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        cor = (220, 38, 38, 255) if gravando else (120, 120, 120, 255)
        d.ellipse((8, 8, 56, 56), fill=cor)
        return img

    def avisar(tray, msg):
        try:
            tray.notify(msg, "Helpdesk Recorder")
        except Exception:
            log.info("Aviso: %s", msg)

    tray = None

    def alternar(*_):
        with estado_lock:
            try:
                if rec.recording:
                    pasta, meta = rec.stop()
                    tray.icon = icone(False)
                    tray.title = "Helpdesk Recorder - parado"
                    avisar(tray, f"Gravação salva ({meta['duracao_segundos']}s).")
                else:
                    rec.start()
                    tray.icon = icone(True)
                    tray.title = "Helpdesk Recorder - GRAVANDO"
                    avisar(tray, "Gravando atendimento.")
            except Exception as e:
                log.exception("Erro ao alternar gravação")
                avisar(tray, f"Erro: {e}")
            tray.update_menu()

    def abrir_pasta(*_):
        cfg["pasta_saida"].mkdir(parents=True, exist_ok=True)
        os.startfile(cfg["pasta_saida"])  # só existe no Windows

    def sair(*_):
        with estado_lock:
            if rec.recording:
                try:
                    rec.stop()
                except Exception:
                    log.exception("Erro ao finalizar na saída")
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        tray.stop()

    menu = pystray.Menu(
        pystray.MenuItem(
            lambda item: "Parar gravação" if rec.recording else "Iniciar gravação",
            alternar,
            default=True,
        ),
        pystray.MenuItem("Abrir pasta das gravações", abrir_pasta),
        pystray.MenuItem("Sair", sair),
    )
    tray = pystray.Icon("helpdesk_recorder", icone(False), "Helpdesk Recorder - parado", menu)

    keyboard.add_hotkey(cfg["atalho"], alternar)
    log.info("Pronto. Atalho global: %s", cfg["atalho"])
    tray.run()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--teste", type=int, metavar="SEGUNDOS",
                    help="grava N segundos sem abrir a bandeja")
    args = ap.parse_args()
    if args.teste:
        modo_teste(args.teste)
    else:
        modo_bandeja()
