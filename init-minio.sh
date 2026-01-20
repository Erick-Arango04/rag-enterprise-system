#!/bin/bash
# init-minio.sh - Configura el bucket inicial en MinIO

echo "Esperando a que MinIO esté listo..."
sleep 10

echo "Configurando bucket 'documents'..."
docker-compose exec -T minio sh -c "
  mc alias set local http://localhost:9000 minioadmin minioadmin123
  mc mb local/documents --ignore-existing
  mc policy set download local/documents
  echo '✅ Bucket documents creado exitosamente!'
"