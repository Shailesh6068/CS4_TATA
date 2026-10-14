import datetime
from datetime import UTC as _UTC

def _utcnow():
    """Returns a timezone-aware UTC datetime. Use as SQLAlchemy column default."""
    return datetime.datetime.now(_UTC)

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), default="ENGINEER")  # ADMIN, ENGINEER, REVIEWER, VIEWER
    created_at = Column(DateTime, default=_utcnow)
    
    audit_logs = relationship("AuditLog", back_populates="user")
    memberships = relationship("ProjectMember", back_populates="user")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), index=True, nullable=False)
    description = Column(Text, nullable=True)
    repo_path = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="project", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="project")

class ProjectMember(Base):
    __tablename__ = "project_members"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(50), default="ENGINEER")
    joined_at = Column(DateTime, default=_utcnow)
    
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="memberships")

class ProjectFile(Base):
    __tablename__ = "files"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    relative_path = Column(String(500), nullable=False)
    file_name = Column(String(255), nullable=False)
    extension = Column(String(50), nullable=False)
    size_bytes = Column(Integer, default=0)
    language = Column(String(50), default="unknown")
    line_count = Column(Integer, default=0)
    sha256_hash = Column(String(64), nullable=True)
    updated_at = Column(DateTime, default=_utcnow)
    
    project = relationship("Project", back_populates="files")
    symbols = relationship("FileSymbol", back_populates="file", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="file")

class FileSymbol(Base):
    __tablename__ = "file_symbols"
    
    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    symbol_name = Column(String(255), index=True, nullable=False)
    symbol_type = Column(String(50), nullable=False)  # FUNCTION, CLASS, VARIABLE, STRUCT, MACRO, INCLUDE
    line_start = Column(Integer, default=1)
    line_end = Column(Integer, default=1)
    signature = Column(Text, nullable=True)
    
    file = relationship("ProjectFile", back_populates="symbols")

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    review_type = Column(String(50), nullable=False)  # GENERAL, SECURITY, MISRA, DEBUG, DIFF, LOG
    status = Column(String(50), default="COMPLETED")  # PENDING, RUNNING, COMPLETED, FAILED
    summary = Column(Text, nullable=True)
    overall_risk = Column(String(50), default="LOW")  # CRITICAL, HIGH, MEDIUM, LOW
    score = Column(Float, default=100.0)
    security_score = Column(Float, default=100.0)
    correctness_score = Column(Float, default=100.0)
    maintainability_score = Column(Float, default=100.0)
    created_at = Column(DateTime, default=_utcnow)
    
    project = relationship("Project", back_populates="reviews")
    findings = relationship("Finding", back_populates="review", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="review", cascade="all, delete-orphan")

class Finding(Base):
    __tablename__ = "findings"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    finding_code = Column(String(50), index=True, nullable=False)  # e.g., SEC-001, MISRA-11.4
    category = Column(String(100), nullable=False)  # Security, MISRA, Bug, Performance, Style
    severity = Column(String(50), default="MEDIUM")  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence = Column(String(50), default="HIGH")  # HIGH, MEDIUM, LOW
    source_type = Column(String(50), default="LLM")  # STATIC_ANALYZER, COMPILER, SECURITY_RULE, RAG, LLM, COMBINED
    file_path = Column(String(500), nullable=False)
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    issue = Column(String(500), nullable=False)
    evidence = Column(Text, nullable=True)
    explanation = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=True)
    suggested_fix = Column(Text, nullable=True)
    status = Column(String(50), default="OPEN")  # OPEN, CONFIRMED, FALSE_POSITIVE, IN_PROGRESS, FIXED, VERIFIED, REJECTED
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    
    project = relationship("Project", back_populates="findings")
    review = relationship("Review", back_populates="findings")
    file = relationship("ProjectFile", back_populates="findings")
    comments = relationship("FindingComment", back_populates="finding", cascade="all, delete-orphan")

class FindingComment(Base):
    __tablename__ = "finding_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    finding_id = Column(Integer, ForeignKey("findings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=_utcnow)
    
    finding = relationship("Finding", back_populates="comments")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    title = Column(String(255), nullable=False)
    version = Column(String(50), default="1.0")
    document_type = Column(String(50), default="GUIDELINE")  # GUIDELINE, STANDARD, ARCHITECTURE, SPEC
    file_path = Column(String(500), nullable=False)
    is_enabled = Column(Boolean, default=True)
    is_approved = Column(Boolean, default=True)
    owner = Column(String(100), default="Automotive Lead")
    created_at = Column(DateTime, default=_utcnow)
    
    project = relationship("Project", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, default=0)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    embedding_id = Column(String(100), nullable=True)
    
    document = relationship("Document", back_populates="chunks")

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"), nullable=False)
    analyzer_name = Column(String(100), nullable=False)  # Bandit, PythonAST, ClangMISRA, RegexSec
    execution_status = Column(String(50), default="SUCCESS")
    raw_output = Column(Text, nullable=True)
    metrics_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    
    review = relationship("Review", back_populates="analysis_results")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    action = Column(String(100), nullable=False)  # REVIEW_STARTED, FINDING_UPDATED, FILE_UPLOADED, RAG_QUERY
    target_type = Column(String(100), nullable=True)
    target_id = Column(String(100), nullable=True)
    details_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=_utcnow)
    
    user = relationship("User", back_populates="audit_logs")
    project = relationship("Project", back_populates="audit_logs")

class ReviewRule(Base):
    __tablename__ = "review_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(100), unique=True, index=True, nullable=False)
    standard = Column(String(100), default="MISRA_C_2012")  # MISRA_C_2012, CERT_C, CWE, AUTOSAR
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(50), default="HIGH")
    is_enabled = Column(Boolean, default=True)
    custom_parameters = Column(Text, nullable=True)

class ReviewRun(Base):
    __tablename__ = "review_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    trigger_type = Column(String(50), default="MANUAL")  # MANUAL, CI_CD, GIT_COMMIT
    started_at = Column(DateTime, default=_utcnow)
    completed_at = Column(DateTime, nullable=True)
    total_files = Column(Integer, default=0)
    total_findings = Column(Integer, default=0)
