#!/bin/bash -eu
cat <<EOF > a.js
import * as a from "./b.js"
export function f(x) { return a.g(x) }
EOF
cat <<EOF > b.js
import {f} from "./a.js"
export {f}
export function g(x) { return x }
EOF
build/qjs b.js
