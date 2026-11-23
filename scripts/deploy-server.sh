#!/usr/bin/env bash
# Invoked by deploy.ps1 over SSH as the deployment user.
set -euo pipefail
umask 077
mode=${1:?}
stage=${2:?}
domain=${3:?}
repo="$HOME/inteplast"
origin=https://github.com/opticsensors/inteplast.git
config="$HOME/.config/inteplast"
fail() { echo "$*" >&2; exit 1; }

cd "$HOME"
mkdir -p .config
if [[ $stage != - ]]; then
    [[ $stage =~ ^\.config/\.inteplast-setup-[0-9a-f]{32}$ ]] || fail 'Directorio temporal incorrecto.'
    cleanup() {
        if [[ -d $stage ]]; then
            rm -f -- "$stage/.env.production" "$stage/fullchain.pem" "$stage/privkey.pem"
            rmdir -- "$stage"
        fi
    }
    stage="$HOME/$stage"
    trap cleanup EXIT
fi
exec 9>".config/inteplast-deploy.lock"
flock -n 9 || fail 'Hay otro despliegue de INTEPLAST en curso.'

export GIT_TERMINAL_PROMPT=0
if [[ ! -e "$repo/.git" ]]; then
    # git clone creates the directory, accepts an empty one and refuses a
    # non-empty unrelated directory without overwriting its contents.
    git clone --branch main --single-branch "$origin" "$repo"
fi
cd "$repo"
[[ $(git rev-parse --show-toplevel) == "$(pwd -P)" ]] || fail 'El destino no es la raiz del repositorio.'
[[ $(git remote get-url origin) == "$origin" ]] || fail 'El repositorio existente tiene otro origin.'
[[ $(git branch --show-current) == main ]] || fail 'La copia del servidor no esta en main.'
changes=$(git status --porcelain)
[[ -z $changes ]] || fail 'Hay cambios locales en el servidor. Se han conservado.'
git fetch origin refs/heads/main:refs/remotes/origin/main
git merge-base --is-ancestor HEAD origin/main || fail 'El servidor tiene commits propios o un historial divergente.'
git merge --ff-only origin/main
revision=$(git rev-parse --short HEAD)
git log -1 --oneline
[[ $mode != prepare ]] || exit 0
[[ -f compose.server.yml ]] || fail 'Publica primero la configuracion de despliegue en main de GitHub.'

candidate=$config
if [[ $stage != - && ! -e $config ]]; then candidate=$stage; fi
for file in .env.production fullchain.pem privkey.pem; do
    [[ -s "$candidate/$file" ]] || fail "Falta $file. Usa deploy.ps1 -ConfigDirectory con los tres ficheros de produccion."
done
openssl verify -partial_chain -CAfile "$candidate/fullchain.pem" -verify_hostname "$domain" "$candidate/fullchain.pem"
cert_pub=$(openssl x509 -in "$candidate/fullchain.pem" -noout -pubkey)
key_pub=$(openssl pkey -in "$candidate/privkey.pem" -passin pass: -pubout)
[[ $cert_pub == "$key_pub" ]] || fail 'El certificado y la clave TLS no corresponden.'

docker=(docker)
if ! docker info >/dev/null 2>&1; then docker=(sudo docker); fi
compose=("${docker[@]}" compose --project-name inteplast -f compose.yml -f compose.server.yml)
# Verify effective settings before initializing PostgreSQL. Never print the
# expanded Compose model: it contains the credentials.
"${compose[@]}" --env-file "$candidate/.env.production" config --format json | python3 -c '
import json, sys
env = json.load(sys.stdin)["services"]["backend"]["environment"]
if env["DOMAIN"] != sys.argv[1]:
    sys.exit("DOMAIN debe coincidir con el nombre HTTPS del servidor.")
for key in ("FIRST_SUPERUSER", "SECRET_KEY", "POSTGRES_USER", "POSTGRES_DB", "POSTGRES_PASSWORD", "FIRST_SUPERUSER_PASSWORD"):
    if not env.get(key) or env[key] == "changethis":
        sys.exit("Configura un valor privado de produccion para " + key)
' "$domain"

if [[ $candidate != "$config" ]]; then
    chmod 600 "$candidate"/{.env.production,fullchain.pem,privkey.pem}
    mv -T -- "$candidate" "$config"
fi
compose+=(--env-file "$config/.env.production")
# Build first so a build failure leaves the running services in place.
"${compose[@]}" build backend frontend </dev/null
"${compose[@]}" pull --policy missing db proxy </dev/null
"${compose[@]}" up -d --no-build --pull never --wait --wait-timeout 300 db </dev/null

# Preserve the database before prestart upgrades an existing schema.
db_query() {
    "${compose[@]}" exec -T db sh -c 'exec psql -XAtq -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$1"' sh "$1" </dev/null
}
has_schema=$(db_query "SELECT to_regclass('public.alembic_version') IS NOT NULL")
if [[ $has_schema == t ]]; then
    current=$(db_query 'SELECT version_num FROM alembic_version ORDER BY 1')
    target=$("${compose[@]}" run --rm --no-deps -T backend alembic heads </dev/null | awk '{print $1}' | sort)
    [[ -n $target ]] || fail 'El paquete no contiene una revision Alembic.'
    if [[ $current != "$target" ]]; then
        backups="$HOME/.local/share/inteplast/backups"
        mkdir -p "$backups"
        dump=$(mktemp "$backups/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXXXX.partial")
        if ! "${compose[@]}" exec -T db sh -c 'exec pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' </dev/null > "$dump"; then
            rm -f "$dump"
            fail 'Fallo de pg_dump. Se ha detenido la actualizacion antes de migrar.'
        fi
        mv -- "$dump" "${dump%.partial}.dump"
        echo "Copia de PostgreSQL: ${dump%.partial}.dump"
    fi
fi
"${compose[@]}" up -d --no-build --pull never --wait --wait-timeout 300 db backend frontend proxy </dev/null
echo "Servicios preparados en $revision."
