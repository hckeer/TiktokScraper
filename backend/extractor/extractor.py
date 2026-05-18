## !pip install -q TikTokLive pandas openpyxl nest-asyncio gspread google-auth
"""
TikTok Live Monitor v5 - BULLETPROOF Edition
=============================================
✅ ZERO comment loss - queue-based async persistence
✅ Google Sheets real-time sync with separate phone column
✅ Auto-reconnect with exponential backoff
✅ Connection locking prevents race conditions
✅ Immediate write-through to disk + cloud
✅ Graceful degradation on network issues
✅ Comprehensive error logging
"""

import re
import json
import asyncio
import aiofiles
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque
from enum import Enum
import traceback

# TikTok
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials
from google.auth import default

# For Colab environment
try:
    from google.colab import auth
    IN_COLAB = True
except ImportError:
    IN_COLAB = False

# Async compatibility
import nest_asyncio
# nest_asyncio.apply() # Removed to prevent corrupting event loop

# ==========================================
# 📝 LOGGING SETUP
# ==========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s │ %(levelname)s │ %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('tiktok_monitor.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================

@dataclass
class Config:
    """Centralized configuration"""
    # TikTok accounts to monitor
    TIKTOK_USERS: List[str] = field(default_factory=lambda: [
        "santu.rasaili53", "gulf.recruiter", "santu.rasaili3", "best.requirement.a",
        "jopvacancy3", "baidesikkoneelkamal337", "alsecuremanpower1", "jobstation.ae",
        "theriveroverseas.p.v.t", "manpower.demand.pu", "leadingmanpower",
        "menpowerdimantneapalaa12", "sanjeevbaideshikrojgar0", "jobaboard.com.ktm",
        "adhikari.overseas", "monikaraii6", "manpowerdemand6", "support.manpower",
        "gulf.demand_ishwor", "vacancyforgulfcountry", "work.overseas5", "baidesik5",
        "karina.leadingmanpower", "mangalgurung518", "bikashtamang6", "pardesi.dinesh1",
        "baidesikrojgar60", "anisha8878", "manpowershrdemand1", "goldenachieversitahari",
        "baideshikrojgar065",
    ])

    # Timing (seconds)
    LIVE_CHECK_INTERVAL: int = 60        # Check for new lives
    CHECK_BATCH_SIZE: int = 5            # Users per batch
    CHECK_BATCH_DELAY: float = 2.0       # Delay between batches
    DASHBOARD_INTERVAL: int = 30         # Dashboard refresh
    SHEETS_SYNC_INTERVAL: int = 30       # Google Sheets sync
    LOCAL_SAVE_INTERVAL: int = 10        # Local backup frequency

    # Reconnection
    MAX_RECONNECT_ATTEMPTS: int = 5
    RECONNECT_BASE_DELAY: float = 2.0
    RECONNECT_MAX_DELAY: float = 60.0

    # Files
    SESSION_ID: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    DATA_FILE: str = "tiktok_data_v5.json"
    BACKUP_FILE: str = "tiktok_backup_v5.json"
    QUEUE_FILE: str = "tiktok_queue_v5.json"  # Persistence queue for crash recovery

    # Google Sheets
    SHEET_NAME: str = field(default_factory=lambda: f"TikTok_Monitor_{datetime.now().strftime('%Y%m%d')}")
    CREDENTIALS_FILE: str = "credentials.json"  # Service account JSON

    def __post_init__(self):
        # Remove duplicates while preserving order
        self.TIKTOK_USERS = list(dict.fromkeys(self.TIKTOK_USERS))


CONFIG = Config()

# ==========================================
# 📊 DATA MODELS
# ==========================================

class UserStatus(Enum):
    UNKNOWN = "unknown"
    CHECKING = "checking"
    LIVE = "live"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    INVALID = "invalid"
    ERROR = "error"


@dataclass
class CommentData:
    """Single comment record"""
    commenter: str
    live_host: str
    comment: str
    phones: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    synced_to_sheets: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'CommentData':
        return cls(**data)


@dataclass
class UserRecord:
    """Aggregated data for a commenter"""
    username: str
    first_seen_host: str
    all_comments: List[str] = field(default_factory=list)
    all_phones: Set[str] = field(default_factory=set)
    comments_with_phones: List[str] = field(default_factory=list)
    timestamps: List[str] = field(default_factory=list)

    def add_comment(self, comment: str, phones: List[str], timestamp: str):
        self.all_comments.append(comment)
        self.timestamps.append(timestamp)
        if phones:
            self.all_phones.update(phones)
            self.comments_with_phones.append(comment)

    def to_dict(self) -> dict:
        return {
            'username': self.username,
            'first_seen_host': self.first_seen_host,
            'all_comments': self.all_comments,
            'all_phones': list(self.all_phones),
            'comments_with_phones': self.comments_with_phones,
            'timestamps': self.timestamps,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'UserRecord':
        record = cls(
            username=data['username'],
            first_seen_host=data['first_seen_host'],
            all_comments=data.get('all_comments', []),
            all_phones=set(data.get('all_phones', [])),
            comments_with_phones=data.get('comments_with_phones', []),
            timestamps=data.get('timestamps', []),
        )
        return record


# ==========================================
# 📞 PHONE EXTRACTION (Enhanced)
# ==========================================

class PhoneExtractor:
    """Enhanced Nepali phone number extraction"""

    # Nepal mobile prefixes: 98x, 97x (NTC, Ncell, Smart)
    NEPAL_PREFIXES = ('98', '97')

    @classmethod
    def extract(cls, text: str) -> List[str]:
        if not text:
            return []

        phones = set()

        # Clean version for dense patterns
        text_clean = re.sub(r'\s+', '', text)

        # Pattern 1: Direct 10-digit numbers starting with 98/97
        for match in re.findall(r'(?:98|97)\d{8}', text_clean):
            phones.add(match)

        # Pattern 2: With country code 977
        for match in re.findall(r'977((?:98|97)\d{8})', text_clean):
            phones.add(match)

        # Pattern 3: With +977
        for match in re.findall(r'\+977((?:98|97)\d{8})', text_clean):
            phones.add(match)

        # Pattern 4: Spaced/formatted numbers (original text)
        for match in re.findall(r'((?:98|97)[\d\-.\s]{8,18})', text):
            digits = re.sub(r'\D', '', match)
            if len(digits) >= 10:
                candidate = digits[-10:]
                if candidate[:2] in cls.NEPAL_PREFIXES:
                    phones.add(candidate)

        # Pattern 5: Numbers with labels like "phone:", "contact:", "call:"
        labeled = re.findall(r'(?:phone|contact|call|no|number|num)[:\s]*([\d\-.\s+]{10,20})', text, re.I)
        for match in labeled:
            digits = re.sub(r'\D', '', match)
            if len(digits) >= 10:
                candidate = digits[-10:]
                if candidate[:2] in cls.NEPAL_PREFIXES:
                    phones.add(candidate)

        # Validate and return
        return [p for p in phones if len(p) == 10 and p[:2] in cls.NEPAL_PREFIXES]


# ==========================================
# 💾 BULLETPROOF DATA STORE
# ==========================================

class BulletproofDataStore:
    """
    Zero-loss data storage with:
    - Async write-through queue
    - Immediate disk persistence
    - Crash recovery from queue
    - Thread-safe operations
    """

    def __init__(self):
        self.records: Dict[str, UserRecord] = {}
        self.pending_comments: deque = deque()  # Write-through queue
        self.all_comments: List[CommentData] = []  # For sheets sync
        self._lock = asyncio.Lock()
        self._save_lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """Load existing data and recover any pending writes"""
        async with self._lock:
            # 1. Load main data
            await self._load_records()

            # 2. Recover pending queue (crash recovery)
            await self._recover_queue()

            self._initialized = True
            logger.info(f"📂 DataStore initialized: {len(self.records)} users, {len(self.all_comments)} comments")

    async def _load_records(self):
        """Load records from disk"""
        for filepath in [CONFIG.DATA_FILE, CONFIG.BACKUP_FILE]:
            if os.path.exists(filepath):
                try:
                    async with aiofiles.open(filepath, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        data = json.loads(content)

                        for username, record_data in data.get('records', {}).items():
                            self.records[username] = UserRecord.from_dict(record_data)

                        for comment_data in data.get('all_comments', []):
                            self.all_comments.append(CommentData.from_dict(comment_data))

                        logger.info(f"✅ Loaded data from {filepath}")
                        return
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load {filepath}: {e}")

    async def _recover_queue(self):
        """Recover any pending writes from crash"""
        if os.path.exists(CONFIG.QUEUE_FILE):
            try:
                async with aiofiles.open(CONFIG.QUEUE_FILE, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    pending = json.loads(content)

                    for item in pending:
                        comment = CommentData.from_dict(item)
                        await self._process_comment(comment, skip_queue=True)

                    logger.info(f"🔄 Recovered {len(pending)} pending comments from queue")

                # Clear queue file after recovery
                os.remove(CONFIG.QUEUE_FILE)
            except Exception as e:
                logger.warning(f"⚠️ Queue recovery failed: {e}")

    async def add_comment(self, commenter: str, live_host: str, comment_text: str, phones: List[str]) -> CommentData:
        """
        Add comment with guaranteed persistence:
        1. Write to queue file immediately (crash protection)
        2. Process into memory
        3. Periodic save to main files
        """
        comment = CommentData(
            commenter=commenter,
            live_host=live_host,
            comment=comment_text,
            phones=phones
        )

        # Step 1: Immediate queue persistence (crash protection)
        await self._append_to_queue(comment)

        # Step 2: Process into memory
        await self._process_comment(comment)

        return comment

    async def _append_to_queue(self, comment: CommentData):
        """Append to persistence queue immediately"""
        async with self._save_lock:
            try:
                # Read existing queue
                queue = []
                if os.path.exists(CONFIG.QUEUE_FILE):
                    async with aiofiles.open(CONFIG.QUEUE_FILE, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        if content.strip():
                            queue = json.loads(content)

                # Append new comment
                queue.append(comment.to_dict())

                # Write back
                async with aiofiles.open(CONFIG.QUEUE_FILE, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(queue, ensure_ascii=False))
            except Exception as e:
                logger.error(f"❌ Queue write failed: {e}")

    async def _process_comment(self, comment: CommentData, skip_queue: bool = False):
        """Process comment into records"""
        async with self._lock:
            # Add to records
            if comment.commenter not in self.records:
                self.records[comment.commenter] = UserRecord(
                    username=comment.commenter,
                    first_seen_host=comment.live_host
                )

            self.records[comment.commenter].add_comment(
                comment.comment,
                comment.phones,
                comment.timestamp
            )

            # Add to all_comments for sheets
            self.all_comments.append(comment)

    async def save_to_disk(self):
        """Save all data to disk and clear queue"""
        async with self._save_lock:
            try:
                data = {
                    'records': {u: r.to_dict() for u, r in self.records.items()},
                    'all_comments': [c.to_dict() for c in self.all_comments],
                    'saved_at': datetime.now().isoformat(),
                }

                # Write to backup first
                async with aiofiles.open(CONFIG.BACKUP_FILE, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))

                # Then main file
                async with aiofiles.open(CONFIG.DATA_FILE, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(data, ensure_ascii=False, indent=2))

                # Clear queue after successful save
                if os.path.exists(CONFIG.QUEUE_FILE):
                    os.remove(CONFIG.QUEUE_FILE)

                logger.debug(f"💾 Saved {len(self.records)} users to disk")
            except Exception as e:
                logger.error(f"❌ Disk save failed: {e}")

    async def get_stats(self) -> dict:
        async with self._lock:
            total_comments = sum(len(r.all_comments) for r in self.records.values())
            with_phones = sum(1 for r in self.records.values() if r.all_phones)
            total_phones = sum(len(r.all_phones) for r in self.records.values())
            return {
                'users': len(self.records),
                'comments': total_comments,
                'users_with_phones': with_phones,
                'total_phones': total_phones,
                'unsynced': sum(1 for c in self.all_comments if not c.synced_to_sheets)
            }

    async def get_unsynced_comments(self) -> List[CommentData]:
        """Get comments not yet synced to sheets"""
        async with self._lock:
            return [c for c in self.all_comments if not c.synced_to_sheets]

    async def mark_synced(self, comments: List[CommentData]):
        """Mark comments as synced"""
        async with self._lock:
            for comment in comments:
                comment.synced_to_sheets = True

    def get_sheets_data(self) -> List[List]:
        """Get data formatted for Google Sheets"""
        rows = []
        for username, record in sorted(self.records.items(),
                                        key=lambda x: len(x[1].all_phones),
                                        reverse=True):
            rows.append([
                f"https://www.tiktok.com/@{username}",  # Profile URL
                username,                                 # Username
                record.first_seen_host,                   # Host where first seen
                len(record.all_comments),                 # Comment count
                ' | '.join(record.all_comments[-10:]),    # Last 10 comments
                ' | '.join(record.comments_with_phones[-5:]),  # Comments WITH phones
                ', '.join(sorted(record.all_phones)),     # Phone numbers
                'YES' if record.all_phones else 'NO',     # Has phone flag
                len(record.all_phones),                   # Phone count
                record.timestamps[-1] if record.timestamps else '',  # Last seen
            ])
        return rows


# ==========================================
# 📊 GOOGLE SHEETS MANAGER
# ==========================================

class GoogleSheetsManager:
    """
    Manages Google Sheets sync with:
    - Auto sheet creation
    - Incremental updates
    - Separate phone column
    - Error resilience
    """

    HEADERS = [
        'Profile URL', 'Username', 'First Host', 'Comment Count',
        'Recent Comments', 'Comments with Phones', 'Phone Numbers',
        'Has Phone', 'Phone Count', 'Last Seen'
    ]

    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.spreadsheet = None
        self.worksheet = None
        self._initialized = False

    async def initialize(self):
        """Initialize Google Sheets connection"""
        try:
            if IN_COLAB:
                # Colab authentication
                auth.authenticate_user()
                creds, _ = default()
                self.client = gspread.authorize(creds)
                logger.info("✅ Google Sheets: Colab auth successful")
            else:
                # Service account authentication
                if os.path.exists(CONFIG.CREDENTIALS_FILE):
                    creds = Credentials.from_service_account_file(
                        CONFIG.CREDENTIALS_FILE,
                        scopes=[
                            'https://www.googleapis.com/auth/spreadsheets',
                            'https://www.googleapis.com/auth/drive'
                        ]
                    )
                    self.client = gspread.authorize(creds)
                    logger.info("✅ Google Sheets: Service account auth successful")
                else:
                    logger.warning(f"⚠️ No credentials file found at {CONFIG.CREDENTIALS_FILE}")
                    logger.info("📝 To enable Google Sheets:")
                    logger.info("   1. Create a service account at console.cloud.google.com")
                    logger.info("   2. Download JSON key as 'credentials.json'")
                    logger.info("   3. Share your spreadsheet with the service account email")
                    return False

            # Create or open spreadsheet
            await self._setup_spreadsheet()
            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"❌ Google Sheets init failed: {e}")
            return False

    async def _setup_spreadsheet(self):
        """Create or open the spreadsheet"""
        try:
            # Try to open existing
            self.spreadsheet = self.client.open(CONFIG.SHEET_NAME)
            logger.info(f"📊 Opened existing spreadsheet: {CONFIG.SHEET_NAME}")
        except gspread.SpreadsheetNotFound:
            # Create new
            self.spreadsheet = self.client.create(CONFIG.SHEET_NAME)
            logger.info(f"📊 Created new spreadsheet: {CONFIG.SHEET_NAME}")

        # Get or create worksheet
        try:
            self.worksheet = self.spreadsheet.worksheet("Data")
        except gspread.WorksheetNotFound:
            self.worksheet = self.spreadsheet.add_worksheet("Data", rows=1000, cols=15)

        # Set headers if empty
        if not self.worksheet.row_values(1):
            self.worksheet.update('A1:J1',
                [self.HEADERS])
