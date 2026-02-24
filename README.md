# Inteplast

We are using this template for backend fastapi and frontend react: 
https://github.com/fastapi/full-stack-fastapi-template


# Start

## backend:
docker compose up -d db backend prestart


## frontend:


## close docker:
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

