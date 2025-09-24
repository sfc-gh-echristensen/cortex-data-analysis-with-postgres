import json
from sqlalchemy import create_engine
from db import init_db, make_session_factory
from models import Completion


def test_save_and_fetch():
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    Session = make_session_factory(engine)
    with Session() as s:
        # save
        c = Completion(prompt="hello", result={"a": 1})
        s.add(c)
        s.commit()
        s.refresh(c)
        assert c.id is not None
        # fetch
        rows = s.query(Completion).all()
        assert len(rows) == 1
        assert rows[0].prompt == "hello"
        assert rows[0].result == {"a": 1}
