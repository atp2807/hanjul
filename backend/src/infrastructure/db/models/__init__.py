"""ORM 모델 중앙 등록 — Alembic/metadata가 모든 모델을 인식하도록 여기서 import."""
from src.infrastructure.db.models.account import Account, Credential
from src.infrastructure.db.models.age_verification import AgeVerificationRequest
from src.infrastructure.db.models.book import Block, Book, Chapter
from src.infrastructure.db.models.campaign import ReviewApplication, ReviewCampaign, ReviewerBlock
from src.infrastructure.db.models.distribution import Distribution
from src.infrastructure.db.models.doc import Document, ShareLink
from src.infrastructure.db.models.manuscript import ManuscriptBook, ManuscriptRevision
from src.infrastructure.db.models.notification import Follow, Notification
from src.infrastructure.db.models.operator import AuditLog, Operator
from src.infrastructure.db.models.order import Order, Settlement
from src.infrastructure.db.models.payout import BankAccount, Payout, SettlementRun
from src.infrastructure.db.models.report import Report
from src.infrastructure.db.models.review import Review
from src.infrastructure.db.models.withholding import WithholdingSubject

__all__ = [
    "Book", "Chapter", "Block", "Account", "Credential", "Order", "Settlement", "Distribution", "Review",
    "Follow", "Notification", "ReviewCampaign", "ReviewApplication", "ReviewerBlock",
    "Operator", "AuditLog", "Report", "BankAccount", "Payout", "SettlementRun",
    "Document", "ShareLink",
    "ManuscriptBook", "ManuscriptRevision",
    "WithholdingSubject",
    "AgeVerificationRequest",
]
