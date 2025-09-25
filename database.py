from sqlalchemy import create_engine, Column, BigInteger, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, backref
from sqlalchemy.sql import func

DATABASE_URL = "sqlite:///./guarantor.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    user_id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, nullable=True)
    balance = Column(Integer, default=0)
    card_number = Column(String, nullable=True)
    ton_wallet = Column(String, nullable=True)

    referred_by_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=True)
    referrals = relationship("User", backref=backref("referrer", remote_side=[user_id]))

class Deal(Base):
    __tablename__ = "deals"
    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=True)
    seller_id = Column(BigInteger, ForeignKey('users.user_id'), nullable=False)
    amount = Column(Integer, nullable=False)
    description = Column(String)
    currency = Column(String)
    status = Column(String, default='awaiting_buyer')
    payment_method = Column(String)
    deal_code = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])

def init_db():
    Base.metadata.create_all(bind=engine)