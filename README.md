# Inteplast

We are using this template for backend fastapi and frontend react: 
https://github.com/fastapi/full-stack-fastapi-template


# Docker 

```powershell
Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
```

It needs ~30-60 s before the engine answers. Check it is up:

```powershell
docker info --format "{{.ServerVersion}}"     # prints e.g. 28.5.1 when ready
```


## Backend

Pick ONE:

```powershell
docker compose up -d db prestart backend              # normal
docker compose up -d --build db prestart backend      # after changing backend/
docker compose watch backend                          # dev mode: auto-reload, no rebuild
```

`watch backend` replaces the `up` (it starts db + prestart too). Foreground, Ctrl-C to stop.
Always name the service: bare `docker compose watch` starts frontend, proxy, adminer, playwright.

Optional, in another terminal:

```powershell
docker compose exec backend python -m app.seed_features   # dummy data, only if DB empty
docker compose ps                                         # db + backend = Up (healthy)
docker compose exec backend alembic current               # must say ... (head)
```

`prestart` exits with code 0 - correct, it just applies the migrations.

## Frontend

```powershell
cd frontend
npm.cmd run dev          # npm install the first time only
```

-> http://localhost:5173



## Close Docker:
docker compose down
docker builder prune -f


# Docker start

docker rmi backend:latest prestart:latest frontend:latest 2>nul

cmddocker buildx prune -f
docker buildx rm default 2>nul
docker buildx create --use --name mybuilder

cmddocker compose up --build

OR

docker compose watch

http://localhost:5173



# frontend & backend run separately

in backend folder:
C:\Users\eduard.almar\AppData\Local\Programs\Python\Python312\Scripts\uv.exe sync

.\.venv\Scripts\Activate
deactivate (to deactivate venv)

uvicorn app.main:app --reload

In another terminal: 
npm install (only first time)
npm run dev

I think this does not work: it does not start postgre db => we have to use docker for the backend 


# clean frontend

In Chrome/Edge:

Go to http://localhost:5173
Press F12 to open DevTools
Go to Application tab (top menu)
In the left sidebar: Storage → Local Storage → http://localhost:5173
Right-click it → Clear
Refresh the page (F5)

