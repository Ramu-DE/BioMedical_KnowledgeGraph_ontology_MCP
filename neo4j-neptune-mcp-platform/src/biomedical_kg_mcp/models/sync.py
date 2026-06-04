"""Sync-related data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SyncDirection(str, Enum):
    """Sync direction."""
    TO_NEPTUNE = "to_neptune"
    FROM_NEPTUNE = "from_neptune"


class SyncStatus(str, Enum):
    """Sync job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATING = "validating"


class SyncJob(BaseModel):
    """Sync job tracking."""
    
    job_id: str = Field(..., description="Unique job identifier")
    direction: SyncDirection
    status: SyncStatus = SyncStatus.PENDING
    source_query: Optional[str] = None
    named_graph: Optional[str] = None
    entity_count: int = 0
    triple_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    validate: bool = True


class ConflictResolution(str, Enum):
    """Conflict resolution strategy."""
    LAST_WRITER_WINS = "last_writer_wins"
    MANUAL = "manual"
    SOURCE_PREFERRED = "source_preferred"


class ConflictRecord(BaseModel):
    """Record of sync conflict."""
    
    conflict_id: str
    entity_id: str
    entity_type: str
    neo4j_value: Dict[str, Any]
    neptune_value: Dict[str, Any]
    neo4j_timestamp: datetime
    neptune_timestamp: datetime
    resolution: ConflictResolution = ConflictResolution.LAST_WRITER_WINS
    resolved_value: Optional[Dict[str, Any]] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None


class StreamCheckpoint(BaseModel):
    """Neptune Streams checkpoint."""
    
    stream_name: str
    commit_num: int = Field(..., description="Last processed commit number")
    timestamp: datetime
    records_processed: int = 0
