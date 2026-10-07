"""Provider-independent repository verification implemented with Dagger.

No GitHub Actions workflows exist in this repo yet; when any are added they
remain authoritative until parity is demonstrated and a maintainer explicitly
cuts over. Woodpecker decides *when* verification runs. This module defines a
portable, repository-owned baseline for *what* verification means during
shadow mode.
"""

from __future__ import annotations

from typing import Annotated

import dagger
from dagger import DefaultPath, dag, function, object_type

PYTHON_IMAGE = "python:3.12-slim"
NODE_IMAGE = "node:20-bookworm-slim"
GITLEAKS_IMAGE = (
    "ghcr.io/gitleaks/gitleaks:v8.28.0@sha256:"
    "cdbb7c955abce02001a9f6c9f602fb195b7fadc1e812065883f695d1eeaba854"
)
SOURCE = Annotated[dagger.Directory, DefaultPath("/")]


@object_type
class RepoCi:
    """Portable verification baseline shared across repositories."""

    def _container(
        self, image: str, source: dagger.Directory, workdir: str = "/src"
    ) -> dagger.Container:
        return (
            dag.container()
            .from_(image)
            .with_directory("/src", source)
            .with_workdir(workdir)
        )

    @function
    async def node(self, source: SOURCE) -> str:
        """Verify root or conventional Node workspaces when present."""
        script = r"""
set -eu

found=0
for d in . web frontend ui app; do
  [ -f "$d/package.json" ] || continue
  found=1
  echo "== Node verification: $d =="
  cd "/src/${d#./}"

  if [ -f pnpm-lock.yaml ]; then
    corepack enable
    pnpm install --frozen-lockfile
    manager=pnpm
  elif [ -f yarn.lock ]; then
    corepack enable
    (yarn install --immutable || yarn install --frozen-lockfile)
    manager=yarn
  elif [ -f package-lock.json ] || [ -f npm-shrinkwrap.json ]; then
    npm ci
    manager=npm
  else
    npm install
    manager=npm
  fi

  has_script() {
    node -e "const p=require('./package.json'); process.exit(p.scripts && p.scripts[process.argv[1]] ? 0 : 1)" "$1"
  }

  for name in lint test build; do
    if has_script "$name"; then
      echo "running $manager $name"
      if [ "$name" = test ]; then
        CI=true "$manager" run "$name"
      else
        "$manager" run "$name"
      fi
    fi
  done

  if [ "$manager" = npm ] && { [ -f package-lock.json ] || [ -f npm-shrinkwrap.json ]; }; then
    npm audit --omit=dev --audit-level=high
  fi
done

if [ "$found" -eq 0 ]; then
  echo "node: skipped (no package.json in root/web/frontend/ui/app)"
fi
"""
        await self._container(NODE_IMAGE, source).with_exec(
            ["sh", "-lc", script]
        ).stdout()
        return "node: passed or not applicable"

    @function
    async def python(self, source: SOURCE) -> str:
        """Verify Python projects when a root project manifest is present."""
        script = r"""
set -eu

if [ ! -f pyproject.toml ] && [ ! -f setup.py ] && [ ! -f setup.cfg ] && [ ! -f requirements.txt ]; then
  echo "python: skipped (no root Python project manifest)"
  exit 0
fi

python -m pip install --upgrade pip

if [ -f pyproject.toml ] || [ -f setup.py ] || [ -f setup.cfg ]; then
  python -m pip install -e ".[dev]" || python -m pip install -e .
elif [ -f requirements.txt ]; then
  python -m pip install -r requirements.txt
fi

# Fail closed: the suite must actually execute. Earlier revisions silently
# skipped pytest when it was absent (pip accepts unknown extras with only a
# warning), reporting a green pipeline that verified nothing.
if [ -d tests ]; then
  command -v pytest >/dev/null 2>&1 || { echo "pytest is required but not installed"; exit 1; }
fi

python -m pip install "pip-audit==2.7.3"
python -m pip_audit --strict --local

# Advisory until the repo adopts a ruff baseline: reported, never gating.
# (A bare `ruff check .` currently fails on pre-existing findings.)
if command -v ruff >/dev/null 2>&1; then
  ruff check . || echo "ruff: advisory findings reported above (non-gating)"
fi

if [ -d tests ]; then
  pytest -q
fi
"""
        await self._container(PYTHON_IMAGE, source).with_exec(
            ["sh", "-lc", script]
        ).stdout()
        return "python: passed or not applicable"

    @function
    async def production_image(self, source: SOURCE) -> str:
        """Build a root Dockerfile for linux/amd64 when the repository has one."""
        entries = await source.entries()
        if "Dockerfile" not in entries:
            return "production-image: skipped (no root Dockerfile)"
        image = source.docker_build(platform=dagger.Platform("linux/amd64"))
        await image.with_exec(["sh", "-lc", "true"]).stdout()
        return "production-image: passed"

    @function
    async def secrets(self, source: SOURCE) -> str:
        """Scan full Git history for secrets with the same pinned Gitleaks as CAPSF."""
        ctr = (
            dag.container()
            .from_(GITLEAKS_IMAGE)
            .with_directory("/src", source)
            .with_workdir("/src")
            .with_exec(
                [
                    "sh",
                    "-lc",
                    "test -d .git || { echo '.git history is required'; exit 42; }",
                ]
            )
            .with_exec(["gitleaks", "detect", "--redact", "-v", "--source", "."])
        )
        await ctr.stdout()
        return "secrets: passed"

    @function
    async def verify(self, source: SOURCE) -> str:
        """Run the portable shadow-CI baseline."""
        results = [
            await self.node(source),
            await self.python(source),
            await self.production_image(source),
            await self.secrets(source),
        ]
        return "\n".join(results)
