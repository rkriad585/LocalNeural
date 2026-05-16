# Deployment

## Production Considerations

### 1. Secret Key

Always generate a strong `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Never use the default or a weak key in production.

### 2. Database Backup

The SQLite database is at `.data/neural_memory.db`. Back it up regularly:

```bash
cp .data/neural_memory.db .data/backup-$(date +%Y%m%d).db
```

You can also use the built-in backup/restore from Settings → Database.

### 3. Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:59869;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. SSL/HTTPS

Use Certbot with Nginx:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 5. Process Manager (systemd)

```ini
[Unit]
Description=LocalNeural AI Chat
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/LocalNeural
ExecStart=/path/to/LocalNeural/venv/bin/python app.py
Restart=always
RestartSec=10
EnvironmentFile=/path/to/LocalNeural/.env

[Install]
WantedBy=multi-user.target
```

## Docker Deployment

### Image Building

```bash
docker build -t localneural:latest .
```

### Running

```bash
docker run -d \
  --name localneural \
  -p 59869:59869 \
  -e SECRET_KEY=your-key \
  -v localneural-data:/app/.data \
  --restart unless-stopped \
  localneural:latest
```

### Docker Compose (Production)

```yaml
version: '3.8'
services:
  localneural:
    build: .
    ports:
      - "59869:59869"
    environment:
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - localneural_data:/app/.data
    restart: unless-stopped

volumes:
  localneural_data:
```

## Security Checklist

- [ ] Strong `SECRET_KEY` generated and set
- [ ] HTTPS enabled behind reverse proxy
- [ ] Admin email/password set in `.env`
- [ ] Rate limiting configured (default: on)
- [ ] Password minimum length enforced (8 chars)
- [ ] CSRF protection active (`X-Requested-With` check)
- [ ] Sessions expire after 72 hours
- [ ] Database file is backed up
- [ ] Firewall limits access to port 59869
