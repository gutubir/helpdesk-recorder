# Helpdesk Recorder – MVP 1 (gravador)

Grava o atendimento em dois arquivos separados:

- `microfone.wav`: sua voz (microfone padrão do Windows)
- `sistema.wav`: o áudio do cliente (o que sai no fone padrão, via WASAPI loopback)

Os dois têm a mesma duração e ficam alinhados no tempo.

## Instalação (Windows)

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Passo 1: teste rápido (sem bandeja)

Com o GoTo aberto, ou qualquer vídeo tocando no fone:

```
python app.py --teste 10
```

Fale no microfone durante os 10 segundos. Depois abra a pasta indicada e ouça os
dois arquivos. Confira:

- `microfone.wav` tem só a sua voz?
- `sistema.wav` tem só o que toca no fone?
- Se você usa fone, a voz do cliente NÃO deve aparecer no `microfone.wav`.

## Passo 2: uso normal (bandeja)

```
python app.py
```

- Ícone cinza na bandeja = parado. Vermelho = gravando.
- Atalho global **Ctrl+Alt+R** inicia e para (muda em `config.json`).
- Clique duplo no ícone também alterna. Menu: abrir pasta, sair.
- Cada atendimento cria uma pasta em `atendimentos/AAAA-MM-DD_HH-MM-SS/`
  com os dois WAVs e um `meta.json`.
- Log em `helpdesk_recorder.log`.

## Observações

- Se você trocar o fone padrão do Windows no meio da gravação, a trilha do
  sistema para de receber áudio. Troque antes de iniciar.
- WAV ocupa bastante espaço (~2 MB/min por trilha). A compressão (Opus/MP3)
  entra no próximo passo, junto com o envio para o backend.
- Avise os clientes que a ligação é gravada (LGPD).
