#!/bin/sh
python -m hg_runtime.deployment.health || exit 1
