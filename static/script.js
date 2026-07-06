const form = document.getElementById("ppt-form");
const btn = document.getElementById("generate-btn");
const status = document.getElementById("status");

form.addEventListener("submit", async (e) => {
  e.preventDefault();

  const title = document.getElementById("title").value.trim();
  const num_slides = document.getElementById("num_slides").value;
  const tone = document.getElementById("tone").value;
  const audience = document.getElementById("audience").value.trim() || "general professional audience";

  if (!title) return;

  btn.disabled = true;
  btn.textContent = "Generating... (this can take ~20-40s)";
  status.textContent = "";
  status.className = "status";

  try {
    const response = await fetch("/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title, num_slides, tone, audience }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || "Something went wrong on the server.");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/[^a-z0-9_\- ]/gi, "")}.pptx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

    status.textContent = "Done! Your presentation has been downloaded.";
    status.className = "status success";
  } catch (err) {
    status.textContent = err.message;
    status.className = "status error";
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Presentation";
  }
});
