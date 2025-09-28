from langchain_anthropic import ChatAnthropic
from langsmith.evaluation import evaluate_comparative
from pydantic import BaseModel, Field

HEAD_TO_HEAD_PROMPT = """
We are testing out two different implementations of a deep research agent. This research agent is designed to conduct deep research on a given question.

This was the question: 
{question}

First Implementation's Response:
{answer_a}

Second Implementation's Response:
{answer_b}

In order to evaluate these agents, keep the following criteria in mind:
- A good research agent should research sufficient sources to answer the question. These sources should be diverse and high quality. More sources is not always necessarily better, but it is important to have ENOUGH sources to feel confident in the claims that are made.
- A good research agent should completely and comprehensively answer the user's question. 
- Deep research agents are expensive. The user expects a very good, and also very detailed answer. They should get all of the information that they need from this response, and should not have to ask for followups usually.
- Citations should be provided for all claims, and should be formatted in a way that is easy to read and understand.

Important:
These two implementations conducted research differently, and so they might have different information and different sources. This is a key point for you to evaluate.
Which agent was able to find better sources and better answer the question? The #1 thing we care about the most is the quality and comprehensiveness of the answer.

With those criteria in mind, please select which response you prefer, and explain why!
"""

class HeadToHeadRanking(BaseModel):
    reasoning: str = Field(description="The reasoning for why you selected the preferred answer. This should be a detailed explanation!")
    preferred_answer: int = Field(description="The preferred answer between 1 and 2, where 1 is the first response, 2 is the second response.")


def head_to_head_evaluator(inputs: dict, outputs: list[dict]) -> list:
    grader_llm = ChatAnthropic(
        model="claude-opus-4-20250514",
        max_tokens=20000,
        thinking={"type": "enabled", "budget_tokens": 16000},
    )

    response = grader_llm.with_structured_output(HeadToHeadRanking).invoke(HEAD_TO_HEAD_PROMPT.format(
        question=inputs["messages"][0]["content"],
        answer_a=outputs[0].get("final_report", "N/A"),
        answer_b=outputs[1].get("final_report", "N/A"),
    ))

    if response.preferred_answer == 1:
        scores = [1, 0]
    elif response.preferred_answer == 2:
        scores = [0, 1]
    else:
        scores = [0, 0]
    return scores


ALL_THREE_PROMPT = """
We are testing out three different implementations of a deep research agent. This research agent is designed to conduct deep research on a given question.

This was the question: 
{question}

First Implementation's Response:
{answer_a}

Second Implementation's Response:
{answer_b}

Third Implementation's Response:
{answer_c}

In order to evaluate these agents, keep the following criteria in mind:
- A good research agent should research sufficient sources to answer the question. These sources should be diverse and high quality. More sources is not always necessarily better, but it is important to have ENOUGH sources to feel confident in the claims that are made.
- A good research agent should completely and comprehensively answer the user's question. 
- Deep research agents are expensive. The user expects a very good, and also very detailed answer. They should get all of the information that they need from this response, and should not have to ask for followups usually.
- Citations should be provided for all claims, and should be formatted in a way that is easy to read and understand.

Important:
These three implementations conducted research differently, and so they might have different information and different sources. This is a key point for you to evaluate.
Which agent was able to find better sources and better answer the question? The #1 thing we care about the most is the quality and comprehensiveness of the answer.

With those criteria in mind, please rank the responses from 1 to 3, where 1 is the best response, 2 is the second best response, and 3 is the worst response.
And please explain why you selected the ranking you did!
"""

class Rankings(BaseModel):
    reasoning: str = Field(description="The reasoning for why you selected the preferred answer. This should be a detailed explanation!")
    preferred_answer: int = Field(description="The preferred answer between 1 and 3, where 1 is the first response, 2 is the second response, and 3 is the third response.")
    second_best_answer: int = Field(description="The second best answer between 1 and 3, where 1 is the first response, 2 is the second response, and 3 is the third response.")
    worst_answer: int = Field(description="The worst answer between 1 and 3, where 1 is the first response, 2 is the second response, and 3 is the third response.")

def free_for_all_evaluator(inputs: dict, outputs: list[dict]) -> list:
    grader_llm = ChatAnthropic(
        model="claude-opus-4-20250514",
        max_tokens=20000,
        thinking={"type": "enabled", "budget_tokens": 16000},
    )

    response = grader_llm.with_structured_output(Rankings).invoke(ALL_THREE_PROMPT.format(
        question=inputs["messages"][0]["content"],
        answer_a=outputs[0].get("final_report", "N/A"),
        answer_b=outputs[1].get("final_report", "N/A"),
        answer_c=outputs[2].get("final_report", "N/A"),
    ))

    scores = [0, 0, 0]
    scores[response.preferred_answer - 1] = 1
    scores[response.second_best_answer - 1] = .5
    scores[response.worst_answer - 1] = 0
    return scores

single_agent = "DR Single Agent - Tavily #-87e8a6c0"
multi_agent_supervisor = "DR Supervisor: Multi Agent - Tavily #-cd25e7e3"
multi_agent_supervisor_v2 = "DR Supervisor: Multi Agent - Tavily (v2) #-40967f53"
multi_agent_workflow = "DR MAW - Tavily #-c6818a83"


# evaluate_comparative(
#     (single_agent_experiment_name, multi_agent_supervisor_experiment_name, multi_agent_workflow_experiment_name),  # Replace with the names/IDs of your experiments
#     evaluators=[free_for_all_evaluator],
#     randomize_order=True,
# )

evaluate_comparative(
    (single_agent, multi_agent_supervisor_v2),  # Replace with the names/IDs of your experiments
    evaluators=[head_to_head_evaluator],
    randomize_order=True,
)