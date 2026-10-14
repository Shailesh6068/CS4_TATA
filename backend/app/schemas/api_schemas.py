import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

# User & Project
class UserBase(BaseModel):
    username: str
    email: str
    role: str = "ENGINEER"

class UserResponse(UserBase):
    id: int
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    repo_path: Optional[str] = None
    is_active: bool = True
    created_at: datetime.datetime
    file_count: int = 0
    finding_count: int = 0
    model_config = ConfigDict(from_attributes=True)

# Files & Symbols
class FileSymbolResponse(BaseModel):
    id: int
    symbol_name: str
    symbol_type: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class FileResponse(BaseModel):
    id: int
    project_id: int
    relative_path: str
    file_name: str
    extension: str
    size_bytes: int
    language: str
    line_count: int
    symbols: List[FileSymbolResponse] = []
    model_config = ConfigDict(from_attributes=True)

# Findings
class FindingItem(BaseModel):
    id: Optional[str] = "FIND-001"
    finding_code: str
    category: str
    severity: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW
    source_type: str = "LLM"
    file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    issue: str
    evidence: Optional[str] = None
    explanation: str
    recommendation: Optional[str] = None
    suggested_fix: Optional[str] = None

class FindingResponse(BaseModel):
    id: int
    review_id: Optional[int] = None
    project_id: int
    file_id: Optional[int] = None
    finding_code: str
    category: str
    severity: str
    confidence: str
    source_type: str
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    issue: str
    evidence: Optional[str] = None
    explanation: str
    recommendation: Optional[str] = None
    suggested_fix: Optional[str] = None
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class FindingUpdate(BaseModel):
    status: Optional[str] = None  # OPEN, CONFIRMED, FALSE_POSITIVE, IN_PROGRESS, FIXED, VERIFIED, REJECTED
    comment: Optional[str] = None

class FindingVerificationRequest(BaseModel):
    finding_id: Optional[int] = None  # Optional: provided via URL path; included for completeness
    updated_code: str

class FindingVerificationResponse(BaseModel):
    finding_id: int
    previous_status: str
    new_status: str
    verification_passed: bool
    explanation: str
    rechecked_evidence: Optional[str] = None

# Structured AI Output Models
class StructuredReviewOutput(BaseModel):
    summary: str
    overall_risk: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW
    security_score: float = 85.0
    correctness_score: float = 80.0
    maintainability_score: float = 85.0
    findings: List[FindingItem] = []

# Reviews
class CodeReviewRequest(BaseModel):
    project_id: int
    file_paths: Optional[List[str]] = None
    code_snippet: Optional[str] = None
    file_name: Optional[str] = "snippet.cpp"
    use_rag: bool = True

class SecurityReviewRequest(BaseModel):
    project_id: int
    file_paths: Optional[List[str]] = None
    code_snippet: Optional[str] = None
    file_name: Optional[str] = "snippet.cpp"
    use_rag: bool = True

class MisraReviewRequest(BaseModel):
    project_id: int
    file_paths: Optional[List[str]] = None
    code_snippet: Optional[str] = None
    file_name: Optional[str] = "ecu_core.cpp"
    enabled_rules: Optional[List[str]] = None

class ReviewResponse(BaseModel):
    review_id: int
    project_id: int
    review_type: str
    status: str
    summary: str
    overall_risk: str
    score: float
    security_score: float
    correctness_score: float
    maintainability_score: float
    disclaimer: Optional[str] = None
    findings: List[FindingResponse] = []

# Code Explanation
class CodeExplanationRequest(BaseModel):
    project_id: int
    file_path: Optional[str] = None
    code_snippet: Optional[str] = None
    mode: str = "TECHNICAL"  # SIMPLE, TECHNICAL
    target_symbol: Optional[str] = None

class CodeExplanationResponse(BaseModel):
    executive_summary: str
    purpose: str
    functions_and_classes: List[Dict[str, Any]] = []
    inputs_and_outputs: Dict[str, Any] = {}
    control_flow: str
    dependencies: List[str] = []
    potential_risks: List[str] = []
    formatted_explanation: str

# Debugging & Error Analysis
class DebugAnalyzeRequest(BaseModel):
    project_id: int
    source_code: Optional[str] = None
    file_path: Optional[str] = None
    compiler_error: Optional[str] = None
    runtime_error: Optional[str] = None
    stack_trace: Optional[str] = None
    log_content: Optional[str] = None
    user_description: Optional[str] = None

class DebugAnalyzeResponse(BaseModel):
    error_summary: str
    severity: str
    likely_root_cause: str
    evidence: str
    affected_file: Optional[str] = None
    affected_line: Optional[int] = None
    explanation: str
    suggested_fix: str
    corrected_code: Optional[str] = None
    confidence: str
    limitations: str

# Logs Analysis
class LogAnalysisRequest(BaseModel):
    project_id: int
    log_content: str
    log_type: str = "ECU"  # ECU, RUNTIME, BUILD, CRASH

class LogAnalysisResponse(BaseModel):
    timeline: List[Dict[str, Any]] = []
    error_summary: str
    repeated_errors: List[Dict[str, Any]] = []
    possible_root_cause: str
    related_source_code: Optional[str] = None
    recommendations: List[str] = []

# Diff & Change Review
class DiffReviewRequest(BaseModel):
    project_id: int
    before_code: Optional[str] = None
    after_code: Optional[str] = None
    git_diff: Optional[str] = None
    file_name: Optional[str] = "diff.patch"

class DiffReviewResponse(BaseModel):
    introduces_security_vulnerability: str  # YES, NO, UNCERTAIN
    confidence: str
    added_risks: List[str] = []
    resolved_issues: List[str] = []
    regression_risks: List[str] = []
    detailed_analysis: str
    findings: List[FindingItem] = []

# Semantic & Symbol Search
class SemanticSearchRequest(BaseModel):
    project_id: int
    query: str
    top_k: int = 5

class SemanticSearchResultItem(BaseModel):
    file_path: str
    function_or_symbol: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    relevant_code: str
    explanation: str
    similarity_score: float

class SemanticSearchResponse(BaseModel):
    query: str
    results: List[SemanticSearchResultItem]

class SymbolSearchRequest(BaseModel):
    project_id: int
    symbol_name: str
    symbol_type: Optional[str] = None

# Knowledge & RAG
class DocumentResponse(BaseModel):
    id: int
    project_id: Optional[int] = None
    title: str
    version: str
    document_type: str
    file_path: str
    is_enabled: bool
    is_approved: bool
    owner: str
    chunk_count: int = 0
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class KnowledgeCitationItem(BaseModel):
    title: str
    section: str = "Standard"
    doc_type: str = "GUIDELINE"
    content: str
    similarity: float = 0.0

class KnowledgeQueryRequest(BaseModel):
    query: str
    project_id: Optional[int] = None
    top_k: int = 4

class KnowledgeQueryResponse(BaseModel):
    query: str
    citations: List[KnowledgeCitationItem]

# Ollama Management
class OllamaStatusResponse(BaseModel):
    is_connected: bool
    base_url: str
    active_model: str
    available_models: List[str] = []
    gpu_accelerated: bool = False
    message: str

class OllamaChangeModelRequest(BaseModel):
    model_name: str

# Code Complexity & Quality Score
class ComplexityMetric(BaseModel):
    symbol_name: str
    symbol_type: str
    cyclomatic_complexity: int
    line_count: int
    nested_depth: int
    parameter_count: int
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    recommendation: str

class ProjectQualityScoreResponse(BaseModel):
    overall_score: float
    security_score: float
    correctness_score: float
    maintainability_score: float
    performance_score: float
    readability_score: float
    risk_breakdown: Dict[str, str]
    explanation: str

# Audit Log
class AuditLogResponse(BaseModel):
    id: int
    user: Optional[str] = "engineer"
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)
