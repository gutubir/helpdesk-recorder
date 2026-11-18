"""Servidor HTTP mínimo para testar o cliente, sem depender do backend real."""

import json
import threading
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, HTTPServer


class ServidorFalso:
    def __init__(self, status=202, resposta=None, token_esperado=None):
        self.recebidos = []
        self.status = status
        self.resposta = resposta if resposta is not None else {"id": 7, "status": "recebido"}
        self.token_esperado = token_esperado
        externo = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                tamanho = int(self.headers.get("Content-Length", 0))
                corpo = self.rfile.read(tamanho)
                if externo.token_esperado and self.headers.get("Authorization") != f"Bearer {externo.token_esperado}":
                    return self._responder(401, {"detail": "Token inválido ou ausente"})
                msg = BytesParser().parsebytes(
                    b"Content-Type: " + self.headers["Content-Type"].encode() + b"\r\n\r\n" + corpo
                )
                partes = {}
                for p in msg.get_payload():
                    nome = p.get_param("name", header="content-disposition")
                    partes[nome] = {
                        "filename": p.get_filename(),
                        "dados": p.get_payload(decode=True),
                    }
                externo.recebidos.append({"caminho": self.path, "partes": partes})
                self._responder(externo.status, externo.resposta)

            def _responder(self, status, obj):
                dados = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def log_message(self, *a):
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_port}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def parar(self):
        self.httpd.shutdown()
        self.httpd.server_close()
