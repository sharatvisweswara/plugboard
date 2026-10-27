#!/bin/sh
# Start the ask-queue hub at login with a macOS LaunchAgent.
#
#   autostart.sh on       write the LaunchAgent and start it now
#   autostart.sh off      stop it and remove the LaunchAgent
#   autostart.sh status   show whether it is installed and running
#
# The LaunchAgent runs <state>/launch-hub.sh. That launcher finds the
# installed ask-queue plugin in installed_plugins.json at every start, so
# plugin updates need no new LaunchAgent. If the plugin is not installed
# (or its version has no --launchd mode), it uses the copy that ran
# `autostart.sh on`.

set -eu

script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
root=$(dirname -- "$script_dir")
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
state="$cfg/ask-queue"
label="plugboard.ask-queue"
plist="$HOME/Library/LaunchAgents/$label.plist"
launcher="$state/launch-hub.sh"
domain="gui/$(id -u)"
port="${ASKQ_PORT:-7788}"

[ "$(uname)" = Darwin ] || { echo "autostart: LaunchAgents are macOS only"; exit 1; }

write_launcher() {
  mkdir -p "$state"
  cat >"$launcher" <<EOF
#!/bin/sh
# Written by ask-queue scripts/autostart.sh; started by the $label LaunchAgent.
cfg="$cfg"
root=\$(python3 - "\$cfg/plugins/installed_plugins.json" <<'PY'
import json, sys
try:
    plugins = json.load(open(sys.argv[1])).get("plugins", {})
except (OSError, ValueError):
    plugins = {}
for name, installs in plugins.items():
    if name.startswith("ask-queue@"):
        for i in installs:
            if i.get("scope") == "user" and i.get("installPath"):
                print(i["installPath"])
                sys.exit(0)
PY
)
# Older installed versions have no --launchd mode; use the copy that ran "autostart.sh on".
grep -q -- "--launchd" "\$root/server/askqd.py" 2>/dev/null || root="$root"
exec python3 "\$root/server/askqd.py" --launchd
EOF
  chmod +x "$launcher"
}

write_plist() {
  mkdir -p "$(dirname -- "$plist")"
  config_env=""
  if [ -n "${CLAUDE_CONFIG_DIR:-}" ]; then
    config_env="<key>CLAUDE_CONFIG_DIR</key><string>$CLAUDE_CONFIG_DIR</string>"
  fi
  cat >"$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$label</string>
  <key>ProgramArguments</key>
  <array><string>/bin/sh</string><string>$launcher</string></array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>ASKQ_PORT</key><string>$port</string>
    $config_env
  </dict>
  <key>RunAtLoad</key><true/>
  <!-- Restart after a crash; exit 0 (another hub already serves the port) stays stopped. -->
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>$state/askqd.log</string>
  <key>StandardErrorPath</key><string>$state/askqd.log</string>
</dict>
</plist>
EOF
  plutil -lint "$plist" >/dev/null
}

loaded() { launchctl print "$domain/$label" >/dev/null 2>&1; }

case "${1:-status}" in
  on)
    write_launcher
    write_plist
    if loaded; then launchctl bootout "$domain/$label" 2>/dev/null || true; fi
    launchctl bootstrap "$domain" "$plist"
    echo "autostart on: $plist"
    if curl -sf --max-time 2 "http://127.0.0.1:$port/health" >/dev/null; then
      echo "note: a hub already runs on port $port, so the LaunchAgent exited for now; it starts the hub at the next login"
    fi
    ;;
  off)
    if loaded; then launchctl bootout "$domain/$label"; fi
    rm -f "$plist" "$launcher"
    echo "autostart off"
    ;;
  status)
    if [ -f "$plist" ]; then echo "LaunchAgent: $plist"; else echo "LaunchAgent: not installed"; fi
    if loaded; then
      launchctl print "$domain/$label" | grep -E '^\s*(state|pid|last exit code) =' | sed 's/^[[:space:]]*/  /'
    fi
    if curl -sf --max-time 2 "http://127.0.0.1:$port/health" >/dev/null; then echo "hub: running on port $port"; else echo "hub: not running"; fi
    ;;
  *)
    echo "usage: autostart.sh on|off|status"; exit 64 ;;
esac
