#!/usr/bin/env bash
set -euo pipefail

cd /home/pablo/odoo
source .venv/bin/activate
export TZ=Europe/Madrid
exec ./odoo-bin -c debian/odoo.conf "$@"
