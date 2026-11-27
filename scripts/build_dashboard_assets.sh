#!/bin/sh
# Regenerate the assets served with the desktop dashboard and parent portal.
set -eu
cd "$(dirname "$0")/.."
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT
npm install --prefix "$build_dir" --ignore-scripts --no-fund --no-audit \
    tailwindcss@3.4.17 chart.js@4.5.1 lucide@0.468.0
vendor="$build_dir/node_modules"
mkdir -p web/vendor
cp "$vendor/chart.js/dist/chart.umd.min.js" web/vendor/chart-4.5.1.min.js
cp "$vendor/lucide/dist/umd/lucide.min.js" web/vendor/lucide-0.468.0.min.js
cp "$vendor/chart.js/LICENSE.md" web/vendor/chart.LICENSE
cp "$vendor/lucide/LICENSE" web/vendor/lucide.LICENSE
cp "$vendor/tailwindcss/LICENSE" web/vendor/tailwind.LICENSE
cat > "$build_dir/tailwind.config.cjs" <<'EOF'
module.exports = {
  content: ['./web/dashboard.html', './web/parent_portal.html'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace']
      },
      colors: {brand: {50: '#fff7ed', 500: '#f97316', 600: '#ea580c', 700: '#c2410c'}}
    }
  }
};
EOF
printf '%s\n' '@tailwind base;' '@tailwind components;' '@tailwind utilities;' > "$build_dir/input.css"
"$vendor/.bin/tailwindcss" -c "$build_dir/tailwind.config.cjs" -i "$build_dir/input.css" -o web/vendor/dashboard.css --minify
