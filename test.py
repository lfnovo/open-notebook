# from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer
# import torch

# # =========================
# # CONFIG
# # =========================
# model_name = "Qwen/Qwen2.5-1.5B-Instruct"

# device = "cuda" if torch.cuda.is_available() else "cpu"
# print(f"Using device: {device}")

# # =========================
# # TOKENIZER
# # =========================
# tokenizer = AutoTokenizer.from_pretrained(model_name)

# # =========================
# # MODEL
# # =========================
# model = AutoModelForCausalLM.from_pretrained(
#     model_name,
#     dtype=torch.float16 if device == "cuda" else torch.float32,
#     device_map="auto"
# )

# # =========================
# # STREAMER
# # =========================
# streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

# # =========================
# # FUNCTION: STREAM RESPONSE
# # =========================
# def generate_stream(prompt, target_words=2000):
#     messages = [{"role": "user", "content": prompt}]
#     total_words = 0

#     while total_words < target_words:
#         text = tokenizer.apply_chat_template(
#             messages,
#             tokenize=False,
#             add_generation_prompt=True
#         )

#         inputs = tokenizer(text, return_tensors="pt").to(model.device)

#         print("\n", end="", flush=True)  # start printing immediately

#         with torch.inference_mode():
#             outputs = model.generate(
#                 **inputs,
#                 max_new_tokens=512,
#                 do_sample=False,   # ⚡ faster
#                 use_cache=True,
#                 streamer=streamer   # 🔥 LIVE OUTPUT
#             )

#         new_text = tokenizer.decode(
#             outputs[0][inputs.input_ids.shape[-1]:],
#             skip_special_tokens=True
#         )

#         word_count = len(new_text.split())
#         total_words += word_count

#         messages.append({"role": "assistant", "content": new_text})
#         messages.append({"role": "user", "content": "Continue from where you stopped. Do not repeat."})

# # =========================
# # LOOP
# # =========================
# while True:
#     user_input = input("\nEnter your prompt (or 'exit'): ")
#     if user_input.lower() == "exit":
#         break

#     enhanced_prompt = f"""
# Write a detailed response of at least 2000 words.

# Topic:
# {user_input}

# Make it structured and complete.
# """

#     print("\n=== Output ===\n")

#     generate_stream(enhanced_prompt, target_words=2000)






import streamlit as st
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
import torch
import threading

# =========================
# CONFIG
# =========================
model_name = "Qwen/Qwen2.5-1.5B-Instruct"
device = "cuda" if torch.cuda.is_available() else "cpu"

st.title("💬 Qwen Chat with Suggestions")

# =========================
# LOAD MODEL
# =========================
@st.cache_resource(show_spinner=True)
def load_model():
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto"
    )
    return tokenizer, model

tokenizer, model = load_model()

# =========================
# SESSION STATE
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "response_text" not in st.session_state:
    st.session_state.response_text = ""

# Placeholder for streaming output
output_container = st.empty()

# =========================
# STREAM GENERATION FUNCTION
# =========================
def generate_stream(prompt, max_tokens=512):
    messages = st.session_state.messages + [{"role": "user", "content": prompt}]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True)
    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    def worker():
        with torch.inference_mode():
            model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=False,
                use_cache=True,
                streamer=streamer
            )

    thread = threading.Thread(target=worker)
    thread.start()

    output = ""
    for new_text in streamer:
        output += new_text
        st.session_state.response_text = output
        output_container.markdown(f"```\n{output}\n```")

    thread.join()
    return output

# =========================
# USER INPUT AND COMMANDS
# =========================

# Text input area for user prompt
prompt_input = st.text_area("Enter your prompt:", height=100)

# Command buttons — act as presets, not overwrite prompt silently
col1, col2, col3, col4 = st.columns(4)
if col1.button("Continue"):
    prompt_input = "Continue from where you stopped."
if col2.button("Explain"):
    prompt_input = "Explain this in simple words."
if col3.button("Examples"):
    prompt_input = "Give real-world examples."
if col4.button("Summarize"):
    prompt_input = "Summarize this."

# Button to send prompt for generation
if st.button("Send") and prompt_input.strip():
    st.session_state.response_text = ""
    st.session_state.messages.append({"role": "user", "content": prompt_input})

    # Generate and wait for full response before appending assistant message
    response = generate_stream(prompt_input)
    st.session_state.messages.append({"role": "assistant", "content": response})

    # Clear prompt input after sending (optional)
    prompt_input = ""

# Show chat history optionally (nice to add)
if st.session_state.messages:
    st.markdown("### Chat History")
    for msg in st.session_state.messages:
        role = msg['role']
        content = msg['content']
        if role == "user":
            st.markdown(f"**User:** {content}")
        else:
            st.markdown(f"**Assistant:** {content}")