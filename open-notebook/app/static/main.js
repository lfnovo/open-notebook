const queryInput = document.getElementById("query");
const submitButton = document.getElementById("submit");
const resultCard = document.getElementById("result");
const answerEl = document.getElementById("answer");
const citationsEl = document.getElementById("citations");

submitButton.addEventListener("click", async () => {
  const query = queryInput.value.trim();
  if (!query) {
    return;
  }

  submitButton.disabled = true;
  answerEl.textContent = "Loading...";
  citationsEl.innerHTML = "";
  resultCard.hidden = false;

  try {
    const response = await fetch("/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, k: 5 }),
    });
    const data = await response.json();
    answerEl.textContent = data.answer || "No answer returned.";
    citationsEl.innerHTML = "";

    (data.citations || []).forEach((citation) => {
      const node = document.createElement("div");
      node.className = "citation";
      node.innerHTML = `
        <strong>${citation.source}</strong>
        <div class="muted">${citation.chunk_id}</div>
        <div>${citation.snippet}</div>
      `;
      citationsEl.appendChild(node);
    });
  } catch (error) {
    answerEl.textContent = `Request failed: ${error.message}`;
  } finally {
    submitButton.disabled = false;
  }
});
