#!/usr/bin/env bash
set -euo pipefail

DEST_DIR="${HOME}/.config/systemd/user"
mkdir -p "${DEST_DIR}"

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../systemd" && pwd)"

echo "📦 Installing systemd user units from ${SRC_DIR} to ${DEST_DIR}..."
cp -v "${SRC_DIR}"/tamil-playlist-*.service "${DEST_DIR}/"
cp -v "${SRC_DIR}"/tamil-playlist-*.timer "${DEST_DIR}/"

echo "🔄 Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "⏰ Enabling and starting timers..."
systemctl --user enable --now tamil-playlist-sync.timer
systemctl --user enable --now tamil-playlist-full-sync.timer

echo "✅ Verifying active timers:"
systemctl --user list-timers --all | grep tamil-playlist || true

echo "🎉 Tamil Discography automated Spotify sync daemon successfully configured!"
