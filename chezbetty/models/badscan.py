from .model import *

from sqlalchemy_utils import ArrowType

class BadScan(Base):
    __tablename__ = 'badscans'

    id        = Column(Integer, primary_key=True, nullable=False)
    timestamp = Column(ArrowType, nullable=False, default=datetime.datetime.utcnow)
    badscan   = Column(String(255), nullable=False)

    def __init__(self, scan):
        self.badscan = scan

    @classmethod
    def from_id(cls, id):
        return DBSession.query(cls).filter(cls.id == id).one()

    @classmethod
    def all(cls):
        return DBSession.query(cls)\
                        .order_by(cls.timestamp).all()

    @classmethod
    def get_scans_with_counts(cls):
        out = []
        badscans = DBSession.query(cls.badscan, func.count(cls.badscan).label('count'))\
                        .group_by(cls.badscan)\
                        .all()
        for badscan in badscans:
            most_recent = DBSession.query(cls)\
                            .filter(cls.badscan==badscan.badscan)\
                            .order_by(cls.timestamp.desc())\
                            .first()
            out.append({
                'badscan': badscan.badscan,
                'count': badscan.count,
                'timestamp': most_recent.timestamp
            })

        return out

    @classmethod
    def delete_scans(cls, badscan):
        DBSession.query(cls).filter(cls.badscan==badscan).delete()
