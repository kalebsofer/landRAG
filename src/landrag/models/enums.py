from enum import StrEnum


class ProjectType(StrEnum):
    ONSHORE_WIND = "onshore_wind"
    OFFSHORE_WIND = "offshore_wind"
    SOLAR = "solar"
    BATTERY_STORAGE = "battery_storage"
    GAS_PEAKER = "gas_peaker"
    TRANSMISSION = "transmission"
    HYDROGEN = "hydrogen"
    CCUS = "ccus"
    OTHER = "other"


class DocumentType(StrEnum):
    DECISION_LETTER = "decision_letter"
    EIA_CHAPTER = "eia_chapter"
    INSPECTOR_REPORT = "inspector_report"
    CONSULTATION_RESPONSE = "consultation_response"
    POLICY_STATEMENT = "policy_statement"
    GUIDANCE = "guidance"


class Topic(StrEnum):
    NOISE = "noise"
    ECOLOGY = "ecology"
    LANDSCAPE = "landscape"
    TRAFFIC = "traffic"
    CULTURAL_HERITAGE = "cultural_heritage"
    FLOOD_RISK = "flood_risk"
    AIR_QUALITY = "air_quality"
    SOCIOECONOMIC = "socioeconomic"
    GRID = "grid"
    CUMULATIVE_IMPACT = "cumulative_impact"
    DECOMMISSIONING = "decommissioning"
    CONSTRUCTION = "construction"


class SourcePortal(StrEnum):
    PINS = "pins"
    LPA = "lpa"
    EA = "ea"
    NE = "ne"
    GOV = "gov"


class DecisionOutcome(StrEnum):
    GRANTED = "granted"
    REFUSED = "refused"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
