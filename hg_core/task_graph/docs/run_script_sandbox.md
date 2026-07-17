# run_script sandbox (plan s3)

For **run_script** tool nodes: time limit, filesystem allowlist, network allowlist, max output bytes. Document in DAG spec; enforce in dispatcher when run_script is invoked. Implementation: pass allowlists and limits to the script runner (e.g. subprocess with timeout, chroot or path allowlist, network block by default).
