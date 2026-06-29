from pydantic import BaseModel, Field
from datetime import datetime, timezone
from pathlib import Path

class FileInfo(BaseModel):
    path: str
    extension: str
    size: int
    modified_time: datetime
    created_time: datetime

class ProjectStatistics(BaseModel):
    """
    Aggregated statistics collected while scanning.
    """

    total_files: int = 0

    total_directories: int = 0

    total_size: int = 0

    average_file_size: float = 0

    hidden_files: int = 0

    max_depth: int = 0

    extensions: dict[str, int] = Field(default_factory=dict)

class FrameworkStatistics(BaseModel):
    """
    Framework statistics detected in the project.
    """
    frameworks: dict[str, bool] = Field(default_factory=dict)

    package_managers: str | None = None

    build_systems: str | None = None

    containerization: list[str] = Field(default_factory=list)

    ci_cd: list[str] = Field(default_factory=list)


class DirectoryScanResult(BaseModel):
    """
    Internal recursive scan result.
    """

    statistics: ProjectStatistics = Field(
        default_factory=ProjectStatistics
    )

    files: list[FileInfo] = Field(default_factory=list)


class LanguageStatistics(BaseModel):
    """
    Language statistics detected in the project.
    """

    languages: dict[str, int] = Field(default_factory=dict)


class GitStatistics(BaseModel):
    """
    Git repository information.
    """

    is_git_repository: bool = False

    repository_root: str | None = None

    current_branch: str | None = None

    default_branch: str | None = None

    remotes: list[str] = Field(default_factory=list)

    last_commit_hash: str | None = None

    last_commit_author: str | None = None

    last_commit_email: str | None = None

    last_commit_date: datetime | None = None

    total_commits: int = 0

    dirty: bool = False

    untracked_files: list[str] = Field(default_factory=list)

    tags: list[str] = Field(default_factory=list)


class DependencyModel(BaseModel):
    file: str
    imports: list[str] = Field(default_factory=list)

class DependencyGraph(BaseModel):
    nodes: dict[str, DependencyModel] = Field(default_factory=dict)


class MethodSymbol(BaseModel):

    name: str
    line: int
    end_line: int
    async_method: bool = False
    decorators: list[str] = Field(default_factory=list)
    docstring: str | None = None


class FunctionSymbol(BaseModel):

    name: str
    line: int
    end_line: int
    decorators: list[str] = Field(default_factory=list)
    async_function: bool = False
    docstring: str | None = None


class ClassSymbol(BaseModel):

    name: str
    line: int
    end_line: int
    decorators: list[str] = Field(default_factory=list)
    base_classes: list[str] = Field(default_factory=list)
    docstring: str | None = None
    methods: list[MethodSymbol] = Field(default_factory=list)


class VariableSymbol(BaseModel):

    name: str
    line: int

class ImportSymbol(BaseModel):
    """
    Represents a single import statement.
    """
    module: str

    name: str | None = None
    alias: str | None = None
    relative_level: int = 0

    resolved_file: str | None = None
    resolved_symbol: str | None = None
    resolved_symbol_type: str | None = None


class FileSymbols(BaseModel):

    path: str = ""
    language: str = "Python"
    imports: list[ImportSymbol] = Field(default_factory=list)
    classes: list[ClassSymbol] = Field(default_factory=list)
    functions: list[FunctionSymbol] = Field(default_factory=list)
    variables: list[VariableSymbol] = Field(default_factory=list)

class SymbolGraph(BaseModel):
    files: dict[str, FileSymbols] = Field(default_factory=dict)



class ProjectScanResult(BaseModel):

    project_id: str

    project_name: str

    root_path: str

    statistics: ProjectStatistics

    language_statistics: LanguageStatistics = Field(
        default_factory=LanguageStatistics
    )
    
    framework_statistics: FrameworkStatistics = Field(
        default_factory=FrameworkStatistics
    )

    git_statistics: GitStatistics = Field(
        default_factory=GitStatistics
    )

    dependency_graph: DependencyGraph = Field(
    default_factory=DependencyGraph
    )

    symbol_graph: SymbolGraph = Field(
    default_factory=SymbolGraph
    )

    files: list[FileInfo] = Field(default_factory=list)
