# Deploy em VM do GCP com `systemd` + `nginx`

Guia passo a passo para publicar este dashboard em uma VM Linux no Google Cloud.

## Decisão recomendada

- Porta pública: `80` no `nginx`
- Porta interna da aplicação: `5000`
- Motivo: a `5001` já está em uso por `registro_de_eventos`, enquanto a `5000` está livre e já combina com o `dashboard.py`
- Modelo de execução: `systemd` rodando `python dashboard.py`

Este projeto já sobe com:

```bash
python dashboard.py
```

e o próprio código lê `PORT` do ambiente. Então a opção mais simples é rodar:

```bash
PORT=5000 python dashboard.py
```

## Visão da arquitetura

```text
Internet -> nginx :80 -> proxy_pass -> 127.0.0.1:5000 -> python dashboard.py
```

## 1. Confirmar a porta

Verifique se a `5000` está livre:

```bash
sudo ss -tulpn | grep :5000
```

Se não aparecer nada, a porta está livre para o dashboard.

## 2. Preparar a aplicação

Entre na pasta do projeto:

```bash
cd /opt/cog/dashboard
```

Confirme o Python do venv que será usado no serviço:

```bash
which python
readlink -f "$(which python)"
```

Guarde esse caminho. Ele será usado no `ExecStart`.

Exemplo comum:

```bash
/opt/cog/venv/bin/python
```

No ambiente que você levantou, o serviço antigo já usava:

```bash
/opt/cog/venv/bin/...
```

então o mais provável é que o novo serviço também deva usar esse mesmo venv.

## 3. Criar ou revisar o `.env`

Garanta que o arquivo `.env` do projeto exista com pelo menos:

```env
URL_API=https://...
API_TOKEN=...
SECRET_KEY=troque-esta-chave
PORT=5000
```

Se quiser conferir:

```bash
sed -n '1,120p' .env
```

## 4. Testar manualmente antes do serviço

Ainda dentro de `/opt/cog/dashboard`, suba a app manualmente com o venv:

```bash
PORT=5000 python dashboard.py
```

Em outro terminal, teste:

```bash
curl http://127.0.0.1:5000/health
```

Esperado:

```json
{"status":"ok"}
```

Se isso funcionar, o `systemd` vai funcionar com a mesma base.

## 5. Criar o serviço `systemd`

Como já existe um `cog.service` antigo, o caminho mais simples é editar o mesmo arquivo:

```bash
sudo nano /etc/systemd/system/cog.service
```

Substitua o conteúdo antigo por este e ajuste apenas se o caminho do venv for diferente:

```ini
[Unit]
Description=COG Dashboard (Flask-SocketIO)
After=network.target

[Service]
Type=simple
User=engeg
Group=engeg
WorkingDirectory=/opt/cog/dashboard
Environment=PORT=5000
EnvironmentFile=/opt/cog/dashboard/.env
ExecStart=/opt/cog/venv/bin/python /opt/cog/dashboard/dashboard.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Observações:

- `Environment=PORT=5000` força a app a subir na porta correta
- `EnvironmentFile` reaproveita as variáveis do `.env`
- `ExecStart` deve apontar para o Python real do venv
- `User` e `Group` foram alinhados com o serviço antigo que você mostrou: `engeg`
- o `WorkingDirectory` antigo era `/opt/cog/cog-ultimate`; para este projeto ele precisa virar `/opt/cog/dashboard`
- o `ExecStart` antigo chamava `gunicorn ... main:app`; para este projeto ele precisa apontar para `dashboard.py`

### 5.1. O que mudou em relação ao serviço antigo

Serviço antigo:

```ini
WorkingDirectory=/opt/cog/cog-ultimate
ExecStart=/opt/cog/venv/bin/gunicorn -k eventlet -w 1 -b 127.0.0.1:5000 main:app
```

Serviço novo deste dashboard:

```ini
WorkingDirectory=/opt/cog/dashboard
ExecStart=/opt/cog/venv/bin/python /opt/cog/dashboard/dashboard.py
```

Motivo da troca:

- o projeto atual sobe por `python dashboard.py`
- o arquivo principal agora é `dashboard.py`, não `main.py`
- o código atual já inicializa o `SocketIO` diretamente
- isso evita depender de `gunicorn` e `eventlet` se eles não fizerem parte do projeto atual

## 6. Ativar o serviço

Depois de salvar o arquivo:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cog
sudo systemctl start cog
```

Conferência:

```bash
sudo systemctl status cog
sudo journalctl -u cog -n 100 --no-pager
```

Teste local:

```bash
curl http://127.0.0.1:5000/health
```

## 7. Configurar o `nginx`

Como a `5001` já está ocupada por `registro_de_eventos`, o recomendado é deixar este dashboard atrás da `5000`.

Se ele tiver um domínio próprio, crie um site dedicado.

Arquivo:

```bash
sudo nano /etc/nginx/sites-available/cog
```

Conteúdo recomendado:

```nginx
server {
    listen 80;
    server_name dashboard.seu-dominio.com.br;

    access_log /var/log/nginx/cog.access.log;
    error_log  /var/log/nginx/cog.error.log;

    location / {
        proxy_pass         http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection "upgrade";
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

Ative o site:

```bash
sudo ln -sf /etc/nginx/sites-available/cog /etc/nginx/sites-enabled/cog
sudo nginx -t
sudo systemctl reload nginx
```

## 8. DNS e acesso

No provedor de DNS, aponte o subdomínio para o IP externo da VM.

Exemplo:

- `dashboard.seu-dominio.com.br` -> IP externo da VM

Depois teste:

```bash
curl -I http://dashboard.seu-dominio.com.br
```

## 9. Firewall no Google Cloud

No GCP, normalmente você só precisa liberar:

- `80/tcp`
- `443/tcp` quando ativar HTTPS

Não exponha `5000` nem `5001` para a internet se o `nginx` já faz o proxy.

## 10. Validar tudo

Checklist:

- `cog.service` está `active (running)`
- `curl http://127.0.0.1:5000/health` responde `{"status":"ok"}`
- `sudo nginx -t` retorna `syntax is ok`
- o domínio abre no navegador
- logs sem erro no `journalctl` e no `error.log` do `nginx`

## 11. Comandos úteis de operação

Status do serviço:

```bash
sudo systemctl status cog
```

Reiniciar:

```bash
sudo systemctl restart cog
```

Logs da aplicação:

```bash
sudo journalctl -u cog -f
```

Logs do `nginx`:

```bash
sudo tail -f /var/log/nginx/cog.error.log
sudo tail -f /var/log/nginx/cog.access.log
```

Portas em uso:

```bash
sudo ss -tulpn
```

## 12. Se quiser remover o `cog` antigo

Como o `cog` atual está desabilitado e parado, você pode reaproveitar esse nome para o novo serviço sem problema.

Se quiser remover apenas o site antigo do `nginx` e recriá-lo limpo:

```bash
sudo rm /etc/nginx/sites-enabled/cog
sudo nginx -t
sudo systemctl reload nginx
```

Depois recrie o arquivo em `sites-available/cog` com o conteúdo deste guia e ative de novo com `ln -sf`.

## 13. Receita curta com os caminhos do seu servidor

Pelo que você mostrou até agora, a sequência prática fica assim:

1. Atualizar o serviço:

```bash
sudo nano /etc/systemd/system/cog.service
```

Conteúdo:

```ini
[Unit]
Description=COG Dashboard (Flask-SocketIO)
After=network.target

[Service]
Type=simple
User=engeg
Group=engeg
WorkingDirectory=/opt/cog/dashboard
Environment=PORT=5000
EnvironmentFile=/opt/cog/dashboard/.env
ExecStart=/opt/cog/venv/bin/python /opt/cog/dashboard/dashboard.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

2. Recarregar e subir:

```bash
sudo systemctl daemon-reload
sudo systemctl enable cog
sudo systemctl restart cog
sudo systemctl status cog
```

3. Testar localmente:

```bash
curl http://127.0.0.1:5000/health
```

4. Ajustar o `nginx` em `/etc/nginx/sites-available/cog` para apontar para `127.0.0.1:5000`

5. Validar e recarregar o `nginx`:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 14. Problemas comuns

### `Permission denied` no serviço

Verifique permissões do projeto:

```bash
ls -ld /opt/cog/dashboard
ls -ld /opt/cog/dashboard/.git
```

### Serviço sobe, mas o `nginx` retorna `502 Bad Gateway`

Confira:

```bash
sudo systemctl status cog
sudo journalctl -u cog -n 100 --no-pager
curl http://127.0.0.1:5000/health
```

Se o `curl` local falhar, o problema está na app ou no `systemd`, não no `nginx`.

### WebSocket não conecta

Confira se o bloco `location /` contém:

```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```

## Resumo final

- Use a porta interna `5000`
- Deixe o `nginx` exposto em `80`
- Rode a app com `systemd`
- Faça o `nginx` apontar para `127.0.0.1:5000`
- Não exponha `5000` no firewall do GCP
