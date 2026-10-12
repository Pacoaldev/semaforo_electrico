#!/usr/bin/env bash
# Script de build para plataformas de despliegue (Render, Railway, etc.)
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput
