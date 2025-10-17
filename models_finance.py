from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Account(Base):
    __tablename__ = "accounts"

    account_id = Column(Integer, primary_key=True, autoincrement=True)
    account_name = Column(String(100), nullable=False, unique=True)
    current_balance = Column(Numeric(14, 2), nullable=False, default=0)

    transactions = relationship("Transaction", back_populates="account")


class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime, nullable=False, default=datetime.utcnow)
    amount = Column(Numeric(12, 2), nullable=False)
    merchant = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default='pending')  # pending, approved, completed, declined, cancelled
    account_id = Column(Integer, ForeignKey("accounts.account_id"), nullable=False)

    account = relationship("Account", back_populates="transactions")
