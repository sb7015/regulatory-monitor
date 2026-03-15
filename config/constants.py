from enum import Enum


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class State(str, Enum):
    TX = "TX"
    CA = "CA"
    BOTH = "BOTH"


class Source(str, Enum):
    FEDERAL_REGISTER = "federal_register"
    TDI = "tdi"
    CDI = "cdi"
    OFAC = "ofac"


class RegulationType(str, Enum):
    RULE = "Rule"
    PROPOSED_RULE = "Proposed Rule"
    NOTICE = "Notice"
    BULLETIN = "Bulletin"
    SANCTIONS = "Sanctions"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    CLASSIFIED = "classified"
    REJECTED = "rejected"
    IMPACT_MAPPED = "impact_mapped"
    MEMO_GENERATED = "memo_generated"


SOURCE_STATE_MAP = {
    Source.FEDERAL_REGISTER: None,
    Source.TDI: State.TX,
    Source.CDI: State.CA,
    Source.OFAC: State.BOTH,
}

FR_SEARCH_TERMS = [
    "life insurance",
    "annuity",
    "OFAC sanctions insurance",
    "nonforfeiture life",
    "insurance solvency",
    "variable life insurance",
    "universal life insurance",
    "group life insurance",
    "insurance reserve requirements",
    "NAIC life insurance",
    "accelerated death benefit",
    "insurance illustration regulation",
]

TDI_BULLETIN_YEARS = list(range(2021, 2027))
CDI_BULLETIN_YEARS = list(range(2021, 2027))

POLICY_FILES = [
    "P01_Access_Term_Life.txt",
    "P02_MyLife_Select_Term.txt",
    "P03_Securian_Life_Term.txt",
    "P04_Convertible_Term.txt",
    "P05_Indexed_Universal_Life.txt",
    "P06_Survivorship_IUL.txt",
    "P07_Variable_Universal_Life.txt",
    "P08_Whole_Life.txt",
    "P09_Universal_Life.txt",
    "P10_Group_Term_Life_ADD.txt",
    "P11_Group_Universal_Life.txt",
    "R01_ADB_Terminal_Illness.txt",
    "R02_ADB_Chronic_Illness.txt",
    "R03_Waiver_of_Premium.txt",
    "R04_Term_Insurance_Agreement.txt",
    "R05_Guaranteed_Insurability.txt",
    "R06_Overloan_Protection.txt",
    "R07_Early_Values_Agreement.txt",
]

CHROMA_COLLECTION = "securian_policies"
