#!/bin/sh

echo "Starting application setup..."
cd /app && alembic upgrade head
echo "Starting application..."
exec "$@"
