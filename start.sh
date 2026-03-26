#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="${ROOT_DIR}/ruoyi-fastapi-backend"
FRONTEND_DIR="${ROOT_DIR}/ruoyi-fastapi-frontend"
LOG_DIR="${ROOT_DIR}/logs"

BACKEND_ENV="${BACKEND_ENV:-dev}"
BACKEND_PORT="${BACKEND_PORT:-9100}"
BACKEND_PYTHON="${BACKEND_PYTHON:-python3}"
FRONTEND_PM="${FRONTEND_PM:-npm}"
FRONTEND_CMD="${FRONTEND_CMD:-run dev}"
BACKEND_READY_TIMEOUT="${BACKEND_READY_TIMEOUT:-30}"

mkdir -p "${LOG_DIR}"

BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"

backend_pid=""
frontend_pid=""

cleanup() {
  local exit_code=$?
  if [[ -n "${backend_pid}" ]] && kill -0 "${backend_pid}" 2>/dev/null; then
    kill "${backend_pid}" 2>/dev/null || true
  fi
  if [[ -n "${frontend_pid}" ]] && kill -0 "${frontend_pid}" 2>/dev/null; then
    kill "${frontend_pid}" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  exit "${exit_code}"
}

trap cleanup INT TERM EXIT

echo "项目根目录: ${ROOT_DIR}"
echo "后端目录: ${BACKEND_DIR}"
echo "前端目录: ${FRONTEND_DIR}"
echo "后端环境: ${BACKEND_ENV}"
echo "后端端口: ${BACKEND_PORT}"
echo "后端解释器: ${BACKEND_PYTHON}"
echo "前端包管理器: ${FRONTEND_PM}"
echo "日志目录: ${LOG_DIR}"
echo "后端就绪等待: ${BACKEND_READY_TIMEOUT}s"
echo

wait_for_backend() {
  local elapsed=0
  local backend_url="http://127.0.0.1:${BACKEND_PORT}/docs"

  while (( elapsed < BACKEND_READY_TIMEOUT )); do
    if ! kill -0 "${backend_pid}" 2>/dev/null; then
      echo "后端进程已退出，请查看日志: ${BACKEND_LOG}" >&2
      return 1
    fi

    if command -v curl >/dev/null 2>&1; then
      if curl -fsS "${backend_url}" >/dev/null 2>&1; then
        return 0
      fi
    else
      if (echo >"/dev/tcp/127.0.0.1/${BACKEND_PORT}") >/dev/null 2>&1; then
        return 0
      fi
    fi

    sleep 1
    elapsed=$((elapsed + 1))
  done

  echo "等待后端就绪超时，请查看日志: ${BACKEND_LOG}" >&2
  return 1
}

if [[ ! -d "${BACKEND_DIR}" ]]; then
  echo "未找到后端目录: ${BACKEND_DIR}" >&2
  exit 1
fi

if [[ ! -d "${FRONTEND_DIR}" ]]; then
  echo "未找到前端目录: ${FRONTEND_DIR}" >&2
  exit 1
fi

if ! command -v "${BACKEND_PYTHON}" >/dev/null 2>&1; then
  echo "找不到后端解释器: ${BACKEND_PYTHON}" >&2
  exit 1
fi

if ! command -v "${FRONTEND_PM}" >/dev/null 2>&1; then
  echo "找不到前端包管理器: ${FRONTEND_PM}" >&2
  exit 1
fi

echo "启动后端..."
(
  cd "${BACKEND_DIR}"
  APP_PORT="${BACKEND_PORT}" "${BACKEND_PYTHON}" app.py --env="${BACKEND_ENV}"
) >"${BACKEND_LOG}" 2>&1 &
backend_pid=$!
echo "后端 PID: ${backend_pid}"
echo "后端日志: ${BACKEND_LOG}"

if ! wait_for_backend; then
  exit 1
fi

echo "后端已就绪。"

echo "启动前端..."
(
  cd "${FRONTEND_DIR}"
  "${FRONTEND_PM}" ${FRONTEND_CMD}
) >"${FRONTEND_LOG}" 2>&1 &
frontend_pid=$!
echo "前端 PID: ${frontend_pid}"
echo "前端日志: ${FRONTEND_LOG}"

sleep 2

if ! kill -0 "${frontend_pid}" 2>/dev/null; then
  echo "前端启动失败，请查看日志: ${FRONTEND_LOG}" >&2
  exit 1
fi

echo
echo "前后端已启动。"
echo "前端默认访问: http://127.0.0.1:80"
echo "后端默认访问: http://127.0.0.1:${BACKEND_PORT}"
echo
echo "按 Ctrl+C 可同时停止前后端。"
echo "实时查看日志:"
echo "  tail -f ${BACKEND_LOG}"
echo "  tail -f ${FRONTEND_LOG}"
echo

wait "${backend_pid}" "${frontend_pid}"
