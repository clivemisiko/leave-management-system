# VPS Deployment

Target host:

```text
185-159-72-108.il-cloud-xip.com
```

## Docker Deployment

On the VPS:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin nginx
sudo systemctl enable --now docker
```

Upload the project to `/opt/leave_app_system`, then create `.env` on the VPS with production values.

Build and run:

```bash
cd /opt/leave_app_system
sudo docker compose up -d --build
sudo docker compose logs -f leave-app
```

Check locally on the VPS:

```bash
curl http://127.0.0.1:10000/db-check
```

## Nginx Reverse Proxy

Create `/etc/nginx/sites-available/leave-app`:

```nginx
server {
    listen 80;
    server_name 185-159-72-108.il-cloud-xip.com;

    client_max_body_size 2M;

    location / {
        proxy_pass http://127.0.0.1:10000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it:

```bash
sudo ln -sf /etc/nginx/sites-available/leave-app /etc/nginx/sites-enabled/leave-app
sudo nginx -t
sudo systemctl reload nginx
```

Then open:

```text
http://185-159-72-108.il-cloud-xip.com
```
