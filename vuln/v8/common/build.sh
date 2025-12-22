#!/bin/bash -eu

cat > .gclient <<'EOF'
solutions = [
  {
    "name": ".",
    "url": None,
    "deps_file": "DEPS",
    "managed": True,
    "custom_deps": {},
  },
]
EOF

flock /gclient.lock -c "gclient sync -D -j$(nproc)"

gn gen out/debug_asan --args='
    is_debug=true
    is_asan=true
    is_lsan=true
    v8_enable_backtrace=true
    is_component_build=false
    symbol_level=2
'

retry_count=0
max_retries=3

while [ $retry_count -lt $max_retries ]; do
    if ninja -C out/debug_asan -j8 d8; then
        echo "Ninja build successful on attempt $((retry_count + 1))"
        break
    else
        retry_count=$((retry_count + 1))
        if [ $retry_count -lt $max_retries ]; then
            echo "Ninja build failed on attempt $retry_count, retrying..."
            sleep 2
        else
            echo "Ninja build failed after $max_retries attempts"
            exit 1
        fi
    fi
done

test -f out/debug_asan/d8