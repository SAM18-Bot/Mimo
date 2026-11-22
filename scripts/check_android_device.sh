#!/usr/bin/env bash
# Run the signed-in Compose journeys on a dedicated, running Android emulator.
set -euo pipefail
project_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_root"
qa_dir=$(mktemp -d)
server_pid=
cleanup() {
    if [[ -n "$server_pid" ]]; then kill "$server_pid" 2>/dev/null || true; fi
    adb -e reverse --remove tcp:18443 >/dev/null 2>&1 || true
    rm -rf -- "$qa_dir"
}
trap cleanup EXIT
umask 077
mkdir -p "$qa_dir/assets/res/xml" "$qa_dir/assets/res/raw"
openssl req -x509 -newkey rsa:2048 -nodes -days 2 -subj '/CN=Mimo device test CA' \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -keyout "$qa_dir/ca.key" -out "$qa_dir/assets/res/raw/mimo_device_ca.pem" 2>/dev/null
openssl req -new -newkey rsa:2048 -nodes -subj '/CN=localhost' \
    -keyout "$qa_dir/server.key" -out "$qa_dir/server.csr" 2>/dev/null
cat > "$qa_dir/server.ext" <<'EOF'
basicConstraints=CA:FALSE
extendedKeyUsage=serverAuth
subjectAltName=DNS:localhost
EOF
openssl x509 -req -days 2 -in "$qa_dir/server.csr" -CA "$qa_dir/assets/res/raw/mimo_device_ca.pem" \
    -CAkey "$qa_dir/ca.key" -CAcreateserial -extfile "$qa_dir/server.ext" -out "$qa_dir/server.crt" 2>/dev/null
cat > "$qa_dir/assets/AndroidManifest.xml" <<'EOF'
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application android:networkSecurityConfig="@xml/mimo_device_network" />
</manifest>
EOF
cat > "$qa_dir/assets/res/xml/mimo_device_network.xml" <<'EOF'
<network-security-config>
    <domain-config cleartextTrafficPermitted="false">
        <domain>localhost</domain>
        <trust-anchors><certificates src="@raw/mimo_device_ca" /></trust-anchors>
    </domain-config>
</network-security-config>
EOF
export MIMO_ENV=production NO_HARDWARE=1 NO_VOICE=1
export DATABASE_URL="sqlite:///$qa_dir/device.db"
JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(48))')
SECRET_KEY=$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
export JWT_SECRET_KEY SECRET_KEY
export GEMINI_API_KEY='' GOOGLE_CLIENT_ID=''
python -m uvicorn main:app --host 127.0.0.1 --port 18443 --ssl-keyfile "$qa_dir/server.key" \
    --ssl-certfile "$qa_dir/server.crt" > "$qa_dir/server.log" 2>&1 &
server_pid=$!
curl --fail --silent --show-error --retry 20 --retry-connrefused --retry-delay 1 \
    --cacert "$qa_dir/assets/res/raw/mimo_device_ca.pem" https://localhost:18443/health >/dev/null
adb -e reverse tcp:18443 tcp:18443
cd android
./gradlew "-PmimoDeviceTestAssets=$qa_dir/assets" connectedDeviceQaAndroidTest
