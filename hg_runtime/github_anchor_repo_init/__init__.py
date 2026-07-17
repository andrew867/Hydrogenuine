"""GitHub witness anchor repo operator initialization."""

from hg_runtime.github_anchor_repo_init.deploy_key import DeployKeyResult, generate_deploy_key
from hg_runtime.github_anchor_repo_init.repo_init import RepoInitResult, init_witness_repo
from hg_runtime.github_anchor_repo_init.signing_key import SigningKeyInitResult, generate_signing_key
from hg_runtime.github_anchor_repo_init.ssh_doctor import SSHDoctorResult, run_ssh_doctor

__all__ = [
    "DeployKeyResult",
    "RepoInitResult",
    "SSHDoctorResult",
    "SigningKeyInitResult",
    "generate_deploy_key",
    "generate_signing_key",
    "init_witness_repo",
    "run_ssh_doctor",
]
