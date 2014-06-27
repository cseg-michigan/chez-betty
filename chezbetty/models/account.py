from .model import *

class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, nullable=False)
    type = Column(Enum("user", "special"), nullable=False)
    balance = Column(Float, nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)

    __mapper_args__ = {'polymorphic_on':type}

# special accounts
chezbetty = DBSession.query(Account).filter(Account.name == "chezbetty").one()
lost      = DBSession.query(Account).filter(Account.name == "lost").one()
