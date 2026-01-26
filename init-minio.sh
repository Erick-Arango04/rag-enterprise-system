#!/bin/bash
# init-minio.sh - Configura el bucket inicial en MinIO

echo "Esperando a que MinIO esté listo..."
sleep 10

echo "Configurando bucket 'files'..."
docker-compose exec -T minio sh -c "
  mc alias set local http://localhost:9000 minioadmin minioadmin123
  mc mb local/files --ignore-existing
  mc policy set download local/files
  echo '✅ Bucket files creado exitosamente!'
"