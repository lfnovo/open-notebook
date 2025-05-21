import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from langchain_core.runnables import RunnableConfig

# Import the FastAPI app instance
from open_notebook.api.main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def ensure_model_manager_initialized():
    """
    This fixture automatically runs for every test.
    It patches 'open_notebook.model_manager.model_manager' to ensure it's treated as initialized
    without requiring actual database interaction or environment setup during unit tests.
    We assume that other parts of the system (like graph creation) might try to access
    model_manager attributes upon import or initial setup.
    """
    with patch('open_notebook.model_manager.model_manager', MagicMock()) as mock_mm:
        # You can configure mock_mm further if specific attributes are accessed
        # during the setup phase of the SUT (System Under Test), e.g., before ainvoke is called.
        # For now, a simple MagicMock should prevent AttributeError for basic accesses.
        yield mock_mm

# Test 1: Successful request
@patch('open_notebook.api.main.graph.ainvoke')
def test_ask_success(mock_ainvoke):
    mock_ainvoke.return_value = {"final_answer": "This is a test answer."}
    response = client.post("/api/v1/ask", json={"question": "What is FastAPI?"})
    assert response.status_code == 200
    assert response.json() == {"final_answer": "This is a test answer."}
    mock_ainvoke.assert_called_once()

# Test 2: Graph invocation raises an unexpected error
@patch('open_notebook.api.main.graph.ainvoke')
def test_ask_graph_unexpected_error(mock_ainvoke):
    mock_ainvoke.side_effect = Exception("Graph processing error")
    response = client.post("/api/v1/ask", json={"question": "Test unexpected error"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Graph processing error"}
    mock_ainvoke.assert_called_once()

# Test 3: Graph returns invalid structure
@patch('open_notebook.api.main.graph.ainvoke')
def test_ask_graph_invalid_response_structure(mock_ainvoke):
    mock_ainvoke.return_value = {"wrong_key": "some data"}  # Invalid structure
    response = client.post("/api/v1/ask", json={"question": "Test invalid structure"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Invalid response structure from ask graph"}
    mock_ainvoke.assert_called_once()

# Test 4: Request with optional model IDs
@patch('open_notebook.api.main.graph.ainvoke')
def test_ask_with_model_ids(mock_ainvoke):
    mock_ainvoke.return_value = {"final_answer": "Model IDs test"}
    payload = {
        "question": "Test with model IDs",
        "strategy_model_id": "test_strat_id",
        "answer_model_id": "test_ans_id",
        "final_answer_model_id": "test_final_id"
    }
    response = client.post("/api/v1/ask", json=payload)
    assert response.status_code == 200
    assert response.json() == {"final_answer": "Model IDs test"}

    mock_ainvoke.assert_called_once()
    args, kwargs = mock_ainvoke.call_args
    
    # The input to ainvoke is the first positional argument
    assert args[0] == {"question": "Test with model IDs"}

    # The config is passed as a keyword argument
    config_passed = kwargs.get('config')
    assert isinstance(config_passed, RunnableConfig)
    assert config_passed.configurable['strategy_model'] == "test_strat_id"
    assert config_passed.configurable['answer_model'] == "test_ans_id"
    assert config_passed.configurable['final_answer_model'] == "test_final_id"

@patch('open_notebook.api.main.graph.ainvoke')
def test_ask_with_some_model_ids(mock_ainvoke):
    mock_ainvoke.return_value = {"final_answer": "Partial Model IDs test"}
    payload = {
        "question": "Test with some model IDs",
        "strategy_model_id": "test_strat_id_partial"
        # answer_model_id and final_answer_model_id are omitted
    }
    response = client.post("/api/v1/ask", json=payload)
    assert response.status_code == 200
    assert response.json() == {"final_answer": "Partial Model IDs test"}

    mock_ainvoke.assert_called_once()
    args, kwargs = mock_ainvoke.call_args
    
    assert args[0] == {"question": "Test with some model IDs"}

    config_passed = kwargs.get('config')
    assert isinstance(config_passed, RunnableConfig)
    assert config_passed.configurable['strategy_model'] == "test_strat_id_partial"
    assert "answer_model" not in config_passed.configurable
    assert "final_answer_model" not in config_passed.configurable

# Test for ensuring that an existing HTTPException (e.g. from a deeper layer if not caught) is re-raised
@patch('open_notebook.api.main.graph.ainvoke')
def test_ask_reraises_httpexception(mock_ainvoke):
    from fastapi import HTTPException
    mock_ainvoke.side_effect = HTTPException(status_code=418, detail="I'm a teapot")
    response = client.post("/api/v1/ask", json={"question": "Test HTTP exception re-raise"})
    assert response.status_code == 418
    assert response.json() == {"detail": "I'm a teapot"}
    mock_ainvoke.assert_called_once()
