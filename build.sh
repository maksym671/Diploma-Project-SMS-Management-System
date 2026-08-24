#!/usr/bin/env bash
# Build step for a PaaS deploy (Render). Run on every push.
set -o errexit

pip install -r requirements.txt

# Refresh the Polish catalogue when the build image ships gettext. The compiled
# django.mo is committed too, so a missing msgfmt must not fail the deploy.
# The ignores keep msgfmt out of the catalogues shipped inside installed packages.
python manage.py compilemessages -l pl -i .venv -i pptx_env -i staticfiles \
  || echo "compilemessages skipped; using the committed django.mo"

python manage.py collectstatic --no-input
python manage.py migrate

# Loads the demonstration data only into an empty database.
python manage.py seed_demo
