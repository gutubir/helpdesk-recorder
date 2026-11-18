# Backend (FastAPI)

Recebe os áudios do gravador, converte, transcreve e guarda tudo. Cada atendimento tem
dois canais: `microfone` (atendente) e `sistema` (cliente). Quem falou é definido pelo canal,
sem modelo de identificação de voz.

## Requisitos

- Python 3.10+
- **ffmpeg** no PATH (`winget install Gyan.FFmpeg`) ou caminho em `FFMPEG_PATH`
- Chave da OpenAI (ou use `TRANSCRIPTION_PROVIDER=fake` para testar sem custo)

## Instalação e execução

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # edite: API_TOKEN e OPENAI_API_KEY
uvicorn app.main:create_app --factory --env-file .env
```

Documentação interativa das rotas: http://localhost:8000/docs

## Rotas

Todas (exceto `/health`) exigem `Authorization: Bearer <API_TOKEN>` quando `API_TOKEN` está definido.

| Método | Rota | O que faz |
|---|---|---|
| GET | `/health` | Verifica se está no ar |
| POST | `/atendimentos` | Envia `microfone` (obrigatório), `sistema` e `meta` (JSON com `inicio` e `duracao_segundos`). Responde 202 e transcreve em segundo plano |
| GET | `/atendimentos` | Lista (mais recentes primeiro; `limite`, `deslocamento`) |
| GET | `/atendimentos/{id}` | Status, transcrição por turnos e texto da conversa |
| GET | `/atendimentos/{id}/audio/{canal}` | Baixa o áudio original (`microfone` ou `sistema`) |
| POST | `/atendimentos/{id}/reprocessar` | Refaz a transcrição |
| DELETE | `/atendimentos/{id}` | Apaga registro, transcrição e áudios |

Status: `recebido` → `transcrevendo` → `transcrito` (ou `erro`, com a mensagem em `erro`).

### Teste rápido com a pasta gerada pelo gravador

```
curl -H "Authorization: Bearer SEU_TOKEN" ^
  -F microfone=@atendimentos\2026-11-18_10-00-00\microfone.wav ^
  -F sistema=@atendimentos\2026-11-18_10-00-00\sistema.wav ^
  -F "meta=@atendimentos\2026-11-18_10-00-00\meta.json;type=application/json" ^
  http://localhost:8000/atendimentos
```

(`meta` pode ser enviado como arquivo ou como texto JSON.)

## Como funciona o processamento

1. Cada canal é convertido para MP3 mono 16 kHz (~0,25 MB/min). O WAV do gravador tem ~5,5 MB/min e
   estouraria o limite de 25 MB da API em ligações longas.
2. Cada canal é transcrito separadamente (`whisper-1`, que devolve segmentos com tempo).
3. Trechos de silêncio que o modelo "inventa" (ex.: "Legendas pela comunidade") são descartados.
4. Os dois canais são intercalados por tempo e falas seguidas da mesma pessoa viram um turno.

O provedor de transcrição é trocável: crie uma classe com `transcribe(audio_path, language)` em
`app/transcription/` e registre em `get_provider` (por exemplo, faster-whisper local).

## Dados

Em `data/` (não vai para o Git): banco `helpdesk.db` (SQLite) e `atendimentos/<id>/` com o áudio
original e o MP3 convertido. Para mover para outro PC, copie a pasta `data/` e o `.env`.

## Testes

```
pytest
```

`test_api.py` exige `fastapi` e `httpx`; os demais testes usam ffmpeg real e transcrição simulada.

## LGPD

Os áudios são dados pessoais de clientes. Com `TRANSCRIPTION_PROVIDER=openai`, o áudio é enviado
à OpenAI: confirme com a empresa antes de usar com ligações reais. Use `DELETE /atendimentos/{id}`
para cumprir prazos de retenção.
