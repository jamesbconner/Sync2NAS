import pytest
from services.llm_implementations.llm_interface import LLMInterface

def test_cannot_instantiate_abstract_llm_interface():
    """Test that you cannot instantiate a subclass of LLMInterface without implementing all abstract methods."""
    class DummyLLM(LLMInterface):
        pass
    with pytest.raises(TypeError):
        DummyLLM()