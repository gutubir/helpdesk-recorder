# Helpdesk Recorder

Grava atendimentos de suporte (microfone + áudio do sistema em trilhas separadas), transcreve e gera relatórios técnicos com IA.

## Estrutura

- `recorder/`: aplicativo Windows (Python) que grava os atendimentos e envia ao backend. **MVP 1 pronto.**
- `backend/`: API FastAPI para upload, transcrição e armazenamento. **MVP 2 em andamento** (relatórios com IA ficam para o MVP 3)
- `web/`: aplicação web para consulta e edição (planejado)

## Roadmap

1. Captura de áudio (microfone + loopback) ✅
2. Backend + transcrição por API ✅ (envio automático pelo gravador incluído)
3. Relatórios com IA
4. Aplicação web
5. Automação (início com o Windows, detecção de chamadas)

## LGPD

As gravações contêm dados de clientes. Nunca versione áudios, transcrições ou chaves de API (o `.gitignore` já bloqueia), avise os clientes sobre a gravação e siga a política da empresa.
