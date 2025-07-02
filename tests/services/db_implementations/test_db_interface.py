import pytest
from services.db_implementations.db_interface import DatabaseInterface

def test_cannot_instantiate_abstract_db_interface():
    """Test that you cannot instantiate a subclass of DatabaseInterface without implementing all abstract methods."""
    class DummyDB(DatabaseInterface):
        pass
    with pytest.raises(TypeError):
        DummyDB()