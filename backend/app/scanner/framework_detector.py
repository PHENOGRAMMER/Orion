"""
Framework detector.

Detects frameworks, package managers, build systems,
containerization tools and CI/CD providers.

Supported:

Python
    - requirements.txt
    - pyproject.toml

JavaScript / TypeScript
    - package.json

Infrastructure
    - Dockerfile
    - docker-compose.yml
    - compose.yml

CI/CD
    - GitHub Actions
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

from app.scanner.index import ProjectIndex
from app.scanner.models import ProjectScanResult


class FrameworkDetector:

    PYTHON_PACKAGES = {
        "fastapi": "FastAPI",
        "flask": "Flask",
        "django": "Django",
        "streamlit": "Streamlit",
        "langchain": "LangChain",
        "llama-index": "LlamaIndex",
        "pydantic": "Pydantic",
        "sqlalchemy": "SQLAlchemy",
        "pytest": "PyTest",
        "numpy": "NumPy",
        "pandas": "Pandas",
        "torch": "PyTorch",
        "tensorflow": "TensorFlow",
    }

    JS_PACKAGES = {
        "react": "React",
        "next": "Next.js",
        "express": "Express",
        "vue": "Vue",
        "@angular/core": "Angular",
        "vite": "Vite",
        "tailwindcss": "Tailwind CSS",
        "electron": "Electron",
        "@nestjs/core": "NestJS",
        "svelte": "Svelte",
        "nuxt": "Nuxt",
    }

    def analyze(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ) -> ProjectScanResult:

        self._detect_requirements(result, index)

        self._detect_pyproject(result, index)

        self._detect_package_json(result, index)

        self._detect_docker(result, index)

        self._detect_github_actions(result, index)

        return result

    # --------------------------------------------------------
    # requirements.txt
    # --------------------------------------------------------

    def _detect_requirements(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ):

        files = index.config_files.get("requirements.txt")

        if not files:
            return

        result.framework_statistics.package_managers = "pip"

        for file in files:

            path = Path(result.root_path) / file.path

            if not path.exists():
                continue

            for line in self._read_text_files(path):

                package = line.strip().lower()

                if not package or package.startswith("#"):
                    continue

                package = package.split("==")[0]
                package = package.split(">=")[0]
                package = package.split("<=")[0]

                framework = self.PYTHON_PACKAGES.get(package)

                if framework:

                    result.framework_statistics.frameworks[
                        framework
                    ] = True

    # --------------------------------------------------------
    # pyproject.toml
    # --------------------------------------------------------

    def _detect_pyproject(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ):

        files = index.config_files.get("pyproject.toml")

        if not files:
            return

        for file in files:

            path = Path(result.root_path) / file.path

            if not path.exists():
                continue

            with open(path, "rb") as f:

                data = tomllib.load(f)

            if "tool" in data:

                tool = data["tool"]

                if "poetry" in tool:

                    result.framework_statistics.package_managers = "Poetry"

                if "ruff" in tool:

                    result.framework_statistics.frameworks[
                        "Ruff"
                    ] = True

                if "black" in tool:

                    result.framework_statistics.frameworks[
                        "Black"
                    ] = True

                if "mypy" in tool:

                    result.framework_statistics.frameworks[
                        "MyPy"
                    ] = True

    # --------------------------------------------------------
    # package.json
    # --------------------------------------------------------

    def _detect_package_json(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ):

        files = index.config_files.get("package.json")

        if not files:
            return

        result.framework_statistics.package_managers = "npm"

        for file in files:

            path = Path(result.root_path) / file.path

            if not path.exists():
                continue

            with open(path, encoding="utf-8") as f:

                data = json.load(f)

            dependencies = {}

            dependencies.update(
                data.get("dependencies", {})
            )

            dependencies.update(
                data.get("devDependencies", {})
            )

            for package in dependencies:

                framework = self.JS_PACKAGES.get(package)

                if framework:

                    result.framework_statistics.frameworks[
                        framework
                    ] = True

            if "packageManager" in data:

                pm = data["packageManager"].lower()

                if "pnpm" in pm:

                    result.framework_statistics.package_managers = "pnpm"

                elif "yarn" in pm:

                    result.framework_statistics.package_managers = "yarn"

                else:

                    result.framework_statistics.package_managers = "npm"

            if "vite" in dependencies:

                result.framework_statistics.build_systems = "Vite"

            elif "next" in dependencies:

                result.framework_statistics.build_systems = "Next.js"

    # --------------------------------------------------------
    # Docker
    # --------------------------------------------------------

    def _detect_docker(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ):

        if "Dockerfile" in index.config_files:

            result.framework_statistics.containerization.append(
                "Docker"
            )

        if (
            "docker-compose.yml" in index.config_files
            or
            "compose.yml" in index.config_files
        ):

            result.framework_statistics.containerization.append(
                "Docker Compose"
            )

    # --------------------------------------------------------
    # GitHub Actions
    # --------------------------------------------------------

    def _detect_github_actions(
        self,
        result: ProjectScanResult,
        index: ProjectIndex,
    ):

        for directory in index.directories:

            if directory.startswith(".github"):

                result.framework_statistics.ci_cd.append(
                    "GitHub Actions"
                )

                break

    def _read_text_files(self, path: Path) -> list[str]:
        """
        Read a text file using several common encodings.
        """
        encodings = (
            "utf-8",
            "utf-8-sig",
            "utf-16",
            "latin-1",
        )

        for encoding in encodings:
            try:
                with open(path, "r", encoding=encoding) as f:
                    return f.readlines()
            except UnicodeDecodeError:
                continue
            except OSError:
                return []

        return []