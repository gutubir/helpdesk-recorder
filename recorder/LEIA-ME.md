# Helpdesk Recorder – gravador

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
- Clique duplo no ícone também alterna. Menu: iniciar/parar, reenviar pendentes, abrir pasta, sair.
- Ao parar, o atendimento é enviado ao backend em segundo plano (veja a seção abaixo).
- Cada atendimento cria uma pasta em `atendimentos/AAAA-MM-DD_HH-MM-SS/`
  com os dois WAVs e um `meta.json`.
- Log em `helpdesk_recorder.log`.

## Envio automático ao backend

Ao parar a gravação, o app compacta o áudio (MP3 mono 16 kHz, ~0,25 MB/min) e envia ao backend.
O envio só conta como feito quando o backend confirma; aí a pasta ganha um `enviado.json`.

1. **ffmpeg** instalado (`winget install Gyan.FFmpeg`). Sem ele o app envia o WAV, que é bem maior.
2. Backend rodando (veja `backend/README.md`) e o mesmo `API_TOKEN` configurado aqui.
3. Crie `config.local.json` na pasta do gravador (ele **não vai para o Git**):

```
{ "api_token": "o-mesmo-token-do-backend" }
```

   Alternativa: definir a variável de ambiente `HELPDESK_API_TOKEN`.

Opções do `config.json`:

| Campo | Padrão | O que faz |
|---|---|---|
| `backend_url` | `http://localhost:8000` | Endereço do backend (muda se ele for para outro PC) |
| `enviar_automaticamente` | `true` | Envia ao parar a gravação e tenta os pendentes ao abrir |
| `compactar_antes_de_enviar` | `true` | Converte para MP3 antes de enviar |
| `apagar_local_apos_envio` | `false` | Apaga os WAV locais depois de enviados |
| `ffmpeg` | `ffmpeg` | Caminho do ffmpeg, se não estiver no PATH |

**Se o envio falhar** (backend desligado, token errado, sem rede), nada se perde: a pasta fica
pendente. Use "Reenviar pendentes" no menu, ou `python app.py --enviar-pendentes`. Ao abrir o app,
os pendentes também são tentados automaticamente.

## Testes

```
cd recorder
pip install pytest
pytest
```

Os testes cobrem compactação, envio e pendentes (com servidor falso e ffmpeg real). A captura de
áudio e a bandeja só podem ser testadas no Windows, na mão.

## Observações

- Se você trocar o fone padrão do Windows no meio da gravação, a trilha do
  sistema para de receber áudio. Troque antes de iniciar.
- WAV ocupa bastante espaço: ~5,5 MB por minuto, por trilha (uma ligação de 20 min
  gera ~220 MB nos dois arquivos). Por isso o envio ao backend compacta o áudio antes.
- Avise os clientes que a ligação é gravada (LGPD).
