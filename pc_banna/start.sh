#!/bin/sh
set -eu

chmod +x /usr/local/bin/mounted.sh
/usr/local/bin/mounted.sh

# Keep container alive
tail -f /dev/null

