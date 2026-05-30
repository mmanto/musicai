#!/bin/bash

# Script para ejecutar los tests del módulo Reasoning

echo "=========================================="
echo "MusicAI Reasoning - Test Runner"
echo "=========================================="
echo ""

# Verificar si el contenedor está corriendo
if ! docker ps | grep -q musicai-reasoning; then
    echo "❌ Error: El contenedor musicai-reasoning no está corriendo"
    echo "Ejecuta: docker compose up -d reasoning"
    exit 1
fi

echo "✓ Contenedor musicai-reasoning está corriendo"
echo ""

# Copiar tests al contenedor (en caso de cambios)
echo "📋 Copiando tests al contenedor..."
docker cp tests/test_basic_symbolic.py musicai-reasoning:/app/tests/ 2>/dev/null
docker cp tests/test_basic_hybrid.py musicai-reasoning:/app/tests/ 2>/dev/null
docker cp tests/test_basic_integration.py musicai-reasoning:/app/tests/ 2>/dev/null
docker cp tests/__init__.py musicai-reasoning:/app/tests/ 2>/dev/null
echo "✓ Tests copiados"
echo ""

# Ejecutar tests básicos
echo "🧪 Ejecutando tests básicos..."
echo "=========================================="
docker exec musicai-reasoning pytest tests/test_basic_*.py -v --tb=short

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "✅ Todos los tests pasaron exitosamente"
else
    echo "❌ Algunos tests fallaron"
fi
echo "=========================================="

exit $TEST_EXIT_CODE
